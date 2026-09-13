package bfsi.authz

import future.keywords.in

default allow := false
default deny_reasons := set()

# =========================================================================
# 1. ROOT EVALUATION RULE
# =========================================================================
allow if {
	count(deny_reasons) == 0
	role_has_permission
}

# =========================================================================
# 2. DETERMINISTIC DENIALS (Hard Guardrails)
# =========================================================================

# Denial 1: Agent is currently quarantined in Kill-Switch
deny_reasons contains "SECURITY_QUARANTINE_ACTIVE" if {
	input.is_quarantined == true
}

# Denial 2: Support Bot attempting financial wire/transfer (SOX Section 404)
deny_reasons contains "SOX404_UNAUTHORIZED_FINANCIAL_TRANSFER" if {
	input.role == "tier1_customer_service"
	startswith(input.endpoint, "/transfers/")
}

# Denial 3: Support Bot attempting investment asset liquidation
deny_reasons contains "UNAUTHORIZED_ASSET_LIQUIDATION" if {
	input.role == "tier1_customer_service"
	contains(input.endpoint, "/deposits/liquidate")
}

# Denial 4: Non-admin role attempting bulk customer PII dump (PCI-DSS v4.0)
deny_reasons contains "PCIDSS_PROHIBITED_BULK_PII_EXPORT" if {
	input.endpoint == "/customers/export"
	input.role != "admin_agent"
}

# Denial 5: Payment Bot exceeding its own request-level limit
deny_reasons contains "TRANSACTION_LIMIT_EXCEEDED" if {
	input.role == "payment_execution_bot"
	input.amount > input.max_transaction_amount
}

# Denial 6: Payment Bot's token claims a higher ceiling than its role is
# authorized for — catches a forged/tampered max_transaction_amount claim.
deny_reasons contains "CLAIM_LIMIT_MISMATCH" if {
	input.role == "payment_execution_bot"
	input.max_transaction_amount != data.transaction_limits[input.role]
}

# Denial 7: HTTP method mutation / verb tampering
deny_reasons contains "UNAUTHORIZED_HTTP_METHOD" if {
	input.role == "tier1_customer_service"
	input.method != "GET"
}

# Denial 8: Buffer Overflow Protection (Payload > 64KB)
deny_reasons contains "PAYLOAD_SIZE_LIMIT_EXCEEDED" if {
	input.payload_bytes > 65536
}

# Denial 9: Resource ownership — an agent may only act on the account
# belonging to the customer its session is scoped to (admin exempt).
deny_reasons contains "RESOURCE_OWNERSHIP_VIOLATION" if {
	startswith(input.endpoint, "/accounts/")
	input.role != "admin_agent"
	input.account_owner_id != input.customer_id
}

# =========================================================================
# 3. ROLE-BASED ALLOW PERMISSIONS
# =========================================================================

# Support Bot Allowed Endpoints
role_has_permission if {
	input.role == "tier1_customer_service"
	input.method == "GET"
	is_support_safe_endpoint(input.endpoint)
}

is_support_safe_endpoint(ep) if ep == "/faq"

is_support_safe_endpoint(ep) if {
	startswith(ep, "/accounts/")
	endswith(ep, "/balance")
}

is_support_safe_endpoint(ep) if {
	startswith(ep, "/accounts/")
	endswith(ep, "/deposits")
}

# Payment Bot Allowed Endpoints
role_has_permission if {
	input.role == "payment_execution_bot"
	input.method == "POST"
	startswith(input.endpoint, "/transfers/")
	input.amount <= input.max_transaction_amount
}

# Wealth Advisor Allowed Endpoints
role_has_permission if {
	input.role == "wealth_advisor_bot"
	input.method == "GET"
	startswith(input.endpoint, "/accounts/")
}

# Admin Agent Allowed Endpoints
role_has_permission if {
	input.role == "admin_agent"
}