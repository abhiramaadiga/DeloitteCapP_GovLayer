"""
backend/pep/gateway.py
High-performance Zero-Trust Policy Enforcement Point (PEP) Reverse Proxy.
"""
import time
from fastapi import APIRouter, Request, Response, HTTPException
from backend.core.auth import NHITokenManager
from backend.core.killswitch import KillSwitch
from backend.api.mock_banking import (
    get_bank_faqs,
    get_account_balance,
    execute_wire_transfer,
    export_all_customer_data,
    TransferRequest
)

router = APIRouter(prefix="/gateway", tags=["Policy Enforcement Point"])

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def pep_reverse_proxy(path: str, request: Request):
    """
    Main PEP Gateway Pipeline:
    1. Measure Latency (<5ms SLA)
    2. Extract & Validate Agent Passport Token
    3. Check Redis Revocation Kill-Switch (<1ms)
    4. Enforce Role Separation (Deterministic Gate)
    5. Route to Core Banking Upstream
    """
    start_time = time.perf_counter()
    
    # 1. Extract Bearer Token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication Failed: Missing Bearer Agent Passport")
        
    token = auth_header.replace("Bearer ", "").strip()
    agent_claims = NHITokenManager.verify_agent_token(token)
    if not agent_claims:
        raise HTTPException(status_code=403, detail="Security Denial: Invalid or Expired Agent Passport Signature")
        
    agent_id = agent_claims.get("agent_id")
    agent_role = agent_claims.get("role")
    
    # 2. Check Kill-Switch (<0.2ms)
    if KillSwitch.is_quarantined(agent_id):
        raise HTTPException(
            status_code=403,
            detail=f"SECURITY QUARANTINE: Agent '{agent_id}' is terminated by automated kill-switch."
        )
        
    # 3. Deterministic Least-Privilege Policy Check
    # Support bots can NEVER access wire transfers or bulk customer data
    normalized_path = "/" + path.strip("/")
    method = request.method
    
    #Updated: blocked from premature Fixed Deposit liquidation

    if agent_role == "tier1_customer_service":
        if normalized_path.startswith("/transfers/"):
            raise HTTPException(
                status_code=403,
                detail="POLICY VIOLATION [SOX-404]: Support agents are prohibited from initiating financial transfers."
            )
        if "/deposits/liquidate" in normalized_path:
            raise HTTPException(
                status_code=403,
                detail="POLICY VIOLATION [BANKING-GOV]: Support agents are prohibited from liquidating investment assets."
            )
        if normalized_path == "/customers/export":
            raise HTTPException(
                status_code=403,
                detail="POLICY VIOLATION [PCI-DSS]: Support agents cannot perform bulk customer PII exports."
            )
            
    # 4. Route to Mock Core Banking
    response_data = None
    if normalized_path == "/faq":
        response_data = get_bank_faqs()
    elif normalized_path.startswith("/accounts/") and normalized_path.endswith("/balance"):
        acc_id = normalized_path.split("/")[2]
        response_data = get_account_balance(acc_id)
    elif normalized_path == "/transfers/wire" and method == "POST":
        body = await request.json()
        req_obj = TransferRequest(**body)
        response_data = execute_wire_transfer(req_obj)
    elif normalized_path == "/customers/export":
        response_data = export_all_customer_data()
    else:
        raise HTTPException(status_code=404, detail="Upstream banking endpoint not found")

    # 5. Measure PEP Inline Latency
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    return {
        "governor_status": "ALLOWED",
        "pep_latency_ms": latency_ms,
        "agent_id": agent_id,
        "role": agent_role,
        "upstream_data": response_data
    }