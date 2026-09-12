"""
backend/main.py
Root FastAPI Application mounting PEP, Core Banking, and Health Endpoints.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
from backend.core.config import settings
from backend.ml.risk_engine import _load_model
from backend.pep.gateway import router as pep_router, pep_reverse_proxy
from backend.api.mock_banking import router as banking_router
from backend.core.auth import NHITokenManager
from backend.core.killswitch import KillSwitch
from pydantic import BaseModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup:
    try:
        _load_model()
        print("[ML Engine] Isolation Forest model pre-warmed successfully in memory.")
    except Exception as e:
        print(f"[ML Engine] Pre-warm failed: {e}")
    yield
    # Runs on shutdown (optional cleanup)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Zero-Trust Identity & Access Governor for Autonomous AI Agents in BFSI Banking.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(pep_router)
app.include_router(banking_router)

@app.get("/healthz")
def health_check():
    return {"status": "HEALTHY", "domain": settings.DOMAIN}

class MintTokenRequest(BaseModel):
    agent_id: str
    role: str
    max_amount: float = 0.0

@app.post("/api/v1/passport/mint")
def mint_passport(req: MintTokenRequest):
    """Utility endpoint to mint test Agent Passports."""
    token = NHITokenManager.mint_agent_token(
        agent_id=req.agent_id,
        role=req.role,
        max_transaction_amount=req.max_amount
    )
    return {"agent_id": req.agent_id, "access_token": token, "token_type": "Bearer"}

class QuarantineRequest(BaseModel):
    agent_id: str
    reason: str

@app.post("/api/v1/killswitch/quarantine")
def trigger_quarantine(req: QuarantineRequest):
    """Manual or automated kill-switch trigger."""
    return KillSwitch.quarantine_agent(req.agent_id, req.reason, risk_score=1.0)

@app.post("/api/v1/killswitch/lift")
def lift_quarantine_endpoint(req: QuarantineRequest):
    """Lift quarantine with mandatory justification."""
    return KillSwitch.lift_quarantine(req.agent_id, req.reason, analyst_id="SOC-ANALYST-PES")



class ChatPromptRequest(BaseModel):
    user_prompt: str
    account_id: str = "401"
@app.post("/api/v1/chat/message")
async def chat_agent_endpoint(req: ChatPromptRequest):
    """
    Simulates the AI Chatbot receiving user text and
    invoking Core Banking tools through the Governor Gateway.
    """
    prompt_lower = req.user_prompt.lower()
    token = NHITokenManager.mint_agent_token("Agent-Support-01", "tier1_customer_service")
    
    # 1. Intent: Balance Query
    if "balance" in prompt_lower or "how much" in prompt_lower:
        result = await pep_reverse_proxy(f"accounts/{req.account_id}/balance", Request(scope={"type": "http", "method": "GET", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
        balance = result["upstream_data"]["balance_inr"]
        return {
            "reply": f"Hello Rahul! Your current savings account balance is ₹{balance:,.2f}.",
            "action_taken": "GET /accounts/401/balance",
            "governor_status": "ALLOWED",
            "pep_latency_ms": result["pep_latency_ms"]
        }
        
    # 2. Intent: Fixed Deposit Query
    elif "deposit" in prompt_lower or "fd" in prompt_lower or "investment" in prompt_lower:
        result = await pep_reverse_proxy(f"accounts/{req.account_id}/deposits", Request(scope={"type": "http", "method": "GET", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
        total_fd = result["upstream_data"]["total_deposits_inr"]
        return {
            "reply": f"You currently have 1 active Fixed Deposit of ₹{total_fd:,.2f} earning 7.25% interest maturing in March 2027.",
            "action_taken": "GET /accounts/401/deposits",
            "governor_status": "ALLOWED",
            "pep_latency_ms": result["pep_latency_ms"]
        }
        
    # 3. Intent: Transfer Wire (Attack Scenario 1)
    elif "transfer" in prompt_lower or "wire" in prompt_lower or "send money" in prompt_lower:
        try:
            await pep_reverse_proxy("transfers/wire", Request(scope={"type": "http", "method": "POST", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
        except HTTPException as e:
            return {
                "reply": "⚠️ Security Alert: I attempted to process this wire transfer, but the Bank Identity & Access Governor blocked the execution.",
                "action_taken": "POST /transfers/wire",
                "governor_status": "BLOCKED",
                "error_code": 403,
                "violation_reason": e.detail
            }
            
    # 4. Intent: Liquidate FD (Attack Scenario 2)
    elif "liquidate" in prompt_lower or "break fd" in prompt_lower:
        try:
            await pep_reverse_proxy(f"accounts/{req.account_id}/deposits/liquidate", Request(scope={"type": "http", "method": "POST", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
        except HTTPException as e:
            return {
                "reply": "⚠️ Security Alert: I cannot break or liquidate your Fixed Deposit. High-value asset liquidation is blocked for customer support bots.",
                "action_taken": "POST /deposits/liquidate",
                "governor_status": "BLOCKED",
                "error_code": 403,
                "violation_reason": e.detail
            }
            
    # Default Fallback
    return {
        "reply": "I am Apex Bank's Virtual Assistant. I can help you check your account balance, view your Fixed Deposits, or answer branch questions.",
        "action_taken": "GET /faq",
        "governor_status": "ALLOWED",
        "pep_latency_ms": 0.8
    }