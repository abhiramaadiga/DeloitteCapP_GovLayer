"""
High-speed policy evaluator for the BFSI Agentic-AI Identity & Access Governor.

Primary path: delegate to a running OPA server (POST /v1/data/bfsi/authz).
Fallback path: a native Python re-implementation of the same rules, used
when the OPA server is unreachable, so the PEP never fails open.
"""

import json
import os
import time
from dataclasses import dataclass, field

import requests

OPA_URL = os.environ.get("OPA_URL", "http://localhost:8181/v1/data/bfsi/authz")
OPA_TIMEOUT_SECONDS = 0.05  # fail fast, fall back to native path

_LIMITS_PATH = os.path.join(
    os.path.dirname(__file__), "data", "transaction_limits.json"
)
with open(_LIMITS_PATH) as f:
    TRANSACTION_LIMITS = json.load(f)


@dataclass
class PolicyDecision:
    allow: bool
    deny_reasons: list = field(default_factory=list)
    source: str = "opa"  # "opa" or "native_fallback"
    latency_ms: float = 0.0


def evaluate(input_doc: dict) -> PolicyDecision:
    start = time.perf_counter()
    try:
        resp = requests.post(
            OPA_URL, json={"input": input_doc}, timeout=OPA_TIMEOUT_SECONDS
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        decision = PolicyDecision(
            allow=result.get("allow", False),
            deny_reasons=sorted(result.get("deny_reasons", [])),
            source="opa",
        )
    except (requests.RequestException, ValueError):
        decision = _evaluate_native(input_doc)
        decision.source = "native_fallback"
    decision.latency_ms = (time.perf_counter() - start) * 1000
    return decision


def _evaluate_native(input_doc: dict) -> PolicyDecision:
    """Pure-Python mirror of bfsi_authz.rego. Fail-closed: any unrecognized
    role/endpoint denies, matching the Rego's default-deny behavior."""
    reasons = []
    role = input_doc.get("role")
    endpoint = input_doc.get("endpoint", "")
    method = input_doc.get("method")

    if input_doc.get("is_quarantined"):
        reasons.append("SECURITY_QUARANTINE_ACTIVE")

    if role == "tier1_customer_service" and endpoint.startswith("/transfers/"):
        reasons.append("SOX404_UNAUTHORIZED_FINANCIAL_TRANSFER")

    if role == "tier1_customer_service" and "/deposits/liquidate" in endpoint:
        reasons.append("UNAUTHORIZED_ASSET_LIQUIDATION")

    if endpoint == "/customers/export" and role != "admin_agent":
        reasons.append("PCIDSS_PROHIBITED_BULK_PII_EXPORT")

    if role == "payment_execution_bot":
        amount = input_doc.get("amount", 0)
        max_amount = input_doc.get("max_transaction_amount", 0)
        if amount > max_amount:
            reasons.append("TRANSACTION_LIMIT_EXCEEDED")
        role_limit = TRANSACTION_LIMITS.get(role)
        if role_limit is not None and max_amount != role_limit:
            reasons.append("CLAIM_LIMIT_MISMATCH")

    if role == "tier1_customer_service" and method != "GET":
        reasons.append("UNAUTHORIZED_HTTP_METHOD")

    if input_doc.get("payload_bytes", 0) > 65536:
        reasons.append("PAYLOAD_SIZE_LIMIT_EXCEEDED")

    if endpoint.startswith("/accounts/") and role != "admin_agent":
        if input_doc.get("account_owner_id") != input_doc.get("customer_id"):
            reasons.append("RESOURCE_OWNERSHIP_VIOLATION")

    allow = len(reasons) == 0 and _role_has_permission(input_doc)
    return PolicyDecision(allow=allow, deny_reasons=sorted(set(reasons)))


def _role_has_permission(input_doc: dict) -> bool:
    role = input_doc.get("role")
    method = input_doc.get("method")
    endpoint = input_doc.get("endpoint", "")

    if role == "tier1_customer_service":
        return method == "GET" and _is_support_safe_endpoint(endpoint)
    if role == "payment_execution_bot":
        return (
            method == "POST"
            and endpoint.startswith("/transfers/")
            and input_doc.get("amount", 0) <= input_doc.get("max_transaction_amount", 0)
        )
    if role == "wealth_advisor_bot":
        return method == "GET" and endpoint.startswith("/accounts/")
    if role == "admin_agent":
        return True
    return False


def _is_support_safe_endpoint(ep: str) -> bool:
    if ep == "/faq":
        return True
    if ep.startswith("/accounts/") and ep.endswith("/balance"):
        return True
    if ep.startswith("/accounts/") and ep.endswith("/deposits"):
        return True
    return False
