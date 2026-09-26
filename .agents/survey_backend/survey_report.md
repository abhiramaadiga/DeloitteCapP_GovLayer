# Backend Architecture & Codebase Survey Report
**System**: Apex Commercial Bank Zero-Trust Agentic-AI Governor Gateway  
**Component**: Backend Microservices, PEP Reverse Proxy, ML Governance Engine & Persistence  
**Working Directory**: `D:\Work\Deloite_Capstone_Project\Gateway`  
**Date**: 2026-09-17  
**Author**: Backend Architecture Explorer (`survey_backend`)

---

## 1. Executive Summary

The backend of the **Apex Commercial Bank Zero-Trust Agentic-AI Governor** is a production-grade FastAPI microservice architecture designed to enforce deterministic least-privilege policies, behavioral anomaly detection, and sub-millisecond automated kill-switch revocations over autonomous Non-Human Identity (NHI) AI agents operating in retail banking.

Key Architectural Capabilities:
- **Dual-Plane Policy Enforcement**: A deterministic Policy Enforcement Point (PEP) executing in sub-5ms latency, backed by a persistent database (`governance_policies`) and synchronized with an ultra-fast in-memory L1 cache (<0.05ms evaluation).
- **Behavioral Machine Learning & XAI**: Scikit-Learn Isolation Forest calibrated via sigmoid mapping, fused with Shannon entropy analysis, sliding-window request velocity (RPS), and Markov chain sequence modeling to detect prompt injection, exfiltration bursts, and unauthorized API transitions.
- **FFIEC-Compliant Kill-Switch**: Dual-layer revocation cache (Redis + in-memory fallback) capable of sub-millisecond agent quarantine and requiring audited human justifications for reinstatement.
- **Enterprise Multi-Tenancy**: Complete tenant isolation across customer accounts (`401` Rahul Sharma, `402` Priya Patel, `403` Vikram Malhotra) with separate balances, multiple Fixed Deposit portfolios, and dedicated per-user virtual assistants (`Agent-Support-401`, `402`, `403`).
- **Resilient Dual-Mode Persistence**: Hybrid SQLAlchemy engine connecting to PostgreSQL 16.2 (`governance_db`) with automatic transparent fallback to SQLite WAL mode (`governance_audit.db`).
- **Test Suite Health**: 77 test cases across 4 test suites with 75 passing and 2 gracefully skipped (requiring live Docker daemon).

---

## 2. Codebase Directory Structure & File Map

```
D:\Work\Deloite_Capstone_Project\Gateway\
├── .env                       # Environment configuration (Postgres, Redis, Kafka, Secrets)
├── .env.example               # Template environment configuration
├── conftest.py                # Pytest root configuration (injects Gateway root into sys.path)
├── pytest.ini                 # Pytest filters and test path definitions
├── requirements.txt           # Python dependency specifications
├── schema.sql                 # PostgreSQL DDL System of Record (SoR) table schemas
├── governance_audit.db        # SQLite WAL fallback database (audit logs, policies, accounts)
├── Dockerfile                 # Container packaging for Gateway FastAPI service
├── docker-compose.yml         # Multi-container orchestration (Postgres, Redis, Kafka, Gateway, pgAdmin)
│
├── backend/                   # Core Python application package
│   ├── main.py                # FastAPI app root, lifecycle hooks, management & inspection APIs
│   │
│   ├── core/                  # Infrastructure and security services
│   │   ├── config.py          # Pydantic Settings class loading from .env
│   │   ├── database.py        # SQLAlchemy models (7 tables), engine factory, seed functions, DAL
│   │   ├── auth.py            # PBKDF2 password hashing, AES-Fernet encryption, JWT NHITokenManager
│   │   ├── cache.py           # Dual-tier RevocationCache (Redis + L1 in-memory dictionary)
│   │   ├── killswitch.py      # KillSwitch manager (quarantine, MTTR measurement, FFIEC reinstatement)
│   │   ├── policy_engine.py   # Dual-plane PolicyEngine with in-memory caching and wildcard matcher
│   │   └── kafka_producer.py  # Asynchronous non-blocking telemetry producer with ring buffer fallback
│   │
│   ├── ml/                    # Behavioral Machine Learning governance subsystem
│   │   ├── feature_extractor.py # Shannon entropy, sliding-window velocity, Markov sequence scorer
│   │   ├── risk_engine.py     # Composite risk evaluation, sigmoid calibration, hard-floor guardrails
│   │   ├── model_trainer.py   # Isolation Forest training script & dynamic RLHF retraining function
│   │   ├── kafka_consumer.py  # Telemetry stream consumer, drift detector, security alerting engine
│   │   └── models/            # Serialized model artifacts
│   │       └── isolation_forest.joblib # 100-estimator fitted model
│   │
│   ├── pep/                   # Zero-Trust Policy Enforcement Point
│   │   └── gateway.py         # Reverse proxy pipeline (token check -> killswitch -> policy -> ML -> core banking)
│   │
│   └── api/                   # Upstream simulated core banking microservices
│       └── mock_banking.py    # Multi-tenant accounts, multiple FDs, wire transfers, transactions ledger
│
├── tests/                     # Automated pytest test suites
│   ├── test_auth_and_multitenancy.py # PBKDF2, AES-Fernet, OAuth2, multi-tenant accounts & agent isolation
│   ├── test_backend.py        # PEP latency, kill-switch, database persistence, introspection, prompt defense
│   ├── test_kafka_consumer.py # Telemetry schemas, drift monitoring, security alerting, retraining buffer
│   └── test_ml_risk_engine.py # Entropy, velocity, Markov transitions, Isolation Forest, FFIEC un-quarantine
│
└── data/
    └── sample_events.json     # Pre-recorded synthetic telemetry events for testing and benchmarking
```

---

## 3. Architecture & Entry Points

### 3.1 Application Lifecycle (`backend/main.py`)
The application uses FastAPI's `lifespan` context manager:
1. **Startup (`lifespan`)**:
   - `init_db()`: Initializes table schema in PostgreSQL/SQLite and executes idempotent seeding for Users, Banking Accounts, Fixed Deposits, Transactions, and Baseline Governance Policies.
   - `policy_engine.reload_cache()`: Warms the in-memory policy cache from database records.
   - `_load_model()`: Pre-warms the Isolation Forest model into memory, running a synthetic inference to eliminate first-request cold-start latency.
   - `start_telemetry_consumer()`: Launches the background thread for the `GovernanceEventConsumer`.
2. **Shutdown**:
   - `stop_telemetry_consumer()`: Gracefully closes consumer threads and Kafka connections.

### 3.2 Infrastructure & Fallback Resilience
- **Database (`backend/core/database.py`)**: `_create_resilient_engine` tests TCP connectivity to PostgreSQL (`localhost:5432`). If unreachable within 3 seconds, it seamlessly falls back to `sqlite:///./governance_audit.db` configured with `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, and 30-second busy timeouts.
- **Cache (`backend/core/cache.py`)**: Checks for Redis on `localhost:6379`. If unreachable within 200ms, it falls back to a thread-safe in-memory Python dictionary (`_L1_CACHE`) with per-key TTL tracking.
- **Event Bus (`backend/core/kafka_producer.py`)**: TCP probes Kafka on `localhost:9092`. If unavailable within 100ms, events are buffered in an in-memory queue (`offline_queue`, maxsize 10,000) and broadcast to local fallback listeners without blocking API request threads.

---

## 4. Comprehensive Endpoint Catalog

### 4.1 System, Health & Diagnostic Endpoints
| Method | Path | Function | Auth | Purpose |
|---|---|---|---|---|
| `GET` | `/` | `root_endpoint` | None | Service metadata, online status, swagger links, and TCP connectivity diagnostics for PostgreSQL, Redis, and Kafka. |
| `GET` | `/healthz`, `/health` | `health_check` | None | Global system health status (`HEALTHY` or `DEGRADED`) and database connection status. |
| `GET` | `/api/v1/health/db` | `db_health_check` | None | Database health check reporting active engine URL (credentials masked) and PostgreSQL vs SQLite mode. |
| `GET` | `/api/v1/system/status` | `get_system_status_endpoint` | None | Real-time connectivity status of backend and container infrastructure for frontend badges. |
| `POST`| `/api/v1/system/reset` | `system_reset_endpoint` | None | Restores accounts, deposits, transactions, policies, killswitch states, and ML telemetry metrics to initial baseline. |

### 4.2 Database Introspection Endpoints (pgAdmin-like Data Grid)
| Method | Path | Function | Auth | Purpose |
|---|---|---|---|---|
| `GET` | `/api/v1/db/tables` | `list_database_tables` | None | Lists whitelisted tables (`audit_logs`, `conversations`, `banking_accounts`, `banking_transactions`, `governance_policies`) and their current row counts. |
| `GET` | `/api/v1/db/tables/{table}/schema` | `get_table_schema` | None | Returns column names, data types, nullability, and primary key flags for the table. |
| `GET` | `/api/v1/db/tables/{table}/rows` | `get_table_rows` | None | Returns paginated rows with sorting (`sort_column`, `sort_dir`) and case-insensitive substring search across all columns. |

### 4.3 Authentication, OAuth2 & Cryptography Endpoints
| Method | Path | Function | Auth | Purpose |
|---|---|---|---|---|
| `POST`| `/api/v1/auth/login` | `login_endpoint` | None | Authenticates username/password against database PBKDF2 hash, mints HMAC-SHA256 JWT containing Fernet-encrypted claims. |
| `POST`| `/api/v1/auth/token` | `oauth2_token_endpoint` | Form | Standard OAuth2 password flow accepting `OAuth2PasswordRequestForm` (`username`, `password`) and returning Bearer token. |
| `GET` | `/api/v1/auth/me` | `get_current_user_profile` | Bearer JWT | Decrypts token claims and verifies active user status in database; returns user profile and permissions. |
| `POST`| `/api/v1/crypto/encrypt`| `encrypt_payload_endpoint`| Bearer JWT | Encrypts arbitrary JSON/string payloads using AES-Fernet cipher. |
| `POST`| `/api/v1/crypto/decrypt`| `decrypt_payload_endpoint`| Bearer JWT | Decrypts AES-Fernet ciphertext back to plaintext or structured JSON. |

### 4.4 Governance Policy Management Endpoints
| Method | Path | Function | Auth | Purpose |
|---|---|---|---|---|
| `GET` | `/api/v1/policies` | `get_governance_policies` | None | Returns all active/inactive governance policies from the database alongside in-memory cache evaluation metrics. |
| `POST`| `/api/v1/policies` | `create_governance_policy`| None | Inserts new rule into database and atomically reloads in-memory cache (<0.05ms). |
| `PUT` | `/api/v1/policies/{id}` | `update_governance_policy`| None | Updates existing rule and invalidates/synchronizes cache. |
| `DELETE`| `/api/v1/policies/{id}` | `delete_governance_policy`| None | Deletes policy and updates cache. |
| `POST`| `/api/v1/policies/reset` | `reset_governance_policies` | None | Resets policies to the default 8 baseline rules. |
| `GET` | `/api/v1/policies/available-tools` | `get_available_banking_tools` | None | Returns catalog of registered core banking tools with risk levels and default role mappings. |

### 4.5 Agent Fleet, Kill-Switch & Telemetry Endpoints
| Method | Path | Function | Auth | Purpose |
|---|---|---|---|---|
| `GET` | `/api/v1/agents`, `/api/v1/agents/fleet` | `get_governed_agents` | None | Returns customer assistant fleet (`Agent-Support-401..403`) and institutional fleet (`Treasury`, `Branch`, `Audit`) with live quarantine states. |
| `POST`| `/api/v1/passport/mint` | `mint_passport` | None | Utility to mint test NHI Agent Passports (HMAC-SHA256 tokens). |
| `POST`| `/api/v1/killswitch/quarantine` | `trigger_quarantine` | None | Manually or programmatically quarantines an agent, measuring MTTR (<200ms). |
| `POST`| `/api/v1/killswitch/lift` | `lift_quarantine_endpoint` | None | Reinstates quarantined agent with mandatory FFIEC justification and analyst ID. |
| `GET` | `/api/v1/audit/logs` | `fetch_audit_logs` | None | Returns auditable security event logs with XAI causal factors, filterable by `agent_id` and `decision`. |
| `GET` | `/api/v1/telemetry/metrics` | `telemetry_metrics_endpoint`| None | Real-time event counts, rolling window mean risk, PEP latency, anomaly rates, and security alerts. |
| `GET` | `/api/v1/ml/drift-status` | `ml_drift_status_endpoint` | None | Statistical drift analysis comparing rolling window to benign baseline. |
| `POST`| `/api/v1/ml/retrain` | `ml_retrain_endpoint` | None | Triggers online retraining of Isolation Forest with buffered RLHF feedback samples. |
| `POST`| `/api/v1/chat/message` | `chat_agent_endpoint` | None | Chatbot gateway routing natural language queries to isolated virtual assistants through the PEP. |

### 4.6 Zero-Trust Policy Enforcement Point (PEP) Reverse Proxy
| Method | Path | Function | Auth | Purpose |
|---|---|---|---|---|
| `ANY` | `/gateway/{path:path}` | `pep_reverse_proxy` | Bearer Agent Passport | The core Zero-Trust PEP gateway. Enforces token verification, kill-switch check, policy check, and ML risk evaluation before routing to mock banking services. |

### 4.7 Upstream Core Banking Microservices (`backend/api/mock_banking.py`)
| Method | Path | Function | Auth | Purpose |
|---|---|---|---|---|
| `GET` | `/api/v1/faq` | `get_bank_faqs` | Direct / PEP | Safe public bank hours and directory. |
| `GET` | `/api/v1/accounts/{id}/balance` | `get_account_balance` | Direct / PEP | Savings/checking account balance lookup. |
| `GET` | `/api/v1/accounts/{id}/deposits`| `get_account_deposits` | Direct / PEP | Multi-FD portfolio lookup with maturity dates and interest rates. |
| `POST`| `/api/v1/accounts/{id}/deposits/liquidate` | `liquidate_fixed_deposit` | Direct / PEP | Premature liquidation of term deposits, settling principal into account balance. |
| `POST`| `/api/v1/transfers/wire` | `execute_wire_transfer` | Direct / PEP | NEFT/RTGS interbank fund movement with atomic balance debit/credit and ledger entry. |
| `GET` | `/api/v1/customers/export` | `export_all_customer_data` | Direct / PEP | Bulk customer record and PII export (restricted by PCI-DSS). |
| `GET` | `/api/v1/accounts/{id}/transactions` | `get_account_transactions_endpoint` | Direct / PEP | Historical account transaction ledger. |

---

## 5. Security & Policy Enforcement Deep-Dive

### 5.1 The 7-Stage PEP Pipeline (`backend/pep/gateway.py`)
Every inbound request to `/gateway/{path}` traverses a strict zero-trust decision pipeline:
1. **Agent Passport Authentication**:
   - Header format: `Authorization: Bearer <token>`
   - `NHITokenManager.verify_agent_token()` validates HMAC-SHA256 signature using `JWT_SECRET_KEY` and checks timestamp expiry. Rejects missing token with HTTP 401 and invalid/tampered signature with HTTP 403.
2. **Real-Time Kill-Switch Check**:
   - Checks `KillSwitch.is_quarantined(agent_id)` in Redis/L1 cache (<0.2ms).
   - If quarantined, immediately aborts with HTTP 403, emits `QUARANTINED` telemetry to Kafka alerts topic, and persists audit log.
3. **Payload Inspection Extraction**:
   - Extracts request body safely (`POST`/`PUT`) for downstream entropy and size analysis.
4. **Deterministic Dynamic Policy Engine Evaluation**:
   - Invokes `policy_engine.evaluate(agent_id, role, endpoint, method)`.
   - Wildcard pattern matching (`fnmatch`) evaluated entirely against the in-memory L1 cache (<0.05ms).
   - Priority resolution: **Any matching active DENY rule immediately blocks** with HTTP 403 and logs compliance tag (`SOX-404`, `BANKING-GOV`, `PCI-DSS`).
5. **Behavioral ML Risk Scoring (`backend/ml/risk_engine.py`)**:
   - Fast-path bypass for benign `GET /balance` and `GET /faq` (<0.05ms latency, fixed 0.10 risk).
   - Feature extraction:
     - **Shannon Entropy**: $H(X) = -\sum P(x) \log_2 P(x)$. Flags prompt injection and base64 exfiltration (>4.8 bits).
     - **Request Velocity**: Sliding 10-second window requests-per-second (RPS). Flags scraping bursts (>10.0 RPS).
     - **Markov Sequence Modeling**: O(1) set lookup of illegal state jumps (e.g., `/balance` $\rightarrow$ `/transfers/wire` or `/faq` $\rightarrow$ `/customers/export`).
   - Isolation Forest inference: Predicts anomaly score mapped via sigmoid calibration $S(x) = \frac{1}{1 + e^{3 \cdot \text{decision}}}$.
   - **Deterministic Safety Floors**:
     - Entropy > 4.8 bits $\rightarrow$ Risk $\ge 0.80$ (`HIGH_ENTROPY`)
     - Velocity > 10.0 RPS $\rightarrow$ Risk $\ge 0.78$ (`BURST_VELOCITY`)
     - Markov score == 1.0 $\rightarrow$ Risk $\ge 0.82$ (`ILLEGAL_API_TRANSITION`)
     - Payload > 4000 bytes $\rightarrow$ Risk $\ge 0.76$ (`LARGE_PAYLOAD`)
   - **Auto-Quarantine Trigger**: If `risk_score >= 0.75`, `KillSwitch.quarantine_agent` is automatically executed, terminating the agent and returning HTTP 403.
6. **Dispatch to Upstream Core Banking Microservice**:
   - Executes request against mock banking services (`/faq`, `/balance`, `/deposits`, `/transfers/wire`, etc.).
7. **Telemetry & Audit Emission**:
   - Telemetry emitted asynchronously to Kafka (`agentic-iam.telemetry` and `agentic-iam.alerts`).
   - Audit record persisted asynchronously to `audit_logs` table with XAI causal factors and measured latency.

---

## 6. Authentication & Cryptographic Integrity

### 6.1 Salted PBKDF2 Password Hashing
- Algorithm: `PBKDF2-HMAC-SHA256` with **100,000 iterations** and 16-byte random hex salt generated via Python `secrets.token_hex(16)`.
- Verification: Constant-time comparison using `hmac.compare_digest(calculated_hash, stored_hash)` preventing timing attacks.

### 6.2 Seeded Personas & Database Credentials
The system seeds 4 distinct personas across both username and account ID lookups:
| Username | Password | Role | Account ID | Name | Tier / Clearance |
|---|---|---|---|---|---|
| `admin` | `soc2026` | `admin` | `None` | SOC Lead Auditor | Tier-4 SecOps Lead (Badge: SOC-ANALYST-PES-4091) |
| `rahul` / `401` | `banking123` | `customer` | `401` | Rahul Sharma | GOLD (Badge: CUST-GOLD-401) |
| `priya` / `402` | `banking123` | `customer` | `402` | Priya Patel | PLATINUM (Badge: CUST-PLAT-402) |
| `vikram` / `403` | `banking123` | `customer` | `403` | Vikram Malhotra | SILVER (Badge: CUST-SLVR-403) |

### 6.3 AES-Fernet Authenticated Payload Encryption
- Key Derivation: 32-byte Fernet key derived deterministically from `JWT_SECRET_KEY` via `base64.urlsafe_b64encode(hashlib.sha256(secret).digest())`.
- Cipher: AES-128-CBC with HMAC-SHA256 authentication.
- Client Session JWTs: User tokens minted by `NHITokenManager.mint_user_token` encrypt sensitive claims (user ID, account ID, tier, clearance, PAN) inside an embedded `enc_claims` string. When verifying, `verify_user_token` decrypts the claims and verifies that the decrypted subject matches the unencrypted `sub`.
- Endpoints: `/api/v1/crypto/encrypt` and `/api/v1/crypto/decrypt` expose authenticated payload cryptographic operations.

---

## 7. Multi-Tenant Session & Financial Ledger Segregation

### 7.1 Customer Account Segregation
The ledger strictly partitions balances, portfolios, and transaction histories:
- **Account 401 (Rahul Sharma)**:
  - Savings Balance: **₹84,250.00**
  - Term Deposits: **1 Fixed Deposit** (`FD-901`: ₹500,000.00 @ 7.25% Cumulative, maturing 2027-03-31)
  - Initial Ledger: 4 transactions (Salary credit ₹145,000, Blinkit groceries ₹2,450, ATM cash withdrawal ₹10,000, FD interest credit ₹9,062.50)
- **Account 402 (Priya Patel)**:
  - Savings Balance: **₹312,400.00**
  - Term Deposits: **3 Fixed Deposits** totaling **₹2,350,000.00**:
    - `FD-801`: ₹1,500,000.00 @ 7.80% (High Net-Worth Platinum Term Deposit)
    - `FD-802`: ₹350,000.00 @ 7.40% (Flexi Recurring Fixed Deposit)
    - `FD-803`: ₹500,000.00 @ 8.10% (Corporate High-Yield Bond FD)
  - Initial Ledger: 4 transactions (Salary credit ₹280,000, Apple Store ₹134,900, Taj fine dining ₹12,500, Sovereign Gold Bond interest ₹24,000)
- **Account 403 (Vikram Malhotra)**:
  - Savings Balance: **₹15,000.00**
  - Term Deposits: **2 Fixed Deposits** totaling **₹80,000.00**:
    - `FD-701`: ₹50,000.00 @ 6.80% (Starter Short-Term FD)
    - `FD-702`: ₹30,000.00 @ 6.95% (Monthly Income Plan FD)
  - Initial Ledger: 4 transactions (Freelance consulting credit ₹28,500, Swiggy ₹640, Metro reload ₹500, BookMyShow IMAX ₹850)

### 7.2 Virtual Assistant Fleet Segregation
- Each customer account is paired with a dedicated virtual assistant:
  - Account 401 $\rightarrow$ `Agent-Support-401`
  - Account 402 $\rightarrow$ `Agent-Support-402`
  - Account 403 $\rightarrow$ `Agent-Support-403`
- In `backend/main.py::chat_agent_endpoint`, the assistant ID is deterministically resolved as `Agent-Support-{account_id}`.
- **Tenant Isolation Guarantee**: Quarantining `Agent-Support-401` suspends tool executions exclusively for Account 401. Virtual assistants `Agent-Support-402` and `Agent-Support-403` remain in `ACTIVE` status and continue executing balance inquiries, deposits inspections, and banking FAQs. Verified by `test_user_wise_agent_fleet_isolation`.

---

## 8. Event Streaming, Telemetry & Continuous Learning

### 8.1 Kafka Telemetry Producer (`backend/core/kafka_producer.py`)
- Emits structured JSON events asynchronously:
  - `event_id`, `timestamp`, `timestamp_iso`
  - `agent_id`, `role`, `endpoint`, `method`
  - `governor_status` (`ALLOWED`, `BLOCKED`, `QUARANTINED`)
  - `risk_score`, `pep_latency_ms`, `payload_preview`
  - `violation_reason`, `xai_factors` (causal factors for explainability)
  - `metadata` (trace ID, parent agent, compliance tags, model version)
- Dual-dispatch: Quarantined events and events with `risk_score >= 0.75` are dispatched simultaneously to `agentic-iam.telemetry` and `agentic-iam.alerts`.

### 8.2 Governance Consumer & Concept Drift Detection (`backend/ml/kafka_consumer.py`)
- Ingests events into a rolling window of 100 samples.
- Compares rolling statistics against baseline benchmarks:
  - Baseline mean risk: 0.15
  - Baseline anomaly rate: 5.0%
- Detects Concept & Feature Drift:
  - Triggers `ANOMALY_RATE_SPIKE` if rolling anomaly rate exceeds 20%.
  - Triggers `MEAN_RISK_ELEVATION` if rolling risk shifts by +0.25 above baseline.
- Retraining Buffer: Collects blocked or borderline requests ($0.55 \le \text{risk} < 0.75$) for online model retraining (`/api/v1/ml/retrain`).
- Attack Campaign Detection: Flags agents triggering 3 or more consecutive violations as `ATTACK_CAMPAIGN_DETECTED`.

---

## 9. Backend Test Suite Survey & Execution Results

### 9.1 Test Suite Breakdown
| Test File | Test Count | Key Features Covered |
|---|---|---|
| `tests/test_auth_and_multitenancy.py` | 7 | PBKDF2 hashing, AES-Fernet encryption/decryption, JWT with encrypted claims, OAuth2 token password flow, crypto REST endpoints, multi-tenant accounts (401, 402, 403), distinct FDs, user-wise agent fleet isolation. |
| `tests/test_backend.py` | 32 | PEP latency (<10ms), SOX-404 deny rule, killswitch quarantine (<200ms MTTR), ML anomaly quarantine, chat agent balance/wire, Redis read/write, DB balance mutation on wire transfer, DB mutation on FD liquidation, quarantined agent DB protection, insufficient funds overdraft check, audit trail persistence, PostgreSQL connection/schema/seeds/audit/conversation, resilient SQLite fallback, health masking, table browser GUI endpoints, login, prompt injection defense, transaction ledger, system reset, root metadata. |
| `tests/test_kafka_consumer.py` | 20 | `.env` configuration, docker ports, docker-compose configuration, telemetry schema with XAI factors, consumer ingestion, security incident alerts, attack campaign alerts, feature & concept drift detection, retraining feedback buffer, in-memory fallback queue, telemetry/drift REST endpoints, consumer null robustness, online model retraining. |
| `tests/test_ml_risk_engine.py` | 18 | Shannon entropy computation, sliding-window velocity burst/expiry, feature vector shape, benign balance/FAQ risk (<0.30), high-entropy exfiltration risk ($\ge 0.75$), rogue wire transition risk ($\ge 0.75$), sub-1ms fast-path latency, auto-quarantine blocking, FFIEC reinstatement compliance, parameterized path normalization, Markov sequence jump, ML & Redis KillSwitch synchronization. |
| **Total** | **77** | **Full backend surface area** |

### 9.2 Test Execution Results
Execution command:
```powershell
D:\Work\Deloite_Capstone_Project\venv\Scripts\pytest -v
```
Output Summary:
```
================== 75 passed, 2 skipped in 90.10s (0:01:30) ===================
```
- **Passed**: 75 tests (100% of runnable unit/integration tests passed without failure).
- **Skipped**: 2 tests (`test_docker_postgresql_connection_and_credentials` and `test_docker_services_ports_open`), which probe live Docker container TCP ports and cleanly skip when Docker Compose is not actively running.

### 9.3 Critical Environment Caveats & Findings
1. **Virtual Environment Discrepancy**:
   - `D:\Work\Deloite_Capstone_Project\Gateway\venv` was incomplete (lacked `SQLAlchemy`, `cryptography`, `python-multipart`).
   - The authoritative virtual environment is located at `D:\Work\Deloite_Capstone_Project\venv`, which contains `SQLAlchemy 2.0.52`, `cryptography 50.0.1`, `fastapi 0.141.1`, `scikit-learn 1.9.1`, `psycopg2-binary 2.9.13`, and all required packages.
2. **`requirements.txt` Incompleteness**:
   - `D:\Work\Deloite_Capstone_Project\Gateway\requirements.txt` is missing `SQLAlchemy`, `cryptography`, `python-multipart`, and `psycopg2-binary`. Downstream agents or deployment scripts relying solely on `Gateway/requirements.txt` would fail to install required packages unless updated.

---

## 10. Verification & Regression Recommendations

For subsequent regression testing and quality assurance:
1. **Test Runner Command**:
   Always execute pytest via the project virtual environment:
   ```powershell
   D:\Work\Deloite_Capstone_Project\venv\Scripts\pytest -v
   ```
2. **Dependency Update**:
   Update `Gateway/requirements.txt` to include:
   ```
   SQLAlchemy>=2.0.0
   cryptography>=42.0.0
   python-multipart>=0.0.9
   psycopg2-binary>=2.9.9
   ```
3. **Deterministic State Reset**:
   Before running multi-tenant or adversarial attack tests, call `POST /api/v1/system/reset` or `reset_database()` to ensure clean initial balances and lift any leftover quarantines.
