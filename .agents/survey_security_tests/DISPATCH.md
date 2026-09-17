# Task Assignment: Survey Security, Adversarial Specifications & Test Architecture

## Context
Survey security requirements, adversarial specifications, and test infrastructure for Apex Commercial Bank Zero-Trust Governor.
Read `D:\Work\Deloite_Capstone_Project\.agents\ORIGINAL_REQUEST.md`.

## Objectives
1. Extract detailed security and adversarial specifications:
   - Zero-Trust Policy Enforcement Point (PEP), dynamic database policy engine, caching, Isolation Forest behavioral risk scoring, killswitch revocation.
   - Adversarial boundary testing: prompt injection payloads, token signature tampering, high-entropy exfiltration bursts, unauthorized financial transfers by customer virtual assistants, premature liquidation requests.
2. Extract Authentication, OAuth2 & Cryptographic requirements:
   - Seeded personas: Admin (`admin` / `soc2026`), Rahul (`401` / `banking123`), Priya (`402` / `banking123`), Vikram (`403` / `banking123`).
   - PBKDF2 hashing, database users, OAuth2 flow (`/api/v1/auth/token`, `/api/v1/auth/me`), AES-Fernet encryption/decryption (`/api/v1/crypto/encrypt`, `/api/v1/crypto/decrypt`).
   - Rejection semantics: HTTP 401 for invalid/expired/tampered tokens.
3. Extract Multi-Tenant data & agent isolation specifications:
   - Account 401 (Rahul): Balance ₹84,250.00, 1 FD (₹500,000.00).
   - Account 402 (Priya): Balance ₹312,400.00, 3 FDs (₹2,350,000.00 total).
   - Account 403 (Vikram): Balance ₹15,000.00, 2 FDs (₹80,000.00 total).
   - Isolation: Quarantining Agent-Support-401 must never disrupt Agent-Support-402 or Agent-Support-403.
4. Survey automated regression test script requirements (R5 unified pass/fail results, zero-defect verification).
5. Map existing test assets, gaps, and required test tier structure (Tiers 1-5).
6. Write a comprehensive survey report to `D:\Work\Deloite_Capstone_Project\.agents\survey_security_tests\survey_report.md` and complete with `handoff.md`.

## 2026-09-17T04:28:44Z
<USER_REQUEST>
You are Security & Test Spec Miner (teamwork_preview_spec_miner).
Your working directory is: D:\Work\Deloite_Capstone_Project\.agents\survey_security_tests
Your dispatch instructions are at: D:\Work\Deloite_Capstone_Project\.agents\survey_security_tests\DISPATCH.md
You MUST read D:\Work\Deloite_Capstone_Project\.agents\ORIGINAL_REQUEST.md before starting work.

Mission:
Extract and document all security requirements, adversarial specifications, and test architecture for the Zero-Trust Governor.
1. Extract PEP, policy engine, caching, Isolation Forest behavioral risk scoring, and killswitch revocation rules.
2. Document adversarial boundary conditions: prompt injection payloads, token signature tampering, high-entropy data exfiltration bursts, unauthorized financial transfers, premature liquidation requests.
3. Document Authentication, OAuth2 & Cryptographic requirements: seed personas (admin, 401, 402, 403), PBKDF2 hashing, OAuth2 token issuance, /api/v1/auth/me, AES-Fernet encryption/decryption, HTTP 401 rejections.
4. Document multi-tenant data & agent isolation specifications: balances (401: ₹84,250; 402: ₹312,400; 403: ₹15,000), Fixed Deposits (401: 1 FD ₹500k; 402: 3 FDs ₹2.35M; 403: 2 FDs ₹80k), and per-user assistant quarantine isolation.
5. Map existing test assets, gaps, and required test tier structure (Tiers 1-5) plus automated regression script requirements (R5).
6. Write a comprehensive survey report to D:\Work\Deloite_Capstone_Project\.agents\survey_security_tests\survey_report.md and complete with handoff.md. Send a completion message to the caller when done.
</USER_REQUEST>

