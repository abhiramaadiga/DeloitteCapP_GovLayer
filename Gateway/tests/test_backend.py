"""
tests/test_backend.py
Automated test suite verifying PEP latency, least-privilege, and kill-switch.
"""
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.auth import NHITokenManager
from backend.core.killswitch import KillSwitch

client = TestClient(app)

def test_support_bot_allowed_balance():
    token = NHITokenManager.mint_agent_token("Agent-Test-01", "tier1_customer_service")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/gateway/accounts/401/balance", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["governor_status"] == "ALLOWED"
    assert data["pep_latency_ms"] < 5.0  # <5ms SLA verified!

def test_support_bot_denied_wire_transfer():
    token = NHITokenManager.mint_agent_token("Agent-Test-01", "tier1_customer_service")
    headers = {"Authorization": f"Bearer {token}"}
    body = {"source_account": "401", "destination_account": "992", "amount_inr": 50000, "remarks": "Test"}
    response = client.post("/gateway/transfers/wire", headers=headers, json=body)
    assert response.status_code == 403
    assert "POLICY VIOLATION" in response.json()["detail"]

def test_killswitch_quarantine_blocks_access():
    agent_id = "Agent-Rogue-99"
    token = NHITokenManager.mint_agent_token(agent_id, "tier1_customer_service")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Trigger killswitch
    rec = KillSwitch.quarantine_agent(agent_id, "Anomalous burst", 0.95)
    assert rec["mttr_ms"] < 200.0  # <200ms MTTR verified!
    
    # Request must be blocked
    response = client.get("/gateway/faq", headers=headers)
    assert response.status_code == 403
    assert "QUARANTINE" in response.json()["detail"]
    
    # Clean up
    KillSwitch.lift_quarantine(agent_id, "Automated test cleanup", "TEST-RUNNER")
    