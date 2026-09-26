# Zero-Trust Gateway PEP — Request Lifecycle & Decision Flowchart

## Operational Decision Flowchart

```mermaid
flowchart TD
    %% Styling & Classes
    classDef startEnd fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff
    classDef decision fill:#0f172a,stroke:#f59e0b,stroke-width:2px,color:#fff
    classDef block fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fff
    classDef pass fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff
    classDef async fill:#1e1b4b,stroke:#8b5cf6,stroke-width:2px,color:#fff

    START(["Agentic Query Inbound<br/>(Bearer Passport Token)"]):::startEnd
    AUTH{"1. Valid Passport Signature?"}:::decision
    KILL{"2. Quarantined in Redis?<br/>(<0.2ms)"}:::decision
    SOX{"3. Passes SOX-404 Policy?<br/>(Least-Privilege Role)"}:::decision
    ML{"4. Behavioral ML Anomaly?<br/>(Risk >= 0.75)"}:::decision

    ERR_AUTH["401 Unauthorized<br/>(Signature Failure)"]:::block
    ERR_KILL["403 Forbidden<br/>(Agent Terminated)"]:::block
    ERR_SOX["403 Forbidden<br/>(Policy Violation)"]:::block
    TRIGGER_KS["Auto-Trigger KillSwitch<br/>(Quarantine in Redis)"]:::block
    EXECUTE["200 OK: Execute Core Banking<br/>(Ledger Mutation)"]:::pass

    ASYNC_EVENT[("Async Sidecar:<br/>Kafka Telemetry & PostgreSQL Audit")]:::async

    %% Decision Flow
    START --> AUTH
    AUTH -->|No| ERR_AUTH
    AUTH -->|Yes| KILL

    KILL -->|Yes| ERR_KILL
    KILL -->|No| SOX

    SOX -->|No| ERR_SOX
    SOX -->|Yes| ML

    ML -->|Yes| TRIGGER_KS --> ERR_KILL
    ML -->|No| EXECUTE

    %% Background Sidecar
    EXECUTE -.-> ASYNC_EVENT
    ERR_SOX -.-> ASYNC_EVENT
    TRIGGER_KS -.-> ASYNC_EVENT
```

---

## Gate Evaluation Summary

| Step | Security Gate | Mechanism & Target SLA | Result on Failure |
| :---: | :--- | :--- | :--- |
| **1** | **Cryptographic Identity** | HMAC-SHA256 Bearer Passport signature check (`< 0.5 ms`) | `401 Unauthorized` |
| **2** | **Revocation Check** | Sub-millisecond Redis key lookup `agentic_iam:revoked:agent:<id>` (`< 0.2 ms`) | `403 Forbidden (Agent Terminated)` |
| **3** | **SOX-404 Compliance** | Deterministic role gate (e.g. support agents blocked from transfers) (`< 0.5 ms`) | `403 Forbidden (Policy Violation)` |
| **4** | **Behavioral ML Engine** | Isolation Forest inference scoring entropy, velocity, & Markov transitions (`< 15 ms`) | Auto-Quarantine in Redis + `403 Forbidden` |
| **5** | **Execution & Audit** | Atomic banking balance updates + non-blocking Kafka/Postgres telemetry (`0.0 ms` overhead) | `200 OK (Allowed)` |
