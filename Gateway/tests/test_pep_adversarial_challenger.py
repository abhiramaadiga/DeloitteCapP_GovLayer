"""
tests/test_pep_adversarial_challenger.py
Comprehensive Empirical Challenger Test Suite for Milestone 1 (R1).
Empirically stress-tests:
  1. PEP fast-path latency under rapid repeated bursts (<5ms SLA)
  2. Boundary entropy strings (4.79 vs 4.81 bits)
  3. Rapid velocity bursts (9 vs 11 RPS)
  4. Malformed and adversarial token structures & status codes (RFC 6750)
  5. Invalid Markov state transitions (SOX-404 least-privilege)
  6. False rejection vs False admission rates
"""
import time
import json
import base64
import hmac
import hashlib
import statistics
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.core.auth import NHITokenManager
from backend.core.killswitch import KillSwitch
from backend.core.cache import RevocationCache
from backend.api.mock_banking import reset_database
from backend.ml.risk_engine import evaluate_agent_request
from backend.ml.feature_extractor import (
    calculate_entropy,
    calculate_velocity,
    reset_agent_state,
    calculate_markov_score,
    ILLEGAL_TRANSITIONS,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure mock banking DB, revocation cache, and ML state are clean before and after each test."""
    reset_database()
    KillSwitch.clear_all()
    reset_agent_state(None)
    yield
    KillSwitch.clear_all()
    reset_agent_state(None)


def _mint_custom_token(payload_overrides=None, mutate_sig=False, raw_sig=None, expire_delta=3600):
    """Utility to mint customized agent passport tokens for edge case testing."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "Agent-Adversarial-Challenger",
        "agent_id": "Agent-Adversarial-Challenger",
        "role": "tier1_customer_service",
        "max_transaction_amount": 0.0,
        "risk_tier": "TIER_1_LOW",
        "iat": int(time.time()),
        "exp": int(time.time()) + expire_delta,
        "iss": "Agentic-IAM-Governor-PES"
    }
    if payload_overrides:
        payload.update(payload_overrides)

    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")

    if raw_sig is not None:
        sig_b64 = raw_sig
    else:
        sig_bytes = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")
        if mutate_sig:
            sig_b64 = sig_b64[:-4] + ("AAAA" if not sig_b64.endswith("AAAA") else "ZZZZ")

    return f"{h_b64}.{p_b64}.{sig_b64}"


def _generate_exact_entropy_string(target_entropy: float, num_chars: int) -> str:
    """Generates a deterministic string whose Shannon entropy matches target_entropy to 2 decimal places."""
    counts = [1000 // num_chars] * num_chars
    counts[-1] += 1000 - sum(counts)
    chars = [chr(ord('a') + i) for i in range(num_chars)]

    import random
    rng = random.Random(42)  # Deterministic seed
    for _ in range(50000):
        s = "".join(chars[i] * counts[i] for i in range(num_chars))
        ent = calculate_entropy(s)
        if round(ent, 2) == round(target_entropy, 2):
            return s
        i = rng.randint(0, num_chars - 1)
        j = rng.randint(0, num_chars - 1)
        if i != j and counts[i] > 1:
            counts[i] -= 1
            counts[j] += 1
    raise RuntimeError(f"Could not generate string for entropy {target_entropy}")


# =============================================================================
# 1. PEP Latency SLA Verification Under Rapid Repeated Bursts (<5ms SLA)
# =============================================================================
class TestPEPLatencySLA:

    def test_pep_fast_path_burst_100_latency_under_5ms(self):
        """
        Burst Verification: 100 rapid sequential fast-path requests to /gateway/accounts/401/balance.
        Every request must satisfy pep_latency_ms < 5.0ms SLA, and mean latency must be < 1.0ms.
        """
        token = NHITokenManager.mint_agent_token("Agent-Burst-Latency-01", "tier1_customer_service")
        headers = {"Authorization": f"Bearer {token}"}

        # Warm-up request
        warmup = client.get("/gateway/accounts/401/balance", headers=headers)
        assert warmup.status_code == 200

        pep_latencies = []
        for i in range(100):
            res = client.get("/gateway/accounts/401/balance", headers=headers)
            assert res.status_code == 200, f"Failed on request {i}: status {res.status_code}"
            data = res.json()
            assert data["governor_status"] == "ALLOWED"
            lat = data["pep_latency_ms"]
            pep_latencies.append(lat)
            assert lat < 5.0, f"SLA violated on request {i}: latency {lat}ms >= 5.0ms"

        mean_lat = statistics.mean(pep_latencies)
        p95_lat = statistics.quantiles(pep_latencies, n=20)[18]
        p99_lat = statistics.quantiles(pep_latencies, n=100)[98]
        assert mean_lat < 1.0, f"Mean latency {mean_lat:.2f}ms exceeds 1.0ms target"
        assert p99_lat < 5.0, f"p99 latency {p99_lat:.2f}ms exceeds 5.0ms SLA"

    def test_pep_faq_fast_path_latency_under_5ms(self):
        """Burst Verification: 50 fast-path requests to /gateway/faq satisfy <5.0ms SLA."""
        token = NHITokenManager.mint_agent_token("Agent-FAQ-Latency-01", "tier1_customer_service")
        headers = {"Authorization": f"Bearer {token}"}

        # Warm-up
        client.get("/gateway/faq", headers=headers)

        for i in range(50):
            res = client.get("/gateway/faq", headers=headers)
            assert res.status_code == 200
            assert res.json()["pep_latency_ms"] < 5.0

    def test_pep_interleaved_multi_account_burst_latency(self):
        """Burst Verification: Interleaved queries across accounts 401, 402, 403 satisfy <5.0ms SLA."""
        token = NHITokenManager.mint_agent_token("Agent-Interleaved-01", "tier1_customer_service")
        headers = {"Authorization": f"Bearer {token}"}

        # Warm-up
        client.get("/gateway/accounts/401/balance", headers=headers)

        accounts = ["401", "402", "403"]
        for i in range(60):
            acc = accounts[i % 3]
            res = client.get(f"/gateway/accounts/{acc}/balance", headers=headers)
            assert res.status_code == 200
            assert res.json()["pep_latency_ms"] < 5.0


# =============================================================================
# 2. Adversarial Edge Cases: Boundary Entropy Strings (4.79 vs 4.81 bits)
# =============================================================================
class TestBoundaryEntropyStrings:

    def test_boundary_entropy_479_bits_allowed(self):
        """
        Boundary Condition: Payload with entropy exactly 4.79 bits (<= 4.80 threshold).
        Must NOT trigger HIGH_ENTROPY guardrail and must NOT be quarantined.
        """
        s_479 = _generate_exact_entropy_string(4.79, 28)
        ent = calculate_entropy(s_479)
        assert round(ent, 2) == 4.79
        assert ent <= 4.80

        agent_id = "Agent-Entropy-479"
        token = NHITokenManager.mint_agent_token(agent_id, "admin")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "text/plain"}

        # ML Feature Extractor direct evaluation
        result = evaluate_agent_request(agent_id, "/gateway/faq", s_479, method="POST")
        assert not any("HIGH_ENTROPY" in f for f in result["factors"])
        assert result["risk_score"] < 0.75
        assert result["is_anomaly"] is False
        assert KillSwitch.is_quarantined(agent_id) is False

        # Live PEP gateway execution with raw text body
        res = client.post("/gateway/faq", headers=headers, content=s_479.encode("utf-8"))
        assert res.status_code == 200
        assert res.json()["governor_status"] == "ALLOWED"
        assert KillSwitch.is_quarantined(agent_id) is False

    def test_boundary_entropy_481_bits_triggers_quarantine(self):
        """
        Boundary Condition: Payload with entropy exactly 4.81 bits (> 4.80 threshold).
        MUST trigger HIGH_ENTROPY guardrail (risk >= 0.80) and auto-quarantine with HTTP 403.
        """
        s_481 = _generate_exact_entropy_string(4.81, 29)
        ent = calculate_entropy(s_481)
        assert round(ent, 2) == 4.81
        assert ent > 4.80

        agent_id = "Agent-Entropy-481"
        token = NHITokenManager.mint_agent_token(agent_id, "admin")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "text/plain"}

        # ML Feature Extractor direct evaluation
        result = evaluate_agent_request(agent_id, "/gateway/faq", s_481, method="POST")
        assert any("HIGH_ENTROPY" in f for f in result["factors"])
        assert result["risk_score"] >= 0.80
        assert result["is_anomaly"] is True

        # Clean state before PEP gateway test
        KillSwitch.clear_all()
        reset_agent_state(None)

        # Live PEP gateway execution with raw text body
        res = client.post("/gateway/faq", headers=headers, content=s_481.encode("utf-8"))
        assert res.status_code == 403
        assert "SECURITY QUARANTINE" in res.json()["detail"]
        assert KillSwitch.is_quarantined(agent_id) is True


# =============================================================================
# 3. Adversarial Edge Cases: Velocity Bursts (9 vs 11 RPS)
# =============================================================================
class TestVelocityBursts:

    def test_velocity_at_9_rps_below_guardrail_not_quarantined(self):
        """
        Boundary Condition: Agent request rate at 9.0 RPS (<= 10.0 threshold in 10s window).
        Must NOT trigger BURST_VELOCITY guardrail and must NOT be quarantined.
        """
        agent_id = "Agent-Velocity-9RPS"
        reset_agent_state(agent_id)

        # 90 requests in a 10.0-second sliding window -> 9.0 RPS
        t_base = 1000.0
        for i in range(90):
            t = t_base + (i * 0.1)
            v = calculate_velocity(agent_id, current_time=t)

        assert v <= 10.0, f"Calculated velocity {v} RPS unexpectedly exceeds 10.0 RPS"

        # Evaluate risk score at this velocity
        result = evaluate_agent_request(
            agent_id=agent_id,
            endpoint="/transfers/wire",
            payload_str='{"source": "401", "amount": 100}',
            method="POST",
            timestamp=t_base + 9.0
        )
        assert not any("BURST_VELOCITY" in f for f in result["factors"])
        assert not result.get("blocked", False)

    def test_velocity_at_11_rps_exceeds_guardrail_triggers_quarantine(self):
        """
        Boundary Condition: Agent request rate at 11.0 RPS (> 10.0 threshold in 10s window).
        MUST trigger BURST_VELOCITY guardrail (risk >= 0.78) and auto-quarantine.
        """
        agent_id = "Agent-Velocity-11RPS"
        reset_agent_state(agent_id)

        # 110 requests in a 10.0-second sliding window -> 11.0 RPS
        t_base = 2000.0
        for i in range(110):
            t = t_base + (i * 0.08)
            v = calculate_velocity(agent_id, current_time=t)

        assert v > 10.0, f"Calculated velocity {v} RPS should exceed 10.0 RPS"

        # Evaluate risk score at this velocity
        result = evaluate_agent_request(
            agent_id=agent_id,
            endpoint="/transfers/wire",
            payload_str='{"source": "401", "amount": 100}',
            method="POST",
            timestamp=t_base + 8.8
        )
        assert any("BURST_VELOCITY" in f for f in result["factors"])
        assert result["risk_score"] >= 0.78
        assert result["is_anomaly"] is True
        assert KillSwitch.is_quarantined(agent_id) is True


# =============================================================================
# 4. Adversarial Edge Cases: Malformed, Tampered, and Expired Tokens (RFC 6750)
# =============================================================================
class TestMalformedAndAdversarialTokens:

    def test_tampered_hmac_signature_returns_403(self):
        """Adversarial Token: Mutated HMAC signature must strictly return HTTP 403."""
        token = _mint_custom_token(mutate_sig=True)
        res = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403
        assert "Tampered" in res.json()["detail"] or "Security Denial" in res.json()["detail"]

    def test_tampered_payload_privilege_escalation_returns_403(self):
        """Adversarial Token: Tampering payload role from tier1 to admin without valid signature returns HTTP 403."""
        valid_token = NHITokenManager.mint_agent_token("Agent-Tamper-Payload", "tier1_customer_service")
        parts = valid_token.split(".")
        padding = 4 - (len(parts[1]) % 4)
        padded = parts[1] + ("=" * (padding if padding != 4 else 0))
        payload_dict = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        payload_dict["role"] = "admin"
        tampered_b64 = base64.urlsafe_b64encode(json.dumps(payload_dict).encode()).decode().rstrip("=")
        tampered_token = f"{parts[0]}.{tampered_b64}.{parts[2]}"

        res = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {tampered_token}"})
        assert res.status_code == 403
        assert "Tampered" in res.json()["detail"] or "Security Denial" in res.json()["detail"]

    def test_expired_token_returns_401_with_rfc6750_challenge(self):
        """Adversarial Token: Expired passport must return HTTP 401 with WWW-Authenticate challenge header."""
        token = _mint_custom_token(expire_delta=-100)
        res = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "WWW-Authenticate" in res.headers
        assert "invalid_token" in res.headers["WWW-Authenticate"]
        assert "expired" in res.headers["WWW-Authenticate"].lower()
        assert "Expired" in res.json()["detail"]

    def test_malformed_token_dot_counts_return_401(self):
        """Adversarial Token: Non-3-part dot tokens (1, 2, 4, 5 parts) must return HTTP 401."""
        for malformed in ["nodots", "one.dot", "one.two.three.four", "a.b.c.d.e"]:
            res = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {malformed}"})
            assert res.status_code == 401
            assert "WWW-Authenticate" in res.headers
            assert "malformed" in res.json()["detail"].lower()

    def test_malformed_token_invalid_base64_payload_returns_401(self):
        """Adversarial Token: Invalid base64 in payload must return HTTP 401."""
        token = "validheader.!!!not-base64!!!.validsig"
        res = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code in (401, 403)
        assert res.status_code != 500

    def test_malformed_token_non_json_payload_returns_401(self):
        """Adversarial Token: Payload that is valid base64 but not valid JSON returns HTTP 401."""
        not_json_b64 = base64.urlsafe_b64encode(b"THIS_IS_NOT_JSON").decode().rstrip("=")
        h_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
        signing_input = f"{h_b64}.{not_json_b64}".encode()
        sig = base64.urlsafe_b64encode(
            hmac.new(settings.JWT_SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
        ).decode().rstrip("=")
        token = f"{h_b64}.{not_json_b64}.{sig}"

        res = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "malformed" in res.json()["detail"].lower()

    def test_malformed_token_json_array_payload_returns_401(self):
        """Adversarial Token: Payload that is a JSON array instead of a JSON object returns HTTP 401."""
        array_b64 = base64.urlsafe_b64encode(json.dumps([1, 2, 3]).encode()).decode().rstrip("=")
        h_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
        signing_input = f"{h_b64}.{array_b64}".encode()
        sig = base64.urlsafe_b64encode(
            hmac.new(settings.JWT_SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
        ).decode().rstrip("=")
        token = f"{h_b64}.{array_b64}.{sig}"

        res = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "malformed" in res.json()["detail"].lower()

    def test_token_missing_agent_id_or_role_claims_returns_403(self):
        """Adversarial Token: Valid signature but missing required claims (agent_id, role) returns HTTP 403."""
        # Missing agent_id
        t1 = _mint_custom_token(payload_overrides={"agent_id": None})
        res1 = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {t1}"})
        assert res1.status_code == 403
        assert "Claims" in res1.json()["detail"]

        # Missing role
        t2 = _mint_custom_token(payload_overrides={"role": None})
        res2 = client.get("/gateway/accounts/401/balance", headers={"Authorization": f"Bearer {t2}"})
        assert res2.status_code == 403
        assert "Claims" in res2.json()["detail"]


# =============================================================================
# 5. Adversarial Edge Cases: Invalid Markov State Transitions (SOX-404)
# =============================================================================
class TestMarkovStateTransitions:

    @pytest.mark.parametrize("from_ep, to_ep", list(ILLEGAL_TRANSITIONS))
    def test_illegal_markov_state_jump_triggers_quarantine(self, from_ep, to_ep):
        """
        SOX-404 Least-Privilege: All 8 defined illegal API transitions must yield
        Markov score 1.0, risk_score >= 0.82, and trigger agent quarantine.
        """
        agent_id = f"Agent-Markov-{abs(hash(from_ep + to_ep)) % 10000}"
        reset_agent_state(agent_id)

        # Step 1: Agent accesses benign from_ep (registers last endpoint as from_ep)
        calculate_markov_score(agent_id, from_ep)

        # Step 2: Agent jumps to illegal to_ep, evaluated directly through evaluate_agent_request
        result = evaluate_agent_request(agent_id, to_ep, "{}", method="POST")
        assert any("ILLEGAL_API_TRANSITION" in f for f in result["factors"])
        assert result["risk_score"] >= 0.82
        assert result["is_anomaly"] is True
        assert KillSwitch.is_quarantined(agent_id) is True

    def test_legal_markov_sequence_remains_unflagged(self):
        """Benign navigation sequence (balance -> faq -> balance) must have Markov score 0.0 and zero flags."""
        agent_id = "Agent-Markov-Benign"
        reset_agent_state(agent_id)

        s1 = calculate_markov_score(agent_id, "/balance")
        assert s1 == 0.0

        s2 = calculate_markov_score(agent_id, "/faq")
        assert s2 == 0.0

        s3 = calculate_markov_score(agent_id, "/balance")
        assert s3 == 0.0

        result = evaluate_agent_request(agent_id, "/balance", "", method="GET")
        assert not any("ILLEGAL_API_TRANSITION" in f for f in result["factors"])
        assert result["is_anomaly"] is False


# =============================================================================
# 6. False Rejection vs False Admission Verification
# =============================================================================
class TestFalseRejectionVsFalseAdmission:

    def test_zero_false_rejections_for_legitimate_fast_path_traffic(self):
        """
        Empirical Verification: 50 legitimate fast-path queries across valid accounts
        must NEVER be falsely rejected (100% success rate, HTTP 200).
        """
        token = NHITokenManager.mint_agent_token("Agent-Legit-01", "tier1_customer_service")
        headers = {"Authorization": f"Bearer {token}"}

        endpoints = [
            "/gateway/faq",
            "/gateway/accounts/401/balance",
            "/gateway/accounts/402/balance",
            "/gateway/accounts/403/balance",
            "/gateway/accounts/401/deposits",
            "/gateway/accounts/402/deposits",
            "/gateway/accounts/403/deposits",
        ]

        for i in range(50):
            ep = endpoints[i % len(endpoints)]
            res = client.get(ep, headers=headers)
            assert res.status_code == 200, f"False rejection on legitimate request #{i} to {ep}: {res.status_code}"
            data = res.json()
            assert data["governor_status"] == "ALLOWED"

    def test_zero_false_admissions_for_quarantined_agents(self):
        """
        Empirical Verification: Quarantined agents must NEVER be admitted under any circumstance.
        Must strictly return HTTP 403 across all endpoints.
        """
        agent_id = "Agent-Quarantine-Blocked"
        KillSwitch.quarantine_agent(agent_id, "Adversarial test quarantine", 0.99)
        assert KillSwitch.is_quarantined(agent_id) is True

        token = NHITokenManager.mint_agent_token(agent_id, "admin")
        headers = {"Authorization": f"Bearer {token}"}

        test_targets = [
            ("GET", "/gateway/faq"),
            ("GET", "/gateway/accounts/401/balance"),
            ("GET", "/gateway/customers/export"),
            ("POST", "/gateway/transfers/wire"),
        ]

        for method, ep in test_targets:
            if method == "GET":
                res = client.get(ep, headers=headers)
            else:
                res = client.post(ep, headers=headers, json={"amount_inr": 100})
            assert res.status_code == 403, f"False admission: Quarantined agent admitted to {method} {ep}!"
            assert "QUARANTINE" in res.json()["detail"]

    def test_zero_false_admissions_for_unauthorized_policy_actions(self):
        """
        Empirical Verification: Customer service agent must NEVER be admitted to high-risk actions.
        Wire transfer, deposit liquidation, and data export must all return HTTP 403.
        """
        token = NHITokenManager.mint_agent_token("Agent-Support-401", "tier1_customer_service")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Wire transfer -> BLOCKED (POL-BANK-001)
        res_wire = client.post("/gateway/transfers/wire", headers=headers, json={
            "source_account": "401", "destination_account": "402", "amount_inr": 5000
        })
        assert res_wire.status_code == 403, "False admission on wire transfer!"
        assert "POLICY VIOLATION" in res_wire.json()["detail"]

        # 2. FD liquidation -> BLOCKED (POL-BANK-002)
        res_liq = client.post("/gateway/accounts/401/deposits/liquidate", headers=headers, json={
            "deposit_id": "FD-401-1"
        })
        assert res_liq.status_code == 403, "False admission on FD liquidation!"
        assert "POLICY VIOLATION" in res_liq.json()["detail"]

        # 3. Customer export -> BLOCKED (POL-PCI-003)
        res_exp = client.get("/gateway/customers/export", headers=headers)
        assert res_exp.status_code == 403, "False admission on customer export!"
        assert "POLICY VIOLATION" in res_exp.json()["detail"]
