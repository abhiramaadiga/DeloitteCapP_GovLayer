"""
Verification test suite for:
1. DB-backed authentication and salted PBKDF2 password verification.
2. JWT token minting/verification with AES-Fernet encrypted claims.
3. OAuth2 /api/v1/auth/token and /api/v1/auth/me endpoints.
4. Cryptographic encryption and decryption endpoints.
5. Multi-tenant customer accounts (401, 402, 403) with distinct balances and multiple FDs.
6. Per-user agent fleet isolation: quarantining Agent-Support-401 does not affect Agent-Support-402 or Agent-Support-403.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.auth import (
    hash_password,
    verify_password,
    encrypt_data,
    decrypt_data,
    mint_user_token,
    verify_user_token,
)
from backend.core.database import (
    verify_user_credentials,
    get_user_by_username,
    get_account_from_db,
    get_account_deposits_from_db,
    reset_seeded_users,
    reset_seeded_deposits,
    reset_seeded_accounts,
)
from backend.core.killswitch import KillSwitch

client = TestClient(app)


def setup_function():
    reset_seeded_users()
    reset_seeded_deposits()
    reset_seeded_accounts()
    KillSwitch.lift_quarantine("Agent-Support-401", "Reset before test", "TEST")
    KillSwitch.lift_quarantine("Agent-Support-402", "Reset before test", "TEST")
    KillSwitch.lift_quarantine("Agent-Support-403", "Reset before test", "TEST")


def test_password_hashing_and_db_verification():
    # 1. Direct PBKDF2 verification
    p_hash, p_salt = hash_password("Password@123")
    assert verify_password("Password@123", p_hash, p_salt) is True
    assert verify_password("WrongPassword", p_hash, p_salt) is False

    # 2. Database credential query for seeded users
    user_401 = verify_user_credentials("401", "banking123")
    assert user_401 is not None
    assert user_401["username"] == "401"
    assert user_401["account_id"] == "401"
    assert user_401["role"] == "customer"

    # Wrong password fails
    assert verify_user_credentials("401", "WrongPass") is None

    # Admin user verification
    admin_user = verify_user_credentials("admin", "soc2026")
    assert admin_user is not None
    assert admin_user["role"] == "admin"


def test_aes_encryption_and_decryption():
    import json
    secret_payload = {"account_id": "402", "tier": "PLATINUM", "clearance": "RESTRICTED"}
    encrypted = encrypt_data(secret_payload)
    assert isinstance(encrypted, str)
    assert "PLATINUM" not in encrypted  # Ciphertext hides plaintext

    decrypted = decrypt_data(encrypted)
    assert json.loads(decrypted) == secret_payload


def test_jwt_token_with_encrypted_claims():
    token = mint_user_token(
        username="rahul",
        role="customer",
        account_id="401",
        extra_claims={"pan": "ABCDE1234F", "tier": "GOLD"}
    )
    payload = verify_user_token(token)
    assert payload["sub"] == "rahul"
    assert payload["role"] == "customer"
    assert payload["account_id"] == "401"
    assert payload["decrypted_claims"]["tier"] == "GOLD"
    assert payload["decrypted_claims"]["pan"] == "ABCDE1234F"


def test_oauth2_token_endpoint():
    # OAuth2 standard password flow
    res = client.post(
        "/api/v1/auth/token",
        data={"username": "402", "password": "banking123"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["token_type"] == "bearer"
    token = data["access_token"]
    assert len(token) > 20

    # Invalid credentials
    res_bad = client.post(
        "/api/v1/auth/token",
        data={"username": "402", "password": "WrongPassword"}
    )
    assert res_bad.status_code == 401


def test_crypto_api_endpoints():
    token = mint_user_token("admin", "admin", "admin")
    headers = {"Authorization": f"Bearer {token}"}

    test_data = {"customer_pan": "ABCDE9876Z", "account_id": "403"}
    enc_res = client.post("/api/v1/crypto/encrypt", json={"data": test_data}, headers=headers)
    assert enc_res.status_code == 200
    ciphertext = enc_res.json()["ciphertext"]
    assert "ABCDE9876Z" not in ciphertext

    dec_res = client.post("/api/v1/crypto/decrypt", json={"ciphertext": ciphertext}, headers=headers)
    assert dec_res.status_code == 200
    assert dec_res.json()["plaintext"] == test_data


def test_multitenant_user_sessions_and_distinct_deposits():
    # Check 401
    bal_401 = client.get("/api/v1/accounts/401/balance").json()
    dep_401 = client.get("/api/v1/accounts/401/deposits").json()
    assert bal_401["balance_inr"] == 84250.0
    assert dep_401["total_deposits_inr"] == 500000.0
    assert len(dep_401["deposits"]) == 1

    # Check 402 (Platinum user with 3 distinct FDs)
    bal_402 = client.get("/api/v1/accounts/402/balance").json()
    dep_402 = client.get("/api/v1/accounts/402/deposits").json()
    assert bal_402["balance_inr"] == 312400.0
    assert dep_402["total_deposits_inr"] == 2350000.0
    assert len(dep_402["deposits"]) == 3

    # Check 403 (Silver user with 2 distinct FDs)
    bal_403 = client.get("/api/v1/accounts/403/balance").json()
    dep_403 = client.get("/api/v1/accounts/403/deposits").json()
    assert bal_403["balance_inr"] == 15000.0
    assert dep_403["total_deposits_inr"] == 80000.0
    assert len(dep_403["deposits"]) == 2


def test_user_wise_agent_fleet_isolation():
    # User-specific agents
    agent_401 = "Agent-Support-401"
    agent_402 = "Agent-Support-402"
    agent_403 = "Agent-Support-403"

    # Initially all are active
    assert KillSwitch.is_quarantined(agent_401) is False
    assert KillSwitch.is_quarantined(agent_402) is False
    assert KillSwitch.is_quarantined(agent_403) is False

    # Quarantine agent for User 401 (e.g. Rahul triggered an anomaly)
    KillSwitch.quarantine_agent(agent_401, "Suspicious query burst detected for user 401", 0.92)

    # Verify 401 is quarantined
    assert KillSwitch.is_quarantined(agent_401) is True

    # Crucial tenant isolation guarantee: Agent for 402 and 403 must remain completely active!
    assert KillSwitch.is_quarantined(agent_402) is False
    assert KillSwitch.is_quarantined(agent_403) is False

    # Admin fleet endpoint correctly reflects the quarantined status for 401 while 402 and 403 are Active
    fleet_res = client.get("/api/v1/agents/fleet")
    assert fleet_res.status_code == 200
    fleet_data = fleet_res.json()["agents"]
    
    status_map = {a["agent_id"]: a["status"] for a in fleet_data}
    assert status_map["Agent-Support-401"] == "QUARANTINED"
    assert status_map["Agent-Support-402"] == "ACTIVE"
    assert status_map["Agent-Support-403"] == "ACTIVE"
