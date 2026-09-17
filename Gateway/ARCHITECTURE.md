# Zero-Trust Non-Human Identity (NHI) Access Governor — Architecture

## High-Level System Architecture

```mermaid
flowchart TD
    %% Styling & Classes
    classDef client fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff
    classDef pep fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#fff
    classDef ml fill:#1e1b4b,stroke:#8b5cf6,stroke-width:2px,color:#fff
    classDef infra fill:#1c1917,stroke:#f59e0b,stroke-width:2px,color:#fff

    subgraph CLIENTS["1. Client & Agent Layer"]
        A["AI Agents & Chatbots<br/>(NHI Passport Tokens)"]:::client
        FE["React Banking & SOC Portal<br/>(Port 5173)"]:::client
    end

    subgraph GATEWAY["2. Zero-Trust Gateway PEP (FastAPI :8000)"]
        PEP["Policy Enforcement Point<br/>(gateway.py)"]:::pep
        AUTH["NHI Token Verifier<br/>(auth.py)"]:::pep
        SOX["SOX-404 Policy Gate<br/>(Least-Privilege)"]:::pep
    end

    subgraph ML_ENGINE["3. Behavioral ML Risk Engine"]
        FEAT["Feature Extractor<br/>(Entropy, Velocity, Markov)"]:::ml
        ISO["Isolation Forest Model<br/>(Pre-Warmed Inference)"]:::ml
        CONS["Kafka ML Drift Consumer<br/>(Continuous Learning)"]:::ml
    end

    subgraph DATA_INFRA["4. Infrastructure & Core Banking (Docker)"]
        REDIS[("Redis Cache (:6379)<br/>Sub-ms Kill-Switch")]:::infra
        KAFKA[("Kafka KRaft (:9092)<br/>Telemetry & Alerts")]:::infra
        PG[("PostgreSQL (:5432)<br/>Audit Trail & RLHF")]:::infra
        BANK["Core Banking API<br/>(Accounts & Transfers)"]:::infra
    end

    %% Flows
    A -->|"1. API Request"| PEP
    FE -->|"User Chat"| PEP
    PEP -->|"2. Verify Signature"| AUTH
    PEP -->|"3. Instant Revocation Check (<0.2ms)"| REDIS
    PEP -->|"4. Check Role Bounds"| SOX
    PEP -->|"5. Evaluate Payload Risk (<15ms)"| FEAT
    FEAT --> ISO

    %% Decision Branches
    ISO -->|"Risk >= 0.75 (Anomaly)"| REDIS
    ISO -->|"Nominal Risk"| BANK

    %% Async Telemetry & Persistence
    PEP -.->|"Async Audit Logs"| PG
    PEP -.->|"Async Event Stream"| KAFKA
    KAFKA -.->|"Drift & Retraining"| CONS
    CONS -.->|"Hot-Reload Weights"| ISO
```

---

## Architecture Summary (Executive / Presentation)

| Layer                                | Primary Role                                                                                                            | Key Technology & Files                                                                                     |
| :----------------------------------- | :---------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------- |
| **1. Client & Agent Layer**          | Autonomous AI agents & banking user interfaces presenting cryptographic tokens.                                         | HMAC-SHA256 Passports, React (`frontend/src/App.jsx`)                                                      |
| **2. Zero-Trust Gateway PEP**        | Sub-millisecond policy enforcement, cryptographic signature verification, deterministic SOX-404 least-privilege checks. | FastAPI (`backend/pep/gateway.py`), Auth Manager (`backend/core/auth.py`)                                  |
| **3. Behavioral ML Risk Engine**     | Real-time payload anomaly detection (Shannon entropy, request velocity, Markov transitions) via Isolation Forest.       | Scikit-Learn (`backend/ml/risk_engine.py`), Drift Consumer (`backend/ml/kafka_consumer.py`)                |
| **4. Core Banking & Data Backplane** | Atomic banking mutations, sub-millisecond quarantine cache, enterprise compliance audit trail, and streaming telemetry. | PostgreSQL (`:5432`), Redis (`:6379`), Kafka KRaft (`:9092`), Mock Banking (`backend/api/mock_banking.py`) |

---

## Key Performance SLAs (Deloitte BFSI Rubric)

- **Fast-Path Gateway PEP Overhead**: `< 2.0 ms` (Target: `< 5.0 ms`)
- **Kill-Switch Revocation Lookup**: `< 0.2 ms` (Target: `< 1.0 ms`)
- **Full ML Behavioral Scoring**: `12 - 15 ms` (Target: `< 30.0 ms`)
- **Quarantine MTTR (Mean-Time-To-Remediate)**: `~20 ms` (Target: `< 200.0 ms`)
- **Telemetry & Audit Logging Impact**: `0.0 ms` overhead (fully non-blocking thread and Kafka dispatch)
