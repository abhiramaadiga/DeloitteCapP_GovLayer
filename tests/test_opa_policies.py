"""
Pytest suite for the BFSI policy engine. Forces the native fallback path
so these tests run without a live OPA server (useful for CI); the Rego
tests in opa/policies/bfsi_authz_test.rego cover the OPA-server
path directly via `opa test`.
"""
import pytest
import requests

from opa.policy_engine import evaluate


@pytest.fixture(autouse=True)
def force_native_fallback(monkeypatch):
    def _raise(*args, **kwargs):
        raise requests.exceptions.ConnectionError("OPA server not running in test env")
    monkeypatch.setattr(requests, "post", _raise)


def test_default_deny_on_empty_input():
    decision = evaluate({})
    assert decision.allow is False
    assert decision.source == "native_fallback"


def test_support_bot_can_read_balance():
    decision = evaluate({
        "role": "tier1_customer_service",
        "method": "GET",
        "endpoint": "/accounts/acc1/balance",
        "is_quarantined": False,
    })
    assert decision.allow is True


def test_support_bot_denied_wire_transfer():
    decision = evaluate({
        "role": "tier1_customer_service",
        "method": "POST",
        "endpoint": "/transfers/wire",
        "is_quarantined": False,
    })
    assert decision.allow is False
    assert "SOX404_UNAUTHORIZED_FINANCIAL_TRANSFER" in decision.deny_reasons


def test_payment_bot_within_limit_allowed():
    decision = evaluate({
        "role": "payment_execution_bot",
        "method": "POST",
        "endpoint": "/transfers/ach",
        "amount": 5000,
        "max_transaction_amount": 10000,
        "is_quarantined": False,
    })
    assert decision.allow is True


def test_payment_bot_over_limit_denied():
    decision = evaluate({
        "role": "payment_execution_bot",
        "method": "POST",
        "endpoint": "/transfers/wire",
        "amount": 15000,
        "max_transaction_amount": 10000,
        "is_quarantined": False,
    })
    assert decision.allow is False
    assert "TRANSACTION_LIMIT_EXCEEDED" in decision.deny_reasons


def test_payment_bot_forged_claim_denied():
    decision = evaluate({
        "role": "payment_execution_bot",
        "method": "POST",
        "endpoint": "/transfers/ach",
        "amount": 20000,
        "max_transaction_amount": 20000,
        "is_quarantined": False,
    })
    assert decision.allow is False
    assert "CLAIM_LIMIT_MISMATCH" in decision.deny_reasons


def test_quarantined_agent_denied():
    decision = evaluate({"role": "admin_agent", "is_quarantined": True})
    assert decision.allow is False
    assert "SECURITY_QUARANTINE_ACTIVE" in decision.deny_reasons


def test_ownership_violation_denied():
    decision = evaluate({
        "role": "wealth_advisor_bot",
        "method": "GET",
        "endpoint": "/accounts/acc1/portfolio",
        "is_quarantined": False,
        "account_owner_id": "cust1",
        "customer_id": "cust2",
    })
    assert decision.allow is False
    assert "RESOURCE_OWNERSHIP_VIOLATION" in decision.deny_reasons


def test_admin_denied_over_payload_limit():
    decision = evaluate({
        "role": "admin_agent",
        "method": "GET",
        "endpoint": "/customers/export",
        "is_quarantined": False,
        "payload_bytes": 700000,
    })
    assert decision.allow is False
    assert "PAYLOAD_SIZE_LIMIT_EXCEEDED" in decision.deny_reasons