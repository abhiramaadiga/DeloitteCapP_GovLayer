# Project: Apex Commercial Bank Zero-Trust Agentic-AI Governor Regression & Verification

## Architecture
The system is composed of:
1. **Frontend SPA** (`Gateway/frontend`): React 19 + Vite 8 + Tailwind CSS. Provides Customer Portal (Account Balances, FDs, Floating Chat Assistant, Ledger) and Cyber SOC Admin Dashboard (Live Threat Speedometer, ML Drift Retrain, pgAdmin Database Explorer, Policy Management, User-wise Agent Fleet View).
2. **FastAPI Application Gateway & PEP** (`Gateway/backend`):
   - PEP Interceptor (`backend/pep/gateway.py`): Reverse proxy evaluating token authenticity, killswitch status (<0.2ms), policy rules (<0.05ms), and behavioral ML risk score (<15ms).
   - Core Policy Engine (`backend/core/policy_engine.py`): Database-backed rules with in-memory caching and sub-5ms evaluation SLA.
   - Behavioral ML Engine (`backend/ml/risk_engine.py`): Isolation Forest with Shannon entropy, velocity, Markov jump score, and payload size guardrails.
   - Killswitch Engine (`backend/core/killswitch.py`): Instant agent quarantine and FFIEC-compliant analyst reinstatement.
   - Auth & Crypto Engine (`backend/core/auth.py`): PBKDF2 password hashing, OAuth2 JWT tokens, and AES-Fernet encryption/decryption.
   - Core Banking Microservices (`backend/api/mock_banking.py`): Multi-tenant accounts (401, 402, 403), fixed deposits, and transaction ledgers.
3. **Automated Test Infrastructure**: Pytest suite in `Gateway/tests/` running on root Python environment `D:\Work\Deloite_Capstone_Project\venv\Scripts\python.exe`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Policy Enforcement Point (PEP) Pipeline | 7-stage zero-trust request evaluation with sub-5ms fast-path latency | M1 | Survey / R1 |
| 2 | Dynamic Policy Engine & In-Memory Cache | Database-backed rules (SOX-404, Banking-Gov, etc.) with sub-0.05ms cache lookup | M1 | Survey / R1 |
| 3 | Behavioral ML Risk Scoring | Scikit-Learn Isolation Forest with entropy, velocity, transition guardrail floors | M1 | Survey / R1 |
| 4 | Real-Time Killswitch Quarantine & Reinstatement | Immediate agent revocation (<0.2ms) and FFIEC analyst justification workflow | M1 | Survey / R1 |
| 5 | Adversarial Boundary Defense | Prompt injection interception, token signature tampering, high-entropy exfiltration blocks | M1 | Survey / R1 |
| 6 | PBKDF2 Salted Password Hashing | 100,000 iterations PBKDF2-HMAC-SHA256 with 16-byte random salts | M2 | Survey / R2 |
| 7 | OAuth2 Password Flow & JWT Tokens | `/api/v1/auth/token` issuing tokens with Fernet-encrypted claims and HTTP 401 rejections | M2 | Survey / R2 |
| 8 | Protected Session Profile (`/auth/me`) | Dependency-injected user context validation with claims decryption | M2 | Survey / R2 |
| 9 | AES-Fernet Cryptographic Payload Endpoints | `/api/v1/crypto/encrypt` & `/api/v1/crypto/decrypt` with tamper rejection | M2 | Survey / R2 |
| 10 | Seeded Personas Authentication | Verification of `admin/soc2026`, Rahul `401`, Priya `402`, Vikram `403` | M2 | Survey / R2 |
| 11 | Multi-Tenant Balances & Financial Ledger | Strict isolation for Account 401 (₹84,250), 402 (₹312,400), 403 (₹15,000) | M3 | Survey / R3 |
| 12 | Multi-Tenant Fixed Deposit Portfolios | Portfolio segregation: 401 (1 FD ₹500k), 402 (3 FDs ₹2.35M), 403 (2 FDs ₹80k) | M3 | Survey / R3 |
| 13 | Per-User Virtual Assistant Fleet Isolation | Quarantining `Agent-Support-401` leaves `Agent-Support-402` and `403` operational | M3 | Survey / R3 |
| 14 | Customer Portal UI/UX | Dynamic asset loading, responsive floating chatbot, and real-time transaction ledger | M4 | Survey / R4 |
| 15 | Cyber SOC Admin Dashboard UI/UX | Live SVG threat gauge, ML drift retrain section, database explorer grid, policy editor | M4 | Survey / R4 |
| 16 | User-Wise Agent Fleet View UI/UX | Individual isolation cards, one-click quarantine/reinstate controls | M4 | Survey / R4 |
| 17 | Frontend Build & Multi-Tenant Cleanliness | Clean `npm run build` and remediation of hardcoded account references in modals | M4 | Survey / R4 |
| 18 | Concurrency & Flake Resolution | Eliminate SQLite WAL database reset locking in pytest suite | M5 | Survey / R5 |
| 19 | Missing Package Manifest Synchronization | Update `Gateway/requirements.txt` with SQLAlchemy, cryptography, python-multipart | M5 | Survey / R5 |
| 20 | Unified Automated Regression Script | Automated runner executing full test suite and generating unified pass/fail results | M5 | Survey / R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend Security & Policy Gateway (R1) | Features 1-5: PEP pipeline, policy engine, ML risk engine, killswitch, adversarial tests | none | IN_PROGRESS |
| M2 | Authentication & Cryptography (R2) | Features 6-10: PBKDF2 hashing, OAuth2 tokens, `/auth/me`, Fernet crypto endpoints | none | PLANNED |
| M3 | Multi-Tenant Ledger & Agent Isolation (R3) | Features 11-13: Account balances, FD portfolios, and dedicated assistant isolation | M2 | PLANNED |
| M4 | Frontend Functionality & Build (R4) | Features 14-17: Fix modal hardcodings, verify Customer Portal, SOC Dashboard, Fleet cards, verify `npm run build` | M3 | PLANNED |
| M5 | Zero-Defect Resolution & Automated Regression Runner (R5) | Features 18-20: Fix test concurrency flakes, sync requirements, deliver unified regression runner, 100% pass verification | M1, M2, M3, M4 | PLANNED |

## Interface Contracts

### PEP Gateway ↔ Policy Engine
- `evaluate_policy(agent_id: str, action: str, resource: str, context: dict) -> PolicyDecision`
- Cache Lookup: sub-0.05ms in-memory dictionary backed by SQLite/PostgreSQL `policies` table.
- Decisions: `ALLOW`, `DENY`. Denials trigger HTTP 403.

### PEP Gateway ↔ ML Risk Engine
- `compute_risk_score(agent_id: str, payload: str, endpoint: str) -> float`
- Features: Shannon entropy, velocity RPS, Markov transition jump score, payload length.
- Threshold: >= 0.75 triggers quarantine & HTTP 403.
- Deterministic Guardrails: Entropy > 4.8 bits -> 0.80 floor; Velocity > 10 RPS -> 0.78 floor; Markov violation -> 0.82 floor; Payload > 4000 bytes -> 0.76 floor.

### PEP Gateway ↔ Killswitch
- `is_quarantined(agent_id: str) -> bool`
- Instant lookup (<0.2ms).
- Reinstatement: requires analyst ID and formal justification string.

### Auth Engine ↔ Core Banking
- `get_current_user(token: str = Depends(oauth2_scheme)) -> UserProfile`
- Encrypted claims decrypted via Fernet key.
- Rejection: HTTP 401 for expired, missing, or signature-tampered tokens.

## Code Layout
- Backend Gateway: `Gateway/backend/`
  - `backend/main.py`: FastAPI root entrypoint and routing
  - `backend/pep/gateway.py`: Zero-Trust PEP interceptor
  - `backend/core/policy_engine.py`: Dynamic policy rules
  - `backend/core/killswitch.py`: Quarantine status and audit
  - `backend/core/auth.py`: PBKDF2 hashing and JWT token handling
  - `backend/core/crypto.py`: AES-Fernet cryptographic operations
  - `backend/ml/risk_engine.py`: Behavioral Isolation Forest and guardrails
  - `backend/api/mock_banking.py`: Core banking ledger, accounts 401, 402, 403
- Backend Tests: `Gateway/tests/`
  - `tests/test_backend.py`: PEP, policy rules, and core endpoints
  - `tests/test_auth_and_multitenancy.py`: OAuth2, PBKDF2, and multi-tenant ledger
  - `tests/test_ml_risk_engine.py`: ML features, guardrails, and retraining
  - `tests/test_kafka_consumer.py`: Audit logging pipeline
- Frontend SPA: `Gateway/frontend/`
  - `frontend/src/App.jsx`: Global session and routing
  - `frontend/src/views/CustomerPortal.jsx`: Customer portal view
  - `frontend/src/views/AdminDashboard.jsx`: Cyber SOC admin dashboard
  - `frontend/src/components/customer/`: Balance, FD, Chatbot, Ledger components
  - `frontend/src/components/admin/`: Threat gauge, Drift retrain, DB inspector, Policy editor, Fleet cards
  - `frontend/src/components/WireTransferModal.jsx`: Wire transfer modal
  - `frontend/src/components/LiquidateFdModal.jsx`: FD liquidation modal
- Python Environment: `D:\Work\Deloite_Capstone_Project\venv\`
- Unified Regression Runner: `Gateway/run_regression_suite.py`
