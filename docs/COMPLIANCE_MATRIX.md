# Regulatory Compliance Matrix

Maps each enforced Rego rule (by `deny_reasons` code) to the regulatory
framework it satisfies, for the Agentic-AI Identity & Access Governor.

| Rule / Deny Code                        | Regulation                          | Requirement Addressed                                                          |
|------------------------------------------|--------------------------------------|----------------------------------------------------------------------------------|
| `SOX404_UNAUTHORIZED_FINANCIAL_TRANSFER` | SOX Section 404                      | Separation of duties — front-office (support) agents cannot initiate transfers  |
| `UNAUTHORIZED_ASSET_LIQUIDATION`         | SOX Section 404                      | Prevents liquidation outside the advisory role's mandate                        |
| `PCIDSS_PROHIBITED_BULK_PII_EXPORT`      | PCI-DSS v4.0 (Req. 7 & 8)             | Restricts bulk customer PII export to authorized non-human identities only      |
| `TRANSACTION_LIMIT_EXCEEDED`             | RBI Cyber Security Framework          | Enforces transaction ceilings for autonomous payment execution                  |
| `CLAIM_LIMIT_MISMATCH`                   | NIST AI RMF 1.0 (Manage function)     | Detects tampered/forged agent token claims — defense-in-depth against forgery   |
| `SECURITY_QUARANTINE_ACTIVE`             | NIST AI RMF 1.0 (Govern function)     | Enforces kill-switch quarantine state at the policy layer, not just the gateway |
| `UNAUTHORIZED_HTTP_METHOD`               | OWASP Top 10 for LLMs (LLM08)         | Prevents verb-tampering privilege escalation                                    |
| `PAYLOAD_SIZE_LIMIT_EXCEEDED`            | NIST AI RMF 1.0 (Manage function)     | Mitigates memory-exhaustion / bulk-exfiltration via oversized payloads          |
| `RESOURCE_OWNERSHIP_VIOLATION`           | PCI-DSS v4.0 (Req. 7) / RBI Framework | Least-privilege — agent may only act on its authorized customer's resources    |

**Note:** This matrix should be read alongside the ML Risk Engine's behavioral
detections (Shannon entropy, burst velocity, Markov transitions), which cover
threats this deterministic layer can't express as static rules — e.g. gradual
behavioral drift rather than a single rule-violating request.