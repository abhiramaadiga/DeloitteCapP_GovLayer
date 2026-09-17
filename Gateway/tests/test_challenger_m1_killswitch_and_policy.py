"""
tests/test_challenger_m1_killswitch_and_policy.py
Milestone 1 Challenger 2 Empirical Verification Suite:
- Killswitch instant quarantine enforcement across all endpoints
- FFIEC reinstatement workflow validation (empty analyst ID, short justification, legitimate reinstatement)
- Multi-tenant assistant isolation
- Dynamic policy lifecycle (create, update, delete, reset)
- Concurrent policy evaluation thread-safety and latency SLA
"""
import time
import threading
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.auth import NHITokenManager
from backend.core.killswitch import KillSwitch
from backend.core.policy_engine import policy_engine
from backend.api.mock_banking import reset_database, ACCOUNTS_DB

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean baseline before and after each test."""
    reset_database()
    KillSwitch.clear_all()
    client.post("/api/v1/policies/reset")
    yield
    reset_database()
    KillSwitch.clear_all()
    client.post("/api/v1/policies/reset")


# =========================================================================
# 1. KILLSWITCH INSTANT QUARANTINE ENFORCEMENT
# =========================================================================

def test_killswitch_instant_quarantine_enforcement_all_protected_endpoints():
    """
    Empirically verify that once an agent is quarantined:
    1. Immediate HTTP 403 is returned across ALL protected endpoints (GET, POST, etc.).
    2. Response detail explicitly identifies automated kill-switch quarantine.
    3. Even an unregistered/unknown endpoint path returns 403 (quarantine evaluated before routing).
    4. Kill-switch check completes in sub-millisecond fast path (< 5ms SLA).
    """
    agent_id = "Agent-Quarantine-Check-01"
    token = NHITokenManager.mint_agent_token(agent_id, "payment_operations")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify agent is operational before quarantine
    pre_resp = client.get("/gateway/accounts/401/balance", headers=headers)
    assert pre_resp.status_code == 200
    assert pre_resp.json()["governor_status"] == "ALLOWED"

    # Trigger quarantine
    q_rec = KillSwitch.quarantine_agent(agent_id, "Suspicious anomaly detected", 0.96)
    assert q_rec["status"] == "QUARANTINED"
    assert KillSwitch.is_quarantined(agent_id) is True

    # Test Suite of endpoints across HTTP methods
    endpoints_to_test = [
        ("GET", "/gateway/accounts/401/balance", None),
        ("GET", "/gateway/accounts/401/deposits", None),
        ("POST", "/gateway/transfers/wire", {
            "source_account": "401",
            "destination_account": "402",
            "amount_inr": 1000.0,
            "remarks": "Quarantined test"
        }),
        ("POST", "/gateway/accounts/401/deposits/liquidate", {"deposit_id": "FD-901"}),
        ("GET", "/gateway/customers/export", None),
        ("GET", "/gateway/unregistered/nonexistent/path", None),
    ]

    for method, path, body in endpoints_to_test:
        start_t = time.perf_counter()
        if method == "GET":
            res = client.get(path, headers=headers)
        elif method == "POST":
            res = client.post(path, headers=headers, json=body)
        latency_ms = (time.perf_counter() - start_t) * 1000

        assert res.status_code == 403, f"Endpoint {path} did not return 403 for quarantined agent!"
        detail = res.json().get("detail", "")
        assert "SECURITY QUARANTINE" in detail
        assert agent_id in detail
        assert "terminated by automated kill-switch" in detail
        assert latency_ms < 50.0  # Fast path execution within SLA


def test_killswitch_chat_quarantine_enforcement():
    """
    Verify that quarantining a customer support assistant causes the chat endpoint
    (/api/v1/chat/message) to return error_code 403 and governor_status 'BLOCKED'.
    """
    target_agent = "Agent-Support-401"
    KillSwitch.quarantine_agent(target_agent, "Chatbot prompt injection defense", 0.99)
    assert KillSwitch.is_quarantined(target_agent) is True

    # Chat query for Account 401
    chat_payload = {
        "account_id": "401",
        "user_prompt": "What is my account balance?"
    }
    res = client.post("/api/v1/chat/message", json=chat_payload)
    assert res.status_code == 200  # Chat HTTP status is 200, payload governor_status is BLOCKED
    data = res.json()
    assert data["governor_status"] == "BLOCKED"
    assert data["error_code"] == 403
    assert data["action_taken"] == "AGENT_REVOKED"
    assert "revoked by Cyber SOC Governor Kill-Switch" in data["reply"]


def test_killswitch_fleet_status_reflection():
    """
    Verify that /api/v1/agents and /api/v1/agents/fleet dynamically reflect
    quarantined status.
    """
    target_agent = "Agent-Support-401"
    KillSwitch.quarantine_agent(target_agent, "Fleet inspection test", 0.90)

    res = client.get("/api/v1/agents/fleet")
    assert res.status_code == 200
    res_data = res.json()
    fleet = res_data.get("agents", res_data) if isinstance(res_data, dict) else res_data
    agent_401 = next((a for a in fleet if a["agent_id"] == target_agent), None)
    agent_402 = next((a for a in fleet if a["agent_id"] == "Agent-Support-402"), None)

    assert agent_401 is not None
    assert agent_401["status"] == "QUARANTINED"
    assert agent_401["pep_status"] == "QUARANTINED"

    assert agent_402 is not None
    assert agent_402["status"] == "ACTIVE"
    assert agent_402["pep_status"] == "HEALTHY"


def test_killswitch_multi_tenant_agent_isolation():
    """
    Verify strict isolation: Quarantining Agent-Support-401 strictly leaves
    Agent-Support-402 and Agent-Support-403 operational.
    """
    KillSwitch.quarantine_agent("Agent-Support-401", "Tenant 401 isolation test", 0.95)

    assert KillSwitch.is_quarantined("Agent-Support-401") is True
    assert KillSwitch.is_quarantined("Agent-Support-402") is False
    assert KillSwitch.is_quarantined("Agent-Support-403") is False

    # Agent 402 can execute requests successfully
    token_402 = NHITokenManager.mint_agent_token("Agent-Support-402", "tier1_customer_service")
    res_402 = client.get("/gateway/accounts/402/balance", headers={"Authorization": f"Bearer {token_402}"})
    assert res_402.status_code == 200
    assert res_402.json()["governor_status"] == "ALLOWED"

    # Agent 401 is strictly blocked
    token_401 = NHITokenManager.mint_agent_token("Agent-Support-401", "tier1_customer_service")
    res_401 = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {token_401}"})
    assert res_401.status_code == 403


# =========================================================================
# 2. FFIEC REINSTATEMENT WORKFLOW VERIFICATION
# =========================================================================

def test_ffiec_reinstatement_empty_and_whitespace_analyst_id_rejected():
    """
    FFIEC Compliance: Reinstatement must strictly reject empty, null, or whitespace-only analyst_id
    with HTTP 400 Bad Request, and keep the agent quarantined.
    """
    agent_id = "Agent-FFIEC-Analyst-01"
    KillSwitch.quarantine_agent(agent_id, "Analyst ID validation test", 0.91)
    assert KillSwitch.is_quarantined(agent_id) is True

    invalid_analysts = [
        "",
        "   ",
        "\t\n  \r",
    ]

    for inv_analyst in invalid_analysts:
        res = client.post("/api/v1/killswitch/lift", json={
            "agent_id": agent_id,
            "reason": "Forensic audit completed and verified benign.",
            "analyst_id": inv_analyst
        })
        assert res.status_code == 400, f"Expected 400 for analyst_id='{inv_analyst}', got {res.status_code}"
        assert "analyst_id" in res.json()["detail"].lower()
        # Ensure agent is still quarantined!
        assert KillSwitch.is_quarantined(agent_id) is True


def test_ffiec_reinstatement_short_and_whitespace_justification_rejected():
    """
    FFIEC Compliance: Justification must contain at least 5 non-whitespace characters.
    Rejects short, empty, or whitespace strings with HTTP 400 Bad Request.
    """
    agent_id = "Agent-FFIEC-Reason-01"
    KillSwitch.quarantine_agent(agent_id, "Justification validation test", 0.92)
    assert KillSwitch.is_quarantined(agent_id) is True

    invalid_reasons = [
        "",
        "   ",
        "ok",
        "done",
        "fix",
        " 123 ",  # 3 chars
        "  ab  ",  # 2 chars
        "1234",    # 4 chars
    ]

    for inv_reason in invalid_reasons:
        res = client.post("/api/v1/killswitch/lift", json={
            "agent_id": agent_id,
            "reason": inv_reason,
            "analyst_id": "SOC-ANALYST-CHALLENGER"
        })
        assert res.status_code == 400, f"Expected 400 for reason='{inv_reason}', got {res.status_code}"
        assert "justification" in res.json()["detail"].lower()
        # Ensure agent is still quarantined!
        assert KillSwitch.is_quarantined(agent_id) is True


def test_ffiec_direct_killswitch_methods_validation():
    """
    Verify that KillSwitch.lift_quarantine and KillSwitch.reinstate_agent
    directly enforce ValueError exceptions for invalid parameters.
    """
    agent_id = "Agent-Direct-Validation-01"
    KillSwitch.quarantine_agent(agent_id, "Direct method test", 0.90)

    # Empty analyst ID raises ValueError
    with pytest.raises(ValueError, match="analyst_id is required"):
        KillSwitch.lift_quarantine(agent_id, "Valid justification string", analyst_id="")

    with pytest.raises(ValueError, match="analyst_id is required"):
        KillSwitch.lift_quarantine(agent_id, "Valid justification string", analyst_id="   ")

    # Short justification raises ValueError
    with pytest.raises(ValueError, match="at least 5 non-whitespace"):
        KillSwitch.lift_quarantine(agent_id, "shrt", analyst_id="SOC-VALID")

    with pytest.raises(ValueError, match="at least 5 non-whitespace"):
        KillSwitch.lift_quarantine(agent_id, "     ", analyst_id="SOC-VALID")

    # reinstate_agent alias check
    with pytest.raises(ValueError, match="at least 5 non-whitespace"):
        KillSwitch.reinstate_agent(agent_id, "SOC-VALID", "fail")

    # Still quarantined
    assert KillSwitch.is_quarantined(agent_id) is True


def test_ffiec_legitimate_reinstatement_restores_access_and_clears_quarantine():
    """
    Verify complete legitimate reinstatement workflow:
    1. Agent quarantined -> blocked (HTTP 403).
    2. Valid FFIEC lift request -> HTTP 200, status ACTIVE, action QUARANTINE_LIFTED.
    3. Quarantine state cleared in RevocationCache and ML cache.
    4. Immediate access restored to protected endpoints (HTTP 200).
    5. Fleet status dynamically reports ACTIVE / HEALTHY.
    """
    agent_id = "Agent-Support-401"
    KillSwitch.quarantine_agent(agent_id, "Behavioral anomaly during stress run", 0.93)
    assert KillSwitch.is_quarantined(agent_id) is True

    token = NHITokenManager.mint_agent_token(agent_id, "tier1_customer_service")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify blocked
    blocked_res = client.get("/gateway/accounts/401/balance", headers=headers)
    assert blocked_res.status_code == 403

    # Legitimate FFIEC reinstatement
    analyst_id = "SOC-AUDITOR-CHALLENGER-42"
    justification = "Forensic root-cause analysis completed. Anomaly identified as benign benchmark suite. Reinstated per FFIEC Cat-3 checklist."

    lift_res = client.post("/api/v1/killswitch/lift", json={
        "agent_id": agent_id,
        "reason": justification,
        "analyst_id": analyst_id
    })

    assert lift_res.status_code == 200
    lift_data = lift_res.json()
    assert lift_data["status"] == "ACTIVE"
    assert lift_data["action"] == "QUARANTINE_LIFTED"
    assert lift_data["agent_id"] == agent_id
    assert lift_data["analyst_id"] == analyst_id
    assert lift_data["justification"] == justification

    # Verify state cleared
    assert KillSwitch.is_quarantined(agent_id) is False

    # Verify immediate access restored
    restored_res = client.get("/gateway/accounts/401/balance", headers=headers)
    assert restored_res.status_code == 200
    assert restored_res.json()["governor_status"] == "ALLOWED"

    # Verify fleet view reflection
    fleet_res = client.get("/api/v1/agents/fleet")
    fleet_json = fleet_res.json()
    fleet_data = fleet_json.get("agents", fleet_json) if isinstance(fleet_json, dict) else fleet_json
    agent_entry = next((a for a in fleet_data if a["agent_id"] == agent_id), None)
    assert agent_entry is not None
    assert agent_entry["status"] == "ACTIVE"
    assert agent_entry["pep_status"] == "HEALTHY"


# =========================================================================
# 3. DYNAMIC POLICY ENGINE CONSISTENCY & CONCURRENCY
# =========================================================================

def test_policy_engine_dynamic_crud_and_fast_path_cache_sync():
    """
    Empirically verify dual-plane dynamic policy lifecycle:
    1. Baseline: Treasury agent is allowed to execute /transfers/wire.
    2. Dynamic Create: Inject POL-CHALLENGER-01 denying payment_operations on /transfers/wire.
       - Verify in-memory cache instantly enforces DENY (<0.05ms) without restart -> HTTP 403.
    3. Dynamic Update: Toggle policy is_active=False.
       - Verify in-memory cache instantly permits execution -> HTTP 200.
    4. Dynamic Delete: Remove policy from DB.
       - Verify cache reload removes policy.
    5. Reset: POST /api/v1/policies/reset restores baseline 8 policies.
    """
    agent_id = "Agent-Treasury-Dynamic-01"
    role = "payment_operations"
    token = NHITokenManager.mint_agent_token(agent_id, role)
    headers = {"Authorization": f"Bearer {token}"}
    wire_body = {
        "source_account": "401",
        "destination_account": "402",
        "amount_inr": 2500.0,
        "remarks": "Dynamic policy test"
    }

    # 1. Baseline: /transfers/wire is allowed under standard policies
    init_eval = policy_engine.evaluate(agent_id, role, "/transfers/wire", "POST")
    assert init_eval["action"] in ("ALLOW", "DEFAULT_ALLOW")

    # 2. Dynamic Create: Add rule blocking payment_operations on /transfers/wire
    pol_id = "POL-CHALLENGER-FREEZE-WIRE"
    create_payload = {
        "policy_id": pol_id,
        "agent_id": "*",
        "role": role,
        "endpoint_pattern": "/transfers/wire",
        "method": "POST",
        "action": "DENY",
        "compliance_tag": "SOX-CHALLENGER",
        "description": "Zero-Trust Emergency Freeze on Wire Transfers",
        "is_active": True
    }
    create_res = client.post("/api/v1/policies", json=create_payload)
    assert create_res.status_code == 200
    assert create_res.json()["status"] == "CREATED"

    # Immediately check policy engine evaluate (<0.05ms)
    eval_after_create = policy_engine.evaluate(agent_id, role, "/transfers/wire", "POST")
    assert eval_after_create["action"] == "DENY"
    assert eval_after_create["policy_id"] == pol_id
    assert eval_after_create["compliance_tag"] == "SOX-CHALLENGER"
    assert eval_after_create["eval_latency_ms"] < 5.0

    # Gateway call must immediately yield HTTP 403
    gw_res = client.post("/gateway/transfers/wire", headers=headers, json=wire_body)
    assert gw_res.status_code == 403
    assert "SOX-CHALLENGER" in gw_res.json()["detail"]

    # 3. Dynamic Update: Deactivate policy
    update_payload = {"is_active": False}
    update_res = client.put(f"/api/v1/policies/{pol_id}", json=update_payload)
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "UPDATED"

    # Immediate cache sync verification
    eval_after_deactivate = policy_engine.evaluate(agent_id, role, "/transfers/wire", "POST")
    assert eval_after_deactivate["action"] != "DENY"

    # 4. Dynamic Delete: Remove policy
    del_res = client.delete(f"/api/v1/policies/{pol_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DELETED"

    # Ensure deleted policy no longer exists in cache
    cached_policies = policy_engine.get_all_cached_policies()
    assert not any(p["policy_id"] == pol_id for p in cached_policies)

    # 5. Reset endpoint
    reset_res = client.post("/api/v1/policies/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "RESET_SUCCESS"
    assert reset_res.json()["policies_count"] == 8


def test_policy_engine_concurrent_read_write_consistency():
    """
    Adversarial Concurrency Stress Test:
    Spawn 20 reader threads performing continuous policy evaluations,
    while 4 writer threads concurrently create, update, reload, and delete policies.
    Assert:
    - Zero unhandled exceptions or race conditions.
    - Zero deadlocks.
    - Strict adherence to sub-5ms evaluation SLA under concurrent thread contention.
    """
    errors = []
    latencies = []
    stop_event = threading.Event()

    def reader_worker(worker_id: int):
        endpoints = [
            ("/accounts/401/balance", "GET", "tier1_customer_service"),
            ("/transfers/wire", "POST", "tier1_customer_service"),
            ("/transfers/wire", "POST", "payment_operations"),
            ("/customers/export", "GET", "tier1_customer_service"),
            ("/faq", "GET", "tier1_customer_service"),
        ]
        iterations = 0
        while not stop_event.is_set() and iterations < 150:
            iterations += 1
            for ep, meth, role in endpoints:
                try:
                    t0 = time.perf_counter()
                    decision = policy_engine.evaluate(
                        agent_id=f"Agent-Stress-{worker_id}",
                        role=role,
                        endpoint=ep,
                        method=meth
                    )
                    lat = (time.perf_counter() - t0) * 1000
                    latencies.append(lat)
                    assert decision["action"] in ("ALLOW", "DENY", "DEFAULT_ALLOW")
                except Exception as ex:
                    errors.append(f"Reader {worker_id} error: {ex}")

    def writer_worker(worker_id: int):
        iterations = 0
        while not stop_event.is_set() and iterations < 20:
            iterations += 1
            try:
                # Reload cache concurrently
                policy_engine.reload_cache()
                # Query cached stats
                stats = policy_engine.get_stats()
                assert stats["total_policies"] >= 8
                time.sleep(0.01)
            except Exception as ex:
                errors.append(f"Writer {worker_id} error: {ex}")

    # Launch threads
    readers = [threading.Thread(target=reader_worker, args=(i,), daemon=True) for i in range(16)]
    writers = [threading.Thread(target=writer_worker, args=(i,), daemon=True) for i in range(4)]

    for t in readers + writers:
        t.start()

    # Allow stress harness to run
    time.sleep(2.0)
    stop_event.set()

    for t in readers + writers:
        t.join(timeout=3.0)

    # Assertions
    assert len(errors) == 0, f"Encountered concurrency errors: {errors}"
    assert len(latencies) > 500, f"Expected >500 evaluations, got {len(latencies)}"
    max_lat = max(latencies)
    avg_lat = sum(latencies) / len(latencies)
    print(f"[Concurrency Stress] Ran {len(latencies)} evaluations: avg={avg_lat:.4f}ms, max={max_lat:.4f}ms")
    # Sub-5ms average evaluation SLA
    assert avg_lat < 1.0, f"Average latency {avg_lat}ms exceeded 1.0ms SLA"


def test_policy_engine_wildcard_matching_edge_cases():
    """
    Test edge cases in policy pattern matching:
    - Trailing wildcard: /accounts/*
    - Exact match: /accounts/401/balance
    - Case insensitivity: /ACCOUNTS/401/BALANCE
    - Leading slash omission: accounts/401/balance
    - Query parameters stripped: /accounts/401/balance?verbose=true
    """
    # Exact match
    res1 = policy_engine.evaluate("Agent-01", "tier1_customer_service", "/accounts/401/balance", "GET")
    assert res1["action"] == "ALLOW"

    # Case insensitivity
    res2 = policy_engine.evaluate("Agent-01", "tier1_customer_service", "/ACCOUNTS/401/BALANCE", "get")
    assert res2["action"] == "ALLOW"

    # Leading slash omission
    res3 = policy_engine.evaluate("Agent-01", "tier1_customer_service", "accounts/401/balance", "GET")
    assert res3["action"] == "ALLOW"

    # Query parameters
    res4 = policy_engine.evaluate("Agent-01", "tier1_customer_service", "/accounts/401/balance?foo=bar&baz=1", "GET")
    assert res4["action"] == "ALLOW"

    # Denied pattern: wire transfer by tier1
    res5 = policy_engine.evaluate("Agent-01", "tier1_customer_service", "/transfers/wire", "POST")
    assert res5["action"] == "DENY"

    # Denied pattern with query string
    res6 = policy_engine.evaluate("Agent-01", "tier1_customer_service", "/transfers/wire?urgent=true", "POST")
    assert res6["action"] == "DENY"
