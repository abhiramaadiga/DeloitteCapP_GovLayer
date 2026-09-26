# Task Assignment: Milestone 1 Worker — Backend Security & PEP Suite Implementation

## Context
Project Scope: `D:\Work\Deloite_Capstone_Project\PROJECT.md`
Authoritative Request: `D:\Work\Deloite_Capstone_Project\.agents\ORIGINAL_REQUEST.md`
Milestone: M1 Backend Security & Policy Gateway (R1)
Explorer Reports:
- `D:\Work\Deloite_Capstone_Project\.agents\m1_explorer_1\report.md`
- `D:\Work\Deloite_Capstone_Project\.agents\m1_explorer_2\report.md`
- `D:\Work\Deloite_Capstone_Project\.agents\m1_explorer_3\report.md`

## Mandatory Write Ownership
You exclusively own and may modify:
- `Gateway/backend/pep/gateway.py`
- `Gateway/backend/main.py`
- `Gateway/backend/core/killswitch.py`
- `Gateway/tests/test_backend.py`
- `Gateway/tests/test_ml_risk_engine.py`
Do NOT modify files outside this boundary.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Objectives
1. Token Rejection Semantics in PEP (`Gateway/backend/pep/gateway.py`):
   - Ensure missing tokens and expired tokens return HTTP 401 with appropriate `WWW-Authenticate: Bearer` challenge.
   - Tampered signatures, unauthorized tokens, quarantined agents, and policy denials strictly return HTTP 403.
2. FFIEC Reinstatement Exception Handling (`Gateway/backend/main.py`):
   - In `/api/v1/killswitch/lift`, catch `ValueError` for invalid justification or missing analyst ID and return HTTP 400 with descriptive error detail (not HTTP 500).
   - Ensure justification requirement is consistent (at least 5 non-whitespace characters).
3. Adversarial Boundary Test Suite Expansion (`Gateway/tests/test_backend.py` & `Gateway/tests/test_ml_risk_engine.py`):
   - Implement comprehensive automated test cases for:
     - Prompt injection attack strings (e.g. "ignore previous instructions", "system override") intercepted by intent classifier/PEP.
     - Token signature tampering (HMAC signature mismatch) returning HTTP 403.
     - Expired tokens returning HTTP 401.
     - High-entropy exfiltration bursts (>4.8 bits) triggering immediate quarantine and HTTP 403.
     - Unauthorized financial transfers by virtual assistants blocked under SOX-404 (`POL-SOX-001`).
     - Premature liquidation requests by virtual assistants blocked under Banking-Gov (`POL-BANK-002`).
     - Sub-5ms PEP fast-path policy evaluation latency assertions.
     - Exact deterministic guardrail floors (entropy > 4.8 bits -> 0.80, velocity > 10 -> 0.78, illegal transition -> 0.82, payload > 4000 -> 0.76).
4. Run the backend tests using `D:\Work\Deloite_Capstone_Project\venv\Scripts\python.exe -m pytest tests/test_backend.py tests/test_ml_risk_engine.py -v`.
5. Verify 100% test pass rate with 0 errors and 0 flakes.
6. Write a full implementation report to `D:\Work\Deloite_Capstone_Project\.agents\m1_worker_1\report.md` and complete with `handoff.md`.
