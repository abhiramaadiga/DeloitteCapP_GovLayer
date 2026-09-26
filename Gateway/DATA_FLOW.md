# Zero-Trust Gateway PEP — Data Flow Diagram (DFD)

## High-Level Data Flow Diagram (Level 1 DFD)

```mermaid
flowchart LR
    %% Styling & Classes
    classDef entity fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff
    classDef process fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#fff
    classDef store fill:#1c1917,stroke:#f59e0b,stroke-width:2px,color:#fff

    %% External Entities
    AGENT["External Entity:<br/>Autonomous AI Agent"]:::entity
    SOC["External Entity:<br/>SOC Security Analyst"]:::entity

    %% Processes
    P1(("1.0<br/>Authenticate &<br/>Verify Token")):::process
    P2(("2.0<br/>Enforce Policy &<br/>Revocation Gate")):::process
    P3(("3.0<br/>Extract Features &<br/>Score ML Risk")):::process
    P4(("4.0<br/>Execute Core<br/>Banking Mutation")):::process
    P5(("5.0<br/>Stream Telemetry &<br/>Detect ML Drift")):::process

    %% Data Stores
    D1[("D1: Redis Cache<br/>(Quarantine States)")]:::store
    D2[("D2: Core Banking Ledger<br/>(Account Balances)")]:::store
    D3[("D3: Kafka Broker<br/>(Telemetry & Alerts)")]:::store
    D4[("D4: PostgreSQL DB<br/>(Audit Logs & RLHF)")]:::store

    %% Data Flows
    AGENT -->|"Request Payload + JWT"| P1
    P1 -->|"Validated Claims"| P2
    D1 <-->|"Revocation Status (<0.2ms)"| P2

    P2 -->|"Authorized Context"| P3
    P3 -->|"Anomaly Alert (Quarantine)"| D1
    P3 -->|"Benign Payload"| P4

    P4 <-->|"Atomic Balance Updates"| D2
    P4 -->|"Execution Response"| AGENT

    %% Telemetry & Storage Flows
    P2 & P3 & P4 -.->|"Audit Trail + XAI"| D4
    P2 & P3 & P4 -.->|"Event Metrics"| D3
    D3 -->|"Stream Ingestion"| P5
    P5 -.->|"Drift Alerts & Incident Feeds"| SOC
```

---

## Data Transformation Pipeline

| Stage | Process | Inputs | Outputs / Side Effects | Destination Store |
| :---: | :--- | :--- | :--- | :--- |
| **1.0** | **Authentication** | Bearer Passport (HMAC-SHA256) | Validated Agent Claims (`agent_id`, `role`) | In-Memory Context |
| **2.0** | **Revocation & Policy** | Validated Claims + HTTP Path | Access Allowed vs. `403 Forbidden` | `D1: Redis Cache` (Lookup `< 0.2ms`) |
| **3.0** | **Behavioral ML Scoring** | Raw Payload & Endpoint | Risk Score ($0.0 - 1.0$), XAI Causal Factors | `D1: Redis Cache` (Auto-Quarantine if $\ge 0.75$) |
| **4.0** | **Banking Ledger Update** | Authorized Banking Request | New Balances (`source`, `dest`) & 200 OK | `D2: Banking Ledger` (`banking_accounts`) |
| **5.0** | **Telemetry & Drift Engine** | Dual-Dispatched Event Stream | Continuous Drift Alarms & Retraining Buffer | `D3: Kafka Broker` & `D4: PostgreSQL` |

---

## Data Stores Summary

- **D1: Redis Cache (`:6379`)**: High-performance key-value store holding active quarantine keys (`agentic_iam:revoked:agent:<id>`) with automated TTLs.
- **D2: Core Banking Ledger (`banking_accounts`)**: Relational ACID storage for customer deposits, current accounts, and ledger balance adjustments.
- **D3: Kafka Telemetry Broker (`:9092`)**: High-throughput distributed streaming topics (`agentic-iam.telemetry` and `agentic-iam.alerts`).
- **D4: PostgreSQL Compliance DB (`:5432`)**: Persistent System of Record housing `audit_logs` (tamper-evident XAI decision trail) and `conversations` (RLHF dataset).

