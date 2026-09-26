-- ============================================================================
-- AGENTIC-AI IDENTITY & ACCESS GOVERNOR FOR BFSI RETAIL BANKING
-- Deloitte Capstone 2026 | Team "The dab hands" | PES University
-- PostgreSQL System of Record (SoR) Schema Definition
-- Database: governance_db | Owner: governor_admin
-- ============================================================================

-- Table 1: Security Audit Log (Compliance & Explainable AI Audit Trail)
-- Compliant with SOX-404, PCI-DSS v4.0, and RBI Non-Human Identity Guidelines
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp VARCHAR(64) NOT NULL,
    agent_id VARCHAR(128) NOT NULL,
    role VARCHAR(64) NOT NULL,
    endpoint VARCHAR(256) NOT NULL,
    method VARCHAR(16) NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    decision VARCHAR(32) NOT NULL,         -- 'ALLOWED', 'BLOCKED', 'QUARANTINED'
    xai_reasons TEXT,                      -- JSON array of causal factors (Entropy, Burst Velocity, OPA rule)
    latency_ms DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_id ON audit_logs (id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs (timestamp);
CREATE INDEX IF NOT EXISTS ix_audit_logs_agent_id ON audit_logs (agent_id);

-- Table 2: Non-Human Identity (NHI) Conversations & RLHF Improvement Log
-- Captures human-agent interactions, flagging rogue actions for Reinforcement Learning from Human Feedback
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    timestamp VARCHAR(64) NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    user_prompt TEXT NOT NULL,
    agent_response TEXT NOT NULL,
    action_taken VARCHAR(256),             -- Target API endpoint or action
    governor_status VARCHAR(32) NOT NULL,  -- 'ALLOWED', 'BLOCKED', 'QUARANTINED'
    flagged_for_rlhf BOOLEAN DEFAULT FALSE -- Flagged true when malicious intent / prompt injection is stopped
);

CREATE INDEX IF NOT EXISTS ix_conversations_id ON conversations (id);
CREATE INDEX IF NOT EXISTS ix_conversations_timestamp ON conversations (timestamp);
CREATE INDEX IF NOT EXISTS ix_conversations_account_id ON conversations (account_id);

-- Table 3: Core Banking Accounts (System of Record for Customer Balances)
-- Simulates Finacle / Temenos core banking accounts accessed through the Zero-Trust Gateway
CREATE TABLE IF NOT EXISTS banking_accounts (
    account_id VARCHAR(64) PRIMARY KEY,
    customer_name VARCHAR(128) NOT NULL,
    account_type VARCHAR(32) NOT NULL,     -- 'GOLD', 'PLATINUM', 'SILVER'
    balance_inr DOUBLE PRECISION NOT NULL,
    currency VARCHAR(8) DEFAULT 'INR'
);

CREATE INDEX IF NOT EXISTS ix_banking_accounts_account_id ON banking_accounts (account_id);

-- Baseline Seed Data for Banking Accounts
INSERT INTO banking_accounts (account_id, customer_name, account_type, balance_inr, currency)
VALUES
    ('401', 'Rahul Sharma', 'GOLD', 84250.0, 'INR'),
    ('402', 'Priya Patel', 'PLATINUM', 312400.0, 'INR'),
    ('403', 'Vikram Malhotra', 'SILVER', 15000.0, 'INR')
ON CONFLICT (account_id) DO NOTHING;
