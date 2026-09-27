"""
backend/pep/gateway.py
High-performance Zero-Trust Policy Enforcement Point (PEP) Reverse Proxy.
"""
import time
import hmac
import hashlib
import json
import base64
from typing import Optional, Dict, Any, Tuple
from fastapi import APIRouter, Request, Response, HTTPException
from backend.core.config import settings
from backend.core.auth import NHITokenManager
from backend.core.killswitch import KillSwitch
from backend.core.kafka_producer import telemetry_producer
from backend.core.database import save_audit_log
from backend.core.policy_engine import policy_engine
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

def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))

_VERIFIED_TOKEN_CACHE: Dict[str, Tuple[Dict[str, Any], float]] = {}

def verify_agent_passport_detailed(token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validates HMAC-SHA256 signature and expiration of an Agent Passport token.
    Returns (claims_dict, error_code).
    error_code is one of:
      - None (valid)
      - "MALFORMED" (not 3 parts, invalid base64, or unparseable json)
      - "TAMPERED" (HMAC signature does not match or payload corrupted)
      - "EXPIRED" (signature valid, but token expiration timestamp has passed)
    """
    if not token:
        return None, "MALFORMED"

    # Fast-path cache lookup for pre-validated tokens (<0.001ms)
    cached = _VERIFIED_TOKEN_CACHE.get(token)
    if cached is not None:
        payload, exp = cached
        if time.time() <= exp:
            return payload, None
        else:
            _VERIFIED_TOKEN_CACHE.pop(token, None)
            return None, "EXPIRED"

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None, "MALFORMED"

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        expected_sig = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()

        try:
            actual_sig = _b64_decode(sig_b64)
        except Exception:
            return None, "TAMPERED"

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None, "TAMPERED"

        try:
            payload = json.loads(_b64_decode(payload_b64).decode("utf-8"))
        except Exception:
            return None, "MALFORMED"

        if not isinstance(payload, dict):
            return None, "MALFORMED"

        exp = payload.get("exp", 0)
        if time.time() > exp:
            return None, "EXPIRED"

        _VERIFIED_TOKEN_CACHE[token] = (payload, exp)
        return payload, None
    except Exception:
        return None, "MALFORMED"

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def pep_reverse_proxy(path: str, request: Request):
    start_time = time.perf_counter()
    
    # 1. Extract and Validate Bearer Token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication Failed: Missing Bearer Agent Passport",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    token = auth_header.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication Failed: Missing Bearer Agent Passport",
            headers={"WWW-Authenticate": "Bearer"}
        )

    agent_claims, auth_error = verify_agent_passport_detailed(token)
    if auth_error == "EXPIRED":
        raise HTTPException(
            status_code=401,
            detail="Authentication Failed: Agent Passport Expired",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token expired"'}
        )
    elif auth_error == "MALFORMED":
        raise HTTPException(
            status_code=401,
            detail="Authentication Failed: Malformed Agent Passport",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token is malformed"'}
        )
    elif auth_error == "TAMPERED" or not agent_claims:
        raise HTTPException(
            status_code=403,
            detail="Security Denial: Tampered or Invalid Agent Passport Signature"
        )
        
    agent_id = agent_claims.get("agent_id")
    agent_role = agent_claims.get("role")
    if not agent_id or not agent_role:
        raise HTTPException(
            status_code=403,
            detail="Security Denial: Unauthorized Agent Passport Claims"
        )
    
    # Normalize path cleanly & get HTTP method
    clean_path = path.strip("/")
    normalized_path = "/" + clean_path
    method = request.method

    # 2. Check Kill-Switch (<0.2ms)
    if KillSwitch.is_quarantined(agent_id):
        pep_lat = round((time.perf_counter() - start_time) * 1000, 2)
        telemetry_producer.emit_event(
            agent_id=agent_id,
            role=agent_role,
            endpoint=normalized_path,
            method=method,
            governor_status="QUARANTINED",
            risk_score=1.0,
            pep_latency_ms=pep_lat,
            violation_reason="Terminated by automated kill-switch",
            xai_factors=["Terminated by automated kill-switch"]
        )
        save_audit_log(
            agent_id=agent_id,
            role=agent_role,
            endpoint=normalized_path,
            method=method,
            risk_score=1.0,
            decision="QUARANTINED",
            xai_reasons=["Terminated by automated kill-switch"],
            latency_ms=pep_lat
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

    # 4. Deterministic Database-Backed Policy Check (Dynamic In-Memory Cache)
    policy_eval = policy_engine.evaluate(
        agent_id=agent_id,
        role=agent_role,
        endpoint=normalized_path,
        method=method
    )
    if not policy_eval.get("allowed", True):
        violation_reason = policy_eval.get("violation_reason") or "POLICY VIOLATION: Access denied by Zero-Trust Governance Policy."
        pep_lat = round((time.perf_counter() - start_time) * 1000, 2)
        telemetry_producer.emit_event(
            agent_id=agent_id,
            role=agent_role,
            endpoint=normalized_path,
            method=method,
            governor_status="BLOCKED",
            risk_score=0.90,
            pep_latency_ms=pep_lat,
            payload_preview=body_text,
            violation_reason=violation_reason,
            xai_factors=[violation_reason]
        )
        save_audit_log(
            agent_id=agent_id,
            role=agent_role,
            endpoint=normalized_path,
            method=method,
            risk_score=0.90,
            decision="BLOCKED",
            xai_reasons=[violation_reason],
            latency_ms=pep_lat
        )
        raise HTTPException(status_code=403, detail=violation_reason)

    # 5. Behavioral ML Risk Evaluation (Member 2's Engine)
    risk_score = 0.10
    try:
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
            pep_lat = round((time.perf_counter() - start_time) * 1000, 2)
            ml_factors = risk_result.get("factors", ["ML Behavioral Anomaly Detected"])
            telemetry_producer.emit_event(
                agent_id=agent_id,
                role=agent_role,
                endpoint=normalized_path,
                method=method,
                governor_status="QUARANTINED",
                risk_score=risk_score,
                pep_latency_ms=pep_lat,
                payload_preview=body_text,
                violation_reason=detail_msg,
                xai_factors=ml_factors
            )
            save_audit_log(
                agent_id=agent_id,
                role=agent_role,
                endpoint=normalized_path,
                method=method,
                risk_score=risk_score,
                decision="QUARANTINED",
                xai_reasons=ml_factors,
                latency_ms=pep_lat
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
            req_obj = TransferRequest(source_account="401", destination_account="402", amount_inr=5000.0, remarks="Virtual Assistant Wire Transfer")
        response_data = execute_wire_transfer(req_obj)
    elif normalized_path == "/customers/export":
        response_data = export_all_customer_data()
    else:
        raise HTTPException(status_code=404, detail=f"Upstream banking endpoint '{normalized_path}' not found")

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    allowed_xai = ["Nominal behavioral risk profile and authorized passport"]
    telemetry_producer.emit_event(
        agent_id=agent_id,
        role=agent_role,
        endpoint=normalized_path,
        method=method,
        governor_status="ALLOWED",
        risk_score=risk_score,
        pep_latency_ms=latency_ms,
        payload_preview=body_text,
        xai_factors=allowed_xai
    )
    save_audit_log(
        agent_id=agent_id,
        role=agent_role,
        endpoint=normalized_path,
        method=method,
        risk_score=risk_score,
        decision="ALLOWED",
        xai_reasons=["Nominal behavioral risk profile and authorized passport"],
        latency_ms=latency_ms
    )
    return {
        "governor_status": "ALLOWED",
        "pep_latency_ms": latency_ms,
        "agent_id": agent_id,
        "role": agent_role,
        "risk_score": risk_score,
        "upstream_data": response_data
    }

# Eagerly pre-warm PEP components on import to eliminate cold-start latency spikes
try:
    _warmup_token = NHITokenManager.mint_agent_token("Agent-Prewarm-00", "tier1_customer_service")
    verify_agent_passport_detailed(_warmup_token)
    KillSwitch.is_quarantined("Agent-Prewarm-00")
    policy_engine.evaluate("Agent-Prewarm-00", "tier1_customer_service", "/accounts/401/balance", "GET")
    evaluate_agent_request("Agent-Prewarm-00", "/accounts/401/balance", "", "GET")
    get_account_balance("401")
    get_bank_faqs()
except Exception:
    pass