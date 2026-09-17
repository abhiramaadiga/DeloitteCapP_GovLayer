"""
backend/api/mock_banking.py
Simulated Core Banking Microservices (Infosys Finacle / Temenos proxy target).
Multi-tenant partitioned for accounts 401 (Rahul), 402 (Priya), and 403 (Vikram).
"""
import copy
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["Core Banking"])

try:
    from backend.core.database import (
        sync_account_balance,
        save_banking_transaction,
        get_account_transactions,
        get_account_from_db,
        get_account_deposits_from_db,
        liquidate_deposit_in_db,
        reset_seeded_accounts,
        reset_seeded_deposits,
        reset_seeded_transactions,
        reset_seeded_users
    )
except Exception:
    sync_account_balance = None
    save_banking_transaction = None
    get_account_transactions = None
    get_account_from_db = None
    get_account_deposits_from_db = None
    liquidate_deposit_in_db = None
    reset_seeded_accounts = None
    reset_seeded_deposits = None
    reset_seeded_transactions = None
    reset_seeded_users = None

# Baseline initial database state for testing & resets
_INITIAL_ACCOUNTS_DB = {
    "401": {"account_id": "401", "name": "Rahul Sharma", "balance_inr": 84250.0, "tier": "GOLD"},
    "402": {"account_id": "402", "name": "Priya Patel", "balance_inr": 312400.0, "tier": "PLATINUM"},
    "403": {"account_id": "403", "name": "Vikram Malhotra", "balance_inr": 15000.0, "tier": "SILVER"},
}

_INITIAL_DEPOSITS_DB = {
    "401": [
        {
            "deposit_id": "FD-901",
            "type": "Cumulative Fixed Deposit",
            "principal_inr": 500000.0,
            "interest_rate": "7.25%",
            "maturity_date": "2027-03-31",
            "status": "LOCKED"
        }
    ],
    "402": [
        {
            "deposit_id": "FD-801",
            "type": "High Net-Worth Platinum Term Deposit",
            "principal_inr": 1500000.0,
            "interest_rate": "7.80%",
            "maturity_date": "2028-06-30",
            "status": "LOCKED"
        },
        {
            "deposit_id": "FD-802",
            "type": "Flexi Recurring Fixed Deposit",
            "principal_inr": 350000.0,
            "interest_rate": "7.40%",
            "maturity_date": "2027-11-15",
            "status": "LOCKED"
        },
        {
            "deposit_id": "FD-803",
            "type": "Corporate High-Yield Bond FD",
            "principal_inr": 500000.0,
            "interest_rate": "8.10%",
            "maturity_date": "2030-01-01",
            "status": "LOCKED"
        }
    ],
    "403": [
        {
            "deposit_id": "FD-701",
            "type": "Starter Short-Term Fixed Deposit",
            "principal_inr": 50000.0,
            "interest_rate": "6.80%",
            "maturity_date": "2026-12-31",
            "status": "LOCKED"
        },
        {
            "deposit_id": "FD-702",
            "type": "Monthly Income Plan FD",
            "principal_inr": 30000.0,
            "interest_rate": "6.95%",
            "maturity_date": "2027-04-10",
            "status": "LOCKED"
        }
    ]
}

_INITIAL_TRANSACTIONS_DB = {
    "401": [
        {
            "id": "TXN-98214",
            "date": "Today, 09:15 AM",
            "description": "Tata Consultancy Payroll Direct Credit",
            "category": "Salary",
            "amount": 145000.0,
            "type": "credit",
            "status": "Settled"
        },
        {
            "id": "TXN-98190",
            "date": "Yesterday, 18:40 PM",
            "description": "UPI Merchant Settlement (Blinkit Groceries)",
            "category": "Merchant",
            "amount": 2450.0,
            "type": "debit",
            "status": "Settled"
        },
        {
            "id": "TXN-98012",
            "date": "12 Sep 2026",
            "description": "Apex Commercial ATM Cash Withdrawal (Indiranagar)",
            "category": "Cash",
            "amount": 10000.0,
            "type": "debit",
            "status": "Settled"
        },
        {
            "id": "TXN-97940",
            "date": "10 Sep 2026",
            "description": "Quarterly Fixed Deposit Interest Settlement (#FD-901)",
            "category": "Interest",
            "amount": 9062.5,
            "type": "credit",
            "status": "Settled"
        }
    ],
    "402": [
        {
            "id": "TXN-88101",
            "date": "Today, 10:30 AM",
            "description": "Infosys Executive Compensation Direct Credit",
            "category": "Salary",
            "amount": 280000.0,
            "type": "credit",
            "status": "Settled"
        },
        {
            "id": "TXN-88095",
            "date": "Yesterday, 14:15 PM",
            "description": "Apple Store BKC Merchant Settlement",
            "category": "Electronics",
            "amount": 134900.0,
            "type": "debit",
            "status": "Settled"
        },
        {
            "id": "TXN-88050",
            "date": "14 Sep 2026",
            "description": "Taj Mahal Palace Mumbai Fine Dining Settlement",
            "category": "Merchant",
            "amount": 12500.0,
            "type": "debit",
            "status": "Settled"
        },
        {
            "id": "TXN-88012",
            "date": "08 Sep 2026",
            "description": "RBI Sovereign Gold Bond Semi-Annual Interest",
            "category": "Interest",
            "amount": 24000.0,
            "type": "credit",
            "status": "Settled"
        }
    ],
    "403": [
        {
            "id": "TXN-77110",
            "date": "Today, 11:00 AM",
            "description": "Tech Mahindra Freelance Design Consulting Credit",
            "category": "Freelance",
            "amount": 28500.0,
            "type": "credit",
            "status": "Settled"
        },
        {
            "id": "TXN-77090",
            "date": "Yesterday, 20:10 PM",
            "description": "Swiggy Online Food Delivery Settlement",
            "category": "Food",
            "amount": 640.0,
            "type": "debit",
            "status": "Settled"
        },
        {
            "id": "TXN-77055",
            "date": "13 Sep 2026",
            "description": "Namma Metro Smart Card Auto-Reload",
            "category": "Transport",
            "amount": 500.0,
            "type": "debit",
            "status": "Settled"
        },
        {
            "id": "TXN-77020",
            "date": "11 Sep 2026",
            "description": "BookMyShow IMAX Weekend Tickets",
            "category": "Entertainment",
            "amount": 850.0,
            "type": "debit",
            "status": "Settled"
        }
    ]
}

# Live in-memory mock database
ACCOUNTS_DB = copy.deepcopy(_INITIAL_ACCOUNTS_DB)
DEPOSITS_DB = copy.deepcopy(_INITIAL_DEPOSITS_DB)
TRANSACTIONS_DB = copy.deepcopy(_INITIAL_TRANSACTIONS_DB)


def reset_database():
    """Resets core banking mock database and persistent DB to fresh baseline."""
    global ACCOUNTS_DB, DEPOSITS_DB, TRANSACTIONS_DB
    ACCOUNTS_DB.clear()
    ACCOUNTS_DB.update(copy.deepcopy(_INITIAL_ACCOUNTS_DB))
    DEPOSITS_DB.clear()
    DEPOSITS_DB.update(copy.deepcopy(_INITIAL_DEPOSITS_DB))
    TRANSACTIONS_DB.clear()
    TRANSACTIONS_DB.update(copy.deepcopy(_INITIAL_TRANSACTIONS_DB))

    try:
        from backend.core.killswitch import KillSwitch
        KillSwitch.clear_all()
    except Exception:
        pass

    if reset_seeded_accounts:
        try:
            reset_seeded_accounts()
        except Exception:
            pass
    if reset_seeded_deposits:
        try:
            reset_seeded_deposits()
        except Exception:
            pass
    if reset_seeded_transactions:
        try:
            reset_seeded_transactions()
        except Exception:
            pass
    if reset_seeded_users:
        try:
            reset_seeded_users()
        except Exception:
            pass


class TransferRequest(BaseModel):
    source_account: str
    destination_account: str
    amount_inr: float
    remarks: str


@router.get("/faq")
def get_bank_faqs():
    """Safe read endpoint: Branch timings and FAQs."""
    return {
        "bank_name": "Apex Commercial Bank",
        "branch_hours": "09:30 - 16:30 IST",
        "support_helpline": "1800-400-9900"
    }


@router.get("/accounts/{account_id}/balance")
def get_account_balance(account_id: str):
    """Safe read endpoint: Account balance lookup (sub-millisecond fast-path)."""
    if account_id not in ACCOUNTS_DB:
        raise HTTPException(status_code=404, detail="Account not found")
    acc = ACCOUNTS_DB[account_id]
    return {
        "account_id": acc["account_id"],
        "balance_inr": acc["balance_inr"],
        "tier": acc["tier"],
        "name": acc["name"]
    }


@router.post("/transfers/wire")
def execute_wire_transfer(req: TransferRequest):
    """High-risk financial execution endpoint (Requires payment role!)."""
    if req.source_account not in ACCOUNTS_DB:
        raise HTTPException(status_code=404, detail=f"Source account '{req.source_account}' not found")
    if req.destination_account not in ACCOUNTS_DB:
        raise HTTPException(status_code=404, detail=f"Destination account '{req.destination_account}' not found")

    if ACCOUNTS_DB[req.source_account]["balance_inr"] < req.amount_inr:
        raise HTTPException(status_code=400, detail="Insufficient funds for wire transfer")

    ACCOUNTS_DB[req.source_account]["balance_inr"] = round(ACCOUNTS_DB[req.source_account]["balance_inr"] - req.amount_inr, 2)
    ACCOUNTS_DB[req.destination_account]["balance_inr"] = round(ACCOUNTS_DB[req.destination_account]["balance_inr"] + req.amount_inr, 2)

    txn_id = f"TXN-WIRE-{int(time.time() * 1000) % 100000}"

    if req.source_account not in TRANSACTIONS_DB:
        TRANSACTIONS_DB[req.source_account] = []
    TRANSACTIONS_DB[req.source_account].insert(0, {
        "id": txn_id,
        "date": "Just now",
        "description": f"Wire Transfer to #{req.destination_account} ({req.remarks or 'IMPS Interbank'})",
        "category": "Transfer",
        "amount": req.amount_inr,
        "type": "debit",
        "status": "Settled"
    })

    try:
        from backend.core.database import sync_account_balance
        sync_account_balance(req.source_account, ACCOUNTS_DB[req.source_account]["balance_inr"])
        sync_account_balance(req.destination_account, ACCOUNTS_DB[req.destination_account]["balance_inr"])
    except Exception:
        pass

    if save_banking_transaction:
        try:
            save_banking_transaction(
                account_id=req.source_account,
                txn_id=txn_id,
                description=f"Wire Transfer to #{req.destination_account} ({req.remarks or 'IMPS Interbank'})",
                category="Transfer",
                amount=req.amount_inr,
                txn_type="debit",
                status="Settled"
            )
        except Exception:
            pass

    return {
        "status": "EXECUTED",
        "transaction_id": txn_id,
        "source_account": req.source_account,
        "destination_account": req.destination_account,
        "amount_inr": req.amount_inr,
        "source_new_balance": ACCOUNTS_DB[req.source_account]["balance_inr"],
        "source_new_balance_inr": ACCOUNTS_DB[req.source_account]["balance_inr"],
        "destination_new_balance": ACCOUNTS_DB[req.destination_account]["balance_inr"],
        "destination_new_balance_inr": ACCOUNTS_DB[req.destination_account]["balance_inr"]
    }


@router.get("/customers/export")
def export_all_customer_data():
    """Privileged data read endpoint (Restricted by PCI-DSS policy!)."""
    return {
        "status": "SUCCESS",
        "records_exported": len(ACCOUNTS_DB),
        "data": [
            {
                "account_id": acc_id,
                "name": data["name"],
                "balance_inr": data["balance_inr"],
                "tier": data["tier"]
            }
            for acc_id, data in ACCOUNTS_DB.items()
        ]
    }


@router.get("/accounts/{account_id}/deposits")
def get_account_deposits(account_id: str):
    """Safe read endpoint: Fixed deposit and investment asset lookup."""
    if get_account_deposits_from_db:
        try:
            db_res = get_account_deposits_from_db(account_id)
            if db_res and len(db_res.get("deposits", [])) > 0:
                # sync in-memory cache
                DEPOSITS_DB[account_id] = db_res["deposits"]
                return db_res
        except Exception:
            pass

    if account_id not in DEPOSITS_DB:
        return {"account_id": account_id, "deposits": [], "total_deposits_inr": 0.0}

    active_deposits = [d for d in DEPOSITS_DB[account_id] if d.get("status") != "LIQUIDATED"]
    return {
        "account_id": account_id,
        "total_deposits_inr": sum(d["principal_inr"] for d in active_deposits),
        "deposits": DEPOSITS_DB[account_id]
    }


@router.post("/accounts/{account_id}/deposits/liquidate")
def liquidate_fixed_deposit(account_id: str, deposit_id: str = None):
    """High-risk asset liquidation endpoint (Requires branch officer authorization!)."""
    if account_id not in ACCOUNTS_DB:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found")

    deposits = DEPOSITS_DB.get(account_id, [])
    target = None
    for d in deposits:
        if deposit_id and d["deposit_id"] == deposit_id:
            target = d
            break
        elif not deposit_id and d.get("status") != "LIQUIDATED":
            target = d
            deposit_id = d["deposit_id"]
            break

    if not target:
        if deposit_id:
            raise HTTPException(status_code=404, detail=f"Deposit ID '{deposit_id}' not found")
        else:
            raise HTTPException(status_code=404, detail="No active deposits available to liquidate")

    if target.get("status") == "LIQUIDATED":
        raise HTTPException(status_code=400, detail="Deposit is already liquidated")

    target["status"] = "LIQUIDATED"
    principal = target["principal_inr"]
    penalty = 0.0
    net_credit = principal
    ACCOUNTS_DB[account_id]["balance_inr"] = round(ACCOUNTS_DB[account_id]["balance_inr"] + principal, 2)

    txn_id = f"TXN-LIQ-{int(time.time() * 1000) % 100000}"

    if account_id not in TRANSACTIONS_DB:
        TRANSACTIONS_DB[account_id] = []
    TRANSACTIONS_DB[account_id].insert(0, {
        "id": txn_id,
        "date": "Just now",
        "description": f"Fixed Deposit Premature Liquidation ({deposit_id})",
        "category": "Investment Credit",
        "amount": net_credit,
        "type": "credit",
        "status": "Settled"
    })

    if liquidate_deposit_in_db:
        try:
            liquidate_deposit_in_db(account_id, deposit_id)
        except Exception:
            pass

    try:
        from backend.core.database import sync_account_balance
        sync_account_balance(account_id, ACCOUNTS_DB[account_id]["balance_inr"])
    except Exception:
        pass

    return {
        "status": "LIQUIDATION_APPROVED",
        "account_id": account_id,
        "deposit_id": deposit_id,
        "liquidated_amount_inr": principal,
        "penalty_inr": penalty,
        "net_credited_inr": net_credit,
        "new_balance_inr": ACCOUNTS_DB[account_id]["balance_inr"],
        "message": f"Deposit {deposit_id} liquidated and credited to savings (Net: ₹{net_credit:,.2f})."
    }


@router.get("/accounts/{account_id}/transactions")
def get_account_transactions_endpoint(account_id: str, limit: int = 50):
    """Safe read endpoint: Retrieve transaction activity ledger for an account."""
    if get_account_transactions:
        try:
            db_txns = get_account_transactions(account_id, limit=limit)
            if db_txns and len(db_txns) > 0:
                return {"account_id": account_id, "transactions": db_txns}
        except Exception:
            pass
    txns = TRANSACTIONS_DB.get(account_id, [])[:limit]
    return {"account_id": account_id, "transactions": txns}
