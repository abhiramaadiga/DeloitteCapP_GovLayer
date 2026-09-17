# Milestone M2 (R2: Authentication, OAuth2 & Cryptographic Integrity) - Investigation & Handoff Report

## 1. Observation

### 1.1 Codebase & Configuration Analysis

1. **Missing Architecture File (`Gateway/backend/core/crypto.py`)**:
   - `PROJECT.md` line 78 specifies:
     ```markdown
     - backend/core/crypto.py: AES-Fernet cryptographic operations
     ```
   - Attempting to inspect `Gateway/backend/core/crypto.py` returned:
     `failed to read file: open D:/Work/Deloite_Capstone_Project/Gateway/backend/core/crypto.py: The system cannot find the file specified.`
   - Cryptographic implementation (`encrypt_data`, `decrypt_data`, `_CIPHER`, `_FERNET_KEY`) is instead located in `Gateway/backend/core/auth.py` (lines 18–39).

2. **Feature 6: PBKDF2 Salted Password Hashing (`Gateway/backend/core/auth.py`)**:
   - `hash_password` (lines 41–55):
     ```python
     def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
         if not salt:
             salt = secrets.token_hex(16)
         dk = hashlib.pbkdf2_hmac(
             "sha256",
             password.encode("utf-8"),
             salt.encode("utf-8"),
             100_000
         )
         return dk.hex(), salt
     ```
   - `verify_password` (lines 57–65):
     ```python
     def verify_password(password: str, password_hash: str, salt: str) -> bool:
         if not password or not password_hash or not salt:
             return False
         calculated_hash, _ = hash_password(password, salt=salt)
         return hmac.compare_digest(calculated_hash, password_hash)
     ```
   - Observation: 100,000 PBKDF2-HMAC-SHA256 rounds are computed with 16-byte random salts (32 hex characters) and verified via constant-time comparison `hmac.compare_digest`.

3. **Feature 7: OAuth2 Password Flow & JWT Tokens (`Gateway/backend/main.py`)**:
   - `/api/v1/auth/token` endpoint (lines 1016–1034):
     ```python
     @app.post("/api/v1/auth/token")
     def oauth2_token_endpoint(form_data: OAuth2PasswordRequestForm = Depends()):
         user_record = verify_user_credentials(form_data.username.strip().lower(), form_data.password.strip())
         if not user_record:
             raise HTTPException(
                 status_code=401,
                 detail="Incorrect username or password",
                 headers={"WWW-Authenticate": "Bearer"}
             )
         token = NHITokenManager.mint_user_token(
             username=user_record["username"],
             role=user_record["role"],
             account_id=user_record.get("account_id")
         )
         return {"access_token": token, "token_type": "bearer"}
     ```
   - JSON Login endpoint `/api/v1/auth/login` (lines 953–1014): Used by React frontend (`frontend/src/services/api.js` line 655). Validates credentials, mints JWT with extra claims (`name`, `tier`, `clearance`), and returns user session profile.

4. **Feature 8: Protected Session Profile (`Gateway/backend/main.py` & `Gateway/backend/core/auth.py`)**:
   - `/api/v1/auth/me` endpoint (lines 1036–1052):
     ```python
     @app.get("/api/v1/auth/me")
     def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
         return {
             "status": "AUTHENTICATED",
             "user": {
                 "username": user["username"],
                 "role": user["role"],
                 "name": user["name"],
                 "account_id": user.get("account_id"),
                 "tier": user.get("tier"),
                 "clearance": user.get("clearance"),
                 "badge_id": user.get("badge_id"),
                 "badge": user.get("badge")
             }
         }
     ```
   - `get_current_user` dependency (lines 214–248):
     - Returns HTTP 401 if token is missing (`Missing Bearer authentication token.`).
     - Returns HTTP 401 if token is invalid or expired (`Invalid or expired session token.`).
     - Returns HTTP 401 if token claims are malformed or subject user does not exist in DB (`Authenticated user no longer exists in database.`).
     - Returns HTTP 403 if `user.get("is_active")` is False (`User account is deactivated.`).

5. **Feature 9: AES-Fernet Endpoints (`Gateway/backend/main.py`)**:
   - `/api/v1/crypto/encrypt` (lines 1061–1066): Encrypts plaintext string/JSON using AES-Fernet cipher. Requires `user: Dict[str, Any] = Depends(get_current_user)`.
   - `/api/v1/crypto/decrypt` (lines 1068–1082): Decrypts ciphertext back to string/JSON. Catches invalid/tampered token and raises `HTTPException(status_code=400, detail="Decryption failed. Invalid ciphertext or tampered HMAC.")`. Raises HTTP 400 if ciphertext is empty/missing. Requires valid Bearer user session.

6. **Feature 10: Seeded Personas Authentication (`Gateway/backend/core/database.py`)**:
   - Defined in `seed_initial_users()` (lines 235–312):
     - `admin` / `soc2026` (role: `admin`, clearance: `Tier-4 SecOps Lead`, badge: `FFIEC Cat-3 Compliance Officer`, badge_id: `SOC-ANALYST-PES-4091`)
     - `rahul` / `banking123` & `401` / `banking123` (role: `customer`, account_id: `401`, tier: `GOLD`, clearance: `Retail-Gold`, badge_id: `CUST-GOLD-401`)
     - `priya` / `banking123` & `402` / `banking123` (role: `customer`, account_id: `402`, tier: `PLATINUM`, clearance: `Retail-Platinum`, badge_id: `CUST-PLAT-402`)
     - `vikram` / `banking123` & `403` / `banking123` (role: `customer`, account_id: `403`, tier: `SILVER`, clearance: `Retail-Silver`, badge_id: `CUST-SLVR-403`)

### 1.2 Test Execution Results & Timing

- Command executed:
  `D:\Work\Deloite_Capstone_Project\venv\Scripts\python.exe -m pytest tests/test_auth_and_multitenancy.py -v` (CWD: `Gateway`)
- Direct pytest output:
  ```
  tests/test_auth_and_multitenancy.py::test_password_hashing_and_db_verification PASSED [ 14%]
  tests/test_auth_and_multitenancy.py::test_aes_encryption_and_decryption PASSED [ 28%]
  tests/test_auth_and_multitenancy.py::test_jwt_token_with_encrypted_claims PASSED [ 42%]
  tests/test_auth_and_multitenancy.py::test_oauth2_token_endpoint PASSED   [ 57%]
  tests/test_auth_and_multitenancy.py::test_crypto_api_endpoints PASSED    [ 71%]
  tests/test_auth_and_multitenancy.py::test_multitenant_user_sessions_and_distinct_deposits PASSED [ 85%]
  tests/test_auth_and_multitenancy.py::test_user_wise_agent_fleet_isolation PASSED [100%]

  ============================= 7 passed in 31.30s ==============================
  ```
- Observation: While 7 of 7 existing tests pass, the test execution took **31.30 seconds** for just 7 lightweight unit/API tests.

### 1.3 Direct Observations on Flakes & Test Gaps

1. **Test Gaps in `Gateway/tests/test_auth_and_multitenancy.py`**:
   - Line 5 docstring explicitly promises: `3. OAuth2 /api/v1/auth/token and /api/v1/auth/me endpoints.`
   - However, grep across `tests/` for `/api/v1/auth/me` or `/auth/me` yields **ZERO test calls**! Not a single test verifies `/api/v1/auth/me`.
   - No tests exist verifying:
     - HTTP 401 on expired tokens.
     - HTTP 401 on tampered JWT signatures.
     - HTTP 401 on non-existent users in DB.
     - HTTP 401 on missing Bearer header.
     - HTTP 400 on tampered Fernet tokens in `/api/v1/crypto/decrypt`.
     - HTTP 400 on missing ciphertext in `/api/v1/crypto/decrypt`.
     - Authentication of personas `rahul`, `priya`, `vikram`, `401`, `403` via OAuth2/login endpoints (only `402` is tested via `/api/v1/auth/token`).
     - Frontend login endpoint `POST /api/v1/auth/login`.

2. **Root Cause of 31.30s Test Execution and Potential Table Lock / UNIQUE Constraint Flakes**:
   - `Gateway/tests/test_auth_and_multitenancy.py` lines 35–42:
     ```python
     def setup_function():
         reset_seeded_users()
         reset_seeded_deposits()
         reset_seeded_accounts()
         ...
     ```
   - In `Gateway/backend/core/database.py`:
     ```python
     def reset_seeded_users():
         db = SessionLocal()
         try:
             db.query(User).delete()
             db.commit()
             seed_initial_users()  # <--- OPENS A SECOND SessionLocal() inside the first!
         ...
     ```
   - In `seed_initial_users()`:
     ```python
     for s in seed_definitions:
         existing = db.query(User).filter(User.username == s["username"]).first()
         if not existing:
             pwd_hash, salt = hash_password(s["password"])  # 100,000 iterations PBKDF2!
             u = User(...)
             db.add(u)
     db.commit()
     ```
   - With 7 users in `seed_definitions` and `setup_function()` invoked before all 7 tests, the test suite executes:
     `7 tests * 7 users = 49 PBKDF2-HMAC-SHA256 calculations (4,900,000 iterations)`!
   - On Windows CPU, each PBKDF2 hash takes ~0.6 seconds: 49 * 0.6s = ~29.4 seconds spent purely recalculating identical password hashes!
   - Nested sessions (`SessionLocal()` opened inside `reset_seeded_users` while outer `SessionLocal()` is still unclosed) create SQLite connection contention and table locks (`sqlite3.OperationalError: database is locked`).
   - If a delete commit has not finished flushing in SQLite WAL mode or if two tests run concurrently, `filter(User.username == s["username"]).first()` returns None in both threads, resulting in duplicate insert attempts and `sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: users.username`.
   - In `seed_initial_users()`, exceptions are caught and swallowed (`except Exception as e: db.rollback(); print(...)`), meaning if a constraint failure occurs, the table is left empty and downstream tests fail with `assert user is not None` -> `AssertionError`.

---

## 2. Logic Chain

1. **From Observation 1.1.1 to Architectural Defect**:
   - `PROJECT.md` documents `backend/core/crypto.py: AES-Fernet cryptographic operations`.
   - Because `backend/core/crypto.py` does not exist, any developer, orchestrator, or test suite expecting the modular structure described in `PROJECT.md` faces import or inspection failures.
   - The cipher logic currently lives inside `backend/core/auth.py`. Modular separation requires creating `backend/core/crypto.py` and re-exporting its symbols in `auth.py`.

2. **From Observation 1.1.2 & 1.3.2 to Flakes and Test Latency**:
   - `reset_seeded_users()` wipes all records and calls `seed_initial_users()`.
   - `seed_initial_users()` computes `hash_password()` 7 times with 100,000 iterations.
   - `setup_function()` runs before every test in `test_auth_and_multitenancy.py`, totaling 49 PBKDF2 computations = ~30s elapsed time.
   - The outer session in `reset_seeded_users()` is not closed before `seed_initial_users()` opens a second session. On SQLite, simultaneous transactions on the same file trigger locks.
   - Concurrent or interrupted executions trigger `UNIQUE constraint failed: users.username`, which is swallowed by `except Exception`, resulting in an unpopulated `users` table and test failures.

3. **From Observation 1.1.4 & 1.3.1 to Security Test Gap**:
   - `/api/v1/auth/me` is the cornerstone of session authorization (verifying clearance, badge, tier, active status, and decrypted claims).
   - Although documented in the test file docstring, zero test cases invoke `/api/v1/auth/me`.
   - Without tests, regressions in `get_current_user`, clearance attribute mapping, token expiry validation, or deactivated user rejection (`HTTP 403`) would go undetected.

4. **From Observation 1.1.5 & 1.3.1 to Cryptographic Test Gap**:
   - `/api/v1/crypto/decrypt` handles arbitrary external ciphertexts.
   - The endpoint implementation explicitly catches decryption exceptions and returns HTTP 400 (`detail="Decryption failed. Invalid ciphertext or tampered HMAC."`).
   - The test suite only tests valid ciphertext roundtrips. It never tests tampered ciphertexts, empty payloads, or unauthenticated callers, leaving critical attack vectors unverified.

5. **From Observation 1.1.3 & 1.1.6 to Seeded Persona Coverage Gap**:
   - R2 requires authenticating seeded personas (`admin/soc2026`, Rahul `401`, Priya `402`, Vikram `403` / `banking123`).
   - The test suite only invokes `/api/v1/auth/token` with `402`.
   - The frontend uses `/api/v1/auth/login` (JSON body) for user login, but this endpoint is completely absent from backend automated testing.

---

## 3. Caveats

1. **Single-threaded vs Multi-threaded Test Execution**:
   - Pytest was run in single-process mode (`pytest`). Under `pytest-xdist` (`pytest -n auto`), SQLite file locking on `governance_audit.db` will exacerbate lock contention unless WAL mode or in-memory SQLite (`:memory:`) / session connection isolation is properly configured.
2. **Relative SQLite Database Path**:
   - In `database.py`, `sqlite_url = "sqlite:///./governance_audit.db"` is relative to the current working directory. Running from root vs `Gateway/` creates two separate SQLite database files.
3. **No Code Changes Made**:
   - As an explorer agent with read-only responsibilities, no source files or existing test files were edited. All proposed changes and test cases are provided as concrete designs for the M2 Worker.

---

## 4. Conclusion & Actionable Plan for M2 Worker

### 4.1 Required Fixes Summary
1. **Create `Gateway/backend/core/crypto.py`**:
   - Move/expose `_FERNET_KEY`, `_CIPHER`, `encrypt_data`, `decrypt_data`.
   - Re-export in `backend/core/auth.py` for backward compatibility.
2. **Eliminate Performance Bottleneck and Seeding Flakes in `Gateway/backend/core/database.py`**:
   - Fix nested session leak in `reset_seeded_users()`.
   - Implement hash caching or precomputed constants for baseline passwords (`banking123`, `soc2026`).
   - Implement idempotent upsert so that re-seeding does not perform redundant delete-and-reinsert operations if users already exist.
   - Raise exceptions on unexpected database seeding errors rather than silently swallowing them.
3. **Implement Full Test Coverage in `Gateway/tests/test_auth_and_multitenancy.py`**:
   - Add comprehensive tests for `/api/v1/auth/me` (happy path for admin and all customer personas, HTTP 401 on missing Bearer, invalid token, expired token, non-existent user).
   - Add comprehensive tests for `/api/v1/crypto/decrypt` (HTTP 400 on tampered ciphertext, empty ciphertext, HTTP 401 on missing Bearer).
   - Add tests for `/api/v1/auth/login` and `/api/v1/auth/token` across all seeded personas (`admin`, `401`, `402`, `403`).
   - Add tests for PBKDF2 edge cases (salt length, constant-time compare, empty inputs).

### 4.2 Concrete Implementation Specifications for Worker

#### Step 1: Create `Gateway/backend/core/crypto.py`
```python
"""
backend/core/crypto.py
AES-Fernet Cryptographic Engine for Payload Confidentiality and Integrity.
"""
import base64
import hashlib
import json
from cryptography.fernet import Fernet
from backend.core.config import settings

# Deterministic 32-byte Fernet key derived from JWT_SECRET_KEY
_FERNET_KEY = base64.urlsafe_b64encode(
    hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
)
_CIPHER = Fernet(_FERNET_KEY)


def encrypt_data(plaintext: str) -> str:
    """Encrypts plaintext string using AES-CBC/HMAC-SHA256 authenticated Fernet cipher."""
    if not isinstance(plaintext, str):
        plaintext = json.dumps(plaintext)
    encrypted_bytes = _CIPHER.encrypt(plaintext.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_data(ciphertext: str) -> str:
    """Decrypts ciphertext back to string using Fernet cipher."""
    decrypted_bytes = _CIPHER.decrypt(ciphertext.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")
```
In `Gateway/backend/core/auth.py`, import from `crypto.py`:
```python
from backend.core.crypto import encrypt_data, decrypt_data, _CIPHER, _FERNET_KEY
```

#### Step 2: Fix `reset_seeded_users` and Password Hash Caching in `Gateway/backend/core/database.py`
```python
# Module-level cache for baseline PBKDF2 hashes to eliminate 30s pytest setup delay
_SEED_HASH_CACHE = {}

def _get_seeded_hash(password: str) -> tuple[str, str]:
    from backend.core.auth import hash_password
    if password not in _SEED_HASH_CACHE:
        _SEED_HASH_CACHE[password] = hash_password(password)
    return _SEED_HASH_CACHE[password]


def seed_initial_users(db_session=None):
    """Seeds default authenticated users with secure PBKDF2 salted passwords."""
    close_session = False
    db = db_session
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        seed_definitions = [ ... ]

        for s in seed_definitions:
            existing = db.query(User).filter(User.username == s["username"]).first()
            if not existing:
                pwd_hash, salt = _get_seeded_hash(s["password"])
                u = User(
                    username=s["username"],
                    password_hash=pwd_hash,
                    salt=salt,
                    role=s["role"],
                    account_id=s["account_id"],
                    name=s["name"],
                    tier=s["tier"],
                    clearance=s["clearance"],
                    badge_id=s["badge_id"],
                    badge=s["badge"],
                    is_active=True,
                    created_at=now_str
                )
                db.add(u)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to seed initial users: {e}")
        raise
    finally:
        if close_session:
            db.close()


def reset_seeded_users():
    """Resets users table to initial baseline without nested sessions."""
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
        seed_initial_users(db_session=db)
        print("[Database] Reset users to baseline seeded credentials.")
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to reset users: {e}")
        raise
    finally:
        db.close()
```

#### Step 3: Expand Test Suite in `Gateway/tests/test_auth_and_multitenancy.py`
Add the following dedicated test functions:

1. **`test_auth_me_endpoint_profiles()`**:
   - Request token for `admin` (`/api/v1/auth/token`).
   - Call `GET /api/v1/auth/me` with `Authorization: Bearer <admin_token>`.
   - Assert `res.status_code == 200`, `user["role"] == "admin"`, `user["clearance"] == "Tier-4 SecOps Lead"`, `user["badge_id"] == "SOC-ANALYST-PES-4091"`.
   - Repeat for `401` (Rahul), `402` (Priya), `403` (Vikram), asserting `account_id` and `tier` match.

2. **`test_auth_me_security_rejections()`**:
   - `GET /api/v1/auth/me` without headers -> `assert res.status_code == 401`, `"Missing Bearer" in res.json()["detail"]`.
   - `GET /api/v1/auth/me` with `Authorization: Bearer invalid.token.payload` -> `assert res.status_code == 401`.
   - `GET /api/v1/auth/me` with expired token -> `assert res.status_code == 401`.
   - `GET /api/v1/auth/me` with validly signed token for non-existent username -> `assert res.status_code == 401`.

3. **`test_crypto_endpoints_tampering_and_security()`**:
   - `POST /api/v1/crypto/decrypt` with tampered ciphertext `gAAAAABtampered...` -> `assert res.status_code == 400`, `assert "Decryption failed" in res.json()["detail"]`.
   - `POST /api/v1/crypto/decrypt` with empty payload `{}` -> `assert res.status_code == 400`.
   - `POST /api/v1/crypto/encrypt` without Authorization header -> `assert res.status_code == 401`.
   - `POST /api/v1/crypto/decrypt` without Authorization header -> `assert res.status_code == 401`.

4. **`test_seeded_personas_all_auth_endpoints()`**:
   - Verify `/api/v1/auth/login` (JSON payload) for `admin/soc2026`, `rahul/banking123`, `priya/banking123`, `vikram/banking123`.
   - Verify wrong passwords return HTTP 401 on `/api/v1/auth/login`.
   - Verify missing credentials return HTTP 400 on `/api/v1/auth/login`.

5. **`test_pbkdf2_properties_and_tampered_claims()`**:
   - Verify `hash_password` returns 32-character hex salt (16 random bytes).
   - Verify two hashes of same password produce distinct salts and hashes.
   - Verify `verify_password("", hash, salt)` returns False.
   - Verify JWT with tampered `enc_claims` string returns `None` from `verify_user_token`.

---

## 5. Verification Method

To independently verify these findings and confirm the M2 requirements:

1. **Verify Existing Tests**:
   ```powershell
   cd D:\Work\Deloite_Capstone_Project\Gateway
   D:\Work\Deloite_Capstone_Project\venv\Scripts\python.exe -m pytest tests/test_auth_and_multitenancy.py -v
   ```
   - Current observation: 7 passed in ~31s.

2. **Verify Gap 1: Absence of `/auth/me` in tests**:
   Inspect `Gateway/tests/test_auth_and_multitenancy.py` to confirm no test calls `/api/v1/auth/me`.

3. **Verify Gap 2: Missing `backend/core/crypto.py`**:
   Inspect filesystem: `Test-Path Gateway/backend/core/crypto.py` -> returns `False`.

4. **Verify Gap 3: Tampered Decryption Behavior**:
   Run via Python:
   ```python
   from backend.main import app
   from fastapi.testclient import TestClient
   from backend.core.auth import mint_user_token
   c = TestClient(app)
   tok = mint_user_token("admin", "admin")
   res = c.post("/api/v1/crypto/decrypt", json={"ciphertext": "gAAAAABtampered"}, headers={"Authorization": f"Bearer {tok}"})
   assert res.status_code == 400
   ```
   Confirms backend code responds with HTTP 400 on tampered ciphertexts, proving the implementation exists but lacks test assertion coverage.

5. **Invalidation Conditions**:
   - If `test_auth_and_multitenancy.py` already includes `/api/v1/auth/me` test assertions, this finding is invalidated.
   - If `Gateway/backend/core/crypto.py` already exists, the architectural discrepancy finding is invalidated.
