"""
backend/main.py
Root FastAPI Application mounting PEP, Core Banking, and Health Endpoints.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.pep.gateway import router as pep_router
from backend.api.mock_banking import router as banking_router
from backend.core.auth import NHITokenManager
from backend.core.killswitch import KillSwitch
from pydantic import BaseModel

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Zero-Trust Identity & Access Governor for Autonomous AI Agents in BFSI Banking."
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