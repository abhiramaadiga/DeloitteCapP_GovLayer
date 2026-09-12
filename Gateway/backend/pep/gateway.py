"""
backend/pep/gateway.py
High-performance Zero-Trust Policy Enforcement Point (PEP) Reverse Proxy.
"""
import time
from fastapi import APIRouter, Request, Response, HTTPException
from backend.core.auth import NHITokenManager
from backend.core.killswitch import KillSwitch
from backend.core.kafka_producer import telemetry_producer
from backend.ml.risk_engine import evaluate_agent_request
from backend.api.mock_banking import (
    get_bank_faqs,
    get_account_balance,
    execute_wire_transfer,
    export_all_customer_data,
    get_account_deposits,
    liquidate_fixed_deposit,
    TransferRequest
)

router = APIRouter(prefix="/gateway", tags=["Policy Enforcement Point"])

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def pep_reverse_proxy(path: str, request: Request):
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
    
    # Normalize path cleanly & get HTTP method
    clean_path = path.strip("/")
    normalized_path = "/" + clean_path
    method = request.method

    # 2. Check Kill-Switch (<0.2ms)
    if KillSwitch.is_quarantined(agent_id):
        telemetry_producer.emit_event(
            agent_id=agent_id,
            role=agent_role,
            endpoint=normalized_path,
            method=method,
            governor_status="QUARANTINED",
            risk_score=1.0,
            pep_latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            violation_reason="Terminated by automated kill-switch"
        )
        raise HTTPException(
            status_code=403,
            detail=f"SECURITY QUARANTINE: Agent '{agent_id}' is terminated by automated kill-switch."
        )

    # 3. Read body safely for ML evaluation
    body_text = ""
    req_body_json = None
    if method in ("POST", "PUT", "PATCH"):
        try:
            body_bytes = await request.body()
            body_text = body_bytes.decode("utf-8")
            if body_text:
                import json
                req_body_json = json.loads(body_text)
        except Exception:
            pass

    # 4. Deterministic Least-Privilege Policy Check (SOX 404 / Least-Privilege Gate)
    if agent_role == "tier1_customer_service":
        violation_reason = None
        if normalized_path.startswith("/transfers"):
            violation_reason = "POLICY VIOLATION [SOX-404]: Support agents are prohibited from initiating financial transfers."
        elif "/deposits/liquidate" in normalized_path:
            violation_reason = "POLICY VIOLATION [BANKING-GOV]: Support agents are prohibited from liquidating investment assets."
        elif normalized_path == "/customers/export":
            violation_reason = "POLICY VIOLATION [PCI-DSS]: Support agents cannot perform bulk customer PII exports."

        if violation_reason:
            telemetry_producer.emit_event(
                agent_id=agent_id,
                role=agent_role,
                endpoint=normalized_path,
                method=method,
                governor_status="BLOCKED",
                risk_score=0.90,
                pep_latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                payload_preview=body_text,
                violation_reason=violation_reason
            )
            raise HTTPException(status_code=403, detail=violation_reason)

    # 5. Behavioral ML Risk Evaluation (Member 2's Engine)
    risk_score = 0.10
    try:
        from backend.ml.risk_engine import evaluate_agent_request
        risk_result = evaluate_agent_request(
            agent_id=agent_id,
            endpoint=normalized_path,
            payload_str=body_text,
            method=method
        )
        risk_score = risk_result.get("risk_score", 0.10)
        if risk_result.get("is_anomaly"):
            KillSwitch.quarantine_agent(agent_id, "ML Behavioral Anomaly Detected", risk_score)
            detail_msg = f"SECURITY QUARANTINE: Agent '{agent_id}' auto-quarantined by Behavioral ML Engine (Risk: {risk_score})."
            telemetry_producer.emit_event(
                agent_id=agent_id,
                role=agent_role,
                endpoint=normalized_path,
                method=method,
                governor_status="QUARANTINED",
                risk_score=risk_score,
                pep_latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                payload_preview=body_text,
                violation_reason=detail_msg
            )
            raise HTTPException(status_code=403, detail=detail_msg)
    except HTTPException:
        raise
    except Exception:
        # Fail safe if ML has internal parse issue
        pass

    # 6. Route to Mock Core Banking Upstream
    response_data = None
    if normalized_path == "/faq":
        response_data = get_bank_faqs()
    elif normalized_path.startswith("/accounts/") and normalized_path.endswith("/balance"):
        parts = normalized_path.split("/")
        acc_id = parts[2]
        response_data = get_account_balance(acc_id)
    elif normalized_path.startswith("/accounts/") and normalized_path.endswith("/deposits"):
        parts = normalized_path.split("/")
        acc_id = parts[2]
        response_data = get_account_deposits(acc_id)
    elif "/deposits/liquidate" in normalized_path and method == "POST":
        parts = normalized_path.split("/")
        acc_id = parts[2] if len(parts) > 2 else "401"
        deposit_id = "FD-901"
        if req_body_json and "deposit_id" in req_body_json:
            deposit_id = req_body_json["deposit_id"]
        response_data = liquidate_fixed_deposit(account_id=acc_id, deposit_id=deposit_id)
    elif normalized_path == "/transfers/wire" and method == "POST":
        if req_body_json:
            req_obj = TransferRequest(**req_body_json)
        else:
            req_obj = TransferRequest(source_account="401", destination_account="992", amount_inr=0.0, remarks="")
        response_data = execute_wire_transfer(req_obj)
    elif normalized_path == "/customers/export":
        response_data = export_all_customer_data()
    else:
        raise HTTPException(status_code=404, detail=f"Upstream banking endpoint '{normalized_path}' not found")

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    telemetry_producer.emit_event(
        agent_id=agent_id,
        role=agent_role,
        endpoint=normalized_path,
        method=method,
        governor_status="ALLOWED",
        risk_score=risk_score,
        pep_latency_ms=latency_ms,
        payload_preview=body_text
    )
    return {
        "governor_status": "ALLOWED",
        "pep_latency_ms": latency_ms,
        "agent_id": agent_id,
        "role": agent_role,
        "risk_score": risk_score,
        "upstream_data": response_data
    }