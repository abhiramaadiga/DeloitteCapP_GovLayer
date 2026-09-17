# Task Assignment: Milestone 1 Explorer 2 — Policy Engine & ML Risk Engine

## Context
Project Scope: `D:\Work\Deloite_Capstone_Project\PROJECT.md`
Authoritative Request: `D:\Work\Deloite_Capstone_Project\.agents\ORIGINAL_REQUEST.md`
Milestone: M1 Backend Security & Policy Gateway (R1)

## Objectives
1. Deeply inspect `Gateway/backend/core/policy_engine.py`, `Gateway/backend/core/cache.py`, and `Gateway/backend/ml/risk_engine.py`.
2. Verify policy engine caching mechanics (<0.05ms fast-path), dynamic database rule loading, policy rule precedence (DENY > ALLOW > DEFAULT_ALLOW), and cache invalidation on policy updates.
3. Verify the Scikit-Learn Isolation Forest risk model: feature vector extraction (Shannon entropy, velocity RPS, Markov transition jump, payload size), sigmoid probability calibration, and deterministic guardrail floors (entropy > 4.8 bits -> 0.80, velocity > 10 RPS -> 0.78, illegal Markov transition -> 0.82, payload > 4000 bytes -> 0.76).
4. Review test coverage in `tests/test_ml_risk_engine.py` and `tests/test_backend.py`.
5. Provide concrete implementation and test recommendations in `D:\Work\Deloite_Capstone_Project\.agents\m1_explorer_2\report.md` and complete with `handoff.md`.
