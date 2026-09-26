package bfsi.authz

test_default_deny_on_empty_input if {
	not allow with input as {}
}

test_quarantined_agent_denied if {
	not allow with input as {"role": "admin_agent", "is_quarantined": true}
}

test_support_bot_can_read_balance if {
	allow with input as {
		"role": "tier1_customer_service",
		"method": "GET",
		"endpoint": "/accounts/acc1/balance",
		"is_quarantined": false,
	}
}

test_support_bot_denied_wire_transfer if {
	not allow with input as {
		"role": "tier1_customer_service",
		"method": "POST",
		"endpoint": "/transfers/wire",
		"is_quarantined": false,
	}
}

test_payment_bot_within_limit_allowed if {
	allow with input as {
		"role": "payment_execution_bot",
		"method": "POST",
		"endpoint": "/transfers/ach",
		"amount": 5000,
		"max_transaction_amount": 10000,
		"is_quarantined": false,
	}
		with data.transaction_limits as {"payment_execution_bot": 10000}
}

test_payment_bot_over_limit_denied if {
	not allow with input as {
		"role": "payment_execution_bot",
		"method": "POST",
		"endpoint": "/transfers/wire",
		"amount": 15000,
		"max_transaction_amount": 10000,
		"is_quarantined": false,
	}
		with data.transaction_limits as {"payment_execution_bot": 10000}
}

test_payment_bot_forged_claim_denied if {
	not allow with input as {
		"role": "payment_execution_bot",
		"method": "POST",
		"endpoint": "/transfers/ach",
		"amount": 20000,
		"max_transaction_amount": 20000,
		"is_quarantined": false,
	}
		with data.transaction_limits as {"payment_execution_bot": 10000}
}

test_bulk_export_denied_for_non_admin if {
	not allow with input as {
		"role": "wealth_advisor_bot",
		"method": "GET",
		"endpoint": "/customers/export",
		"is_quarantined": false,
	}
}

test_admin_can_bulk_export if {
	allow with input as {
		"role": "admin_agent",
		"method": "GET",
		"endpoint": "/customers/export",
		"is_quarantined": false,
		"payload_bytes": 1024,
	}
}

test_admin_denied_over_payload_limit if {
	not allow with input as {
		"role": "admin_agent",
		"method": "GET",
		"endpoint": "/customers/export",
		"is_quarantined": false,
		"payload_bytes": 700000,
	}
}

test_ownership_violation_denied if {
	not allow with input as {
		"role": "wealth_advisor_bot",
		"method": "GET",
		"endpoint": "/accounts/acc1/portfolio",
		"is_quarantined": false,
		"account_owner_id": "cust1",
		"customer_id": "cust2",
	}
}