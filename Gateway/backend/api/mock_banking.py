"""
backend/api/mock_banking.py
Simulated Core Banking Microservices (Infosys Finacle / Temenos proxy target).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["Core Banking"])

import copy

try:
    from backend.core.database import sync_account_balance
except Exception:
    sync_account_balance = None

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
    ]
}

# Live in-memory mock database
ACCOUNTS_DB = copy.deepcopy(_INITIAL_ACCOUNTS_DB)
DEPOSITS_DB = copy.deepcopy(_INITIAL_DEPOSITS_DB)

def reset_database():
    """Resets core banking mock database to fresh baseline."""
    global ACCOUNTS_DB, DEPOSITS_DB
    ACCOUNTS_DB.clear()
    ACCOUNTS_DB.update(copy.deepcopy(_INITIAL_ACCOUNTS_DB))
    DEPOSITS_DB.clear()
    DEPOSITS_DB.update(copy.deepcopy(_INITIAL_DEPOSITS_DB))

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
    """Safe read endpoint: Account balance lookup."""
    if account_id not in ACCOUNTS_DB:
        raise HTTPException(status_code=404, detail="Account not found")
    acc = ACCOUNTS_DB[account_id]
    return {
        "account_id": acc["account_id"],
        "balance_inr": acc["balance_inr"],
        "tier": acc["tier"]
    }

@router.post("/transfers/wire")
def execute_wire_transfer(req: TransferRequest):
    """High-risk financial execution endpoint (Requires payment role!)."""
    if req.source_account not in ACCOUNTS_DB:
        raise HTTPException(status_code=404, detail=f"Source account '{req.source_account}' not found")
    if req.destination_account not in ACCOUNTS_DB:
        raise HTTPException(status_code=404, detail=f"Destination account '{req.destination_account}' not found")

    src = ACCOUNTS_DB[req.source_account]
    dest = ACCOUNTS_DB[req.destination_account]

    if src["balance_inr"] < req.amount_inr:
        raise HTTPException(status_code=400, detail="Insufficient funds in source account")

    # Atomic in-memory balance update
    src["balance_inr"] = round(src["balance_inr"] - req.amount_inr, 2)
    dest["balance_inr"] = round(dest["balance_inr"] + req.amount_inr, 2)

    if sync_account_balance:
        try:
            sync_account_balance(req.source_account, src["balance_inr"])
            sync_account_balance(req.destination_account, dest["balance_inr"])
        except Exception:
            pass

    return {
        "status": "COMPLETED",
        "transaction_id": "TXN-WIRE-99214A",
        "amount": req.amount_inr,
        "from": req.source_account,
        "to": req.destination_account,
        "source_new_balance": src["balance_inr"],
        "destination_new_balance": dest["balance_inr"],
        "message": "Funds wired successfully"
    }

@router.get("/customers/export")
def export_all_customer_data():
    """Restricted bulk PII dump endpoint (Admin only!)."""
    return {
        "status": "EXPORT_SUCCESS",
        "total_records": len(ACCOUNTS_DB),
        "records": list(ACCOUNTS_DB.values())
    }


@router.get("/accounts/{account_id}/deposits")
def get_account_deposits(account_id: str):
    """Safe read endpoint: Fixed deposit and investment asset lookup."""
    if account_id not in DEPOSITS_DB:
        return {"account_id": account_id, "deposits": []}
    return {
        "account_id": account_id,
        "total_deposits_inr": sum(d["principal_inr"] for d in DEPOSITS_DB[account_id]),
        "deposits": DEPOSITS_DB[account_id]
    }

@router.post("/accounts/{account_id}/deposits/liquidate")
def liquidate_fixed_deposit(account_id: str, deposit_id: str):
    """High-risk asset liquidation endpoint (Requires branch officer authorization!)."""
    if account_id not in ACCOUNTS_DB:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found")
    deposits = DEPOSITS_DB.get(account_id, [])
    target = None
    for d in deposits:
        if d["deposit_id"] == deposit_id:
            target = d
            break
    if not target:
        raise HTTPException(status_code=404, detail=f"Deposit ID '{deposit_id}' not found")
    if target.get("status") == "LIQUIDATED":
        raise HTTPException(status_code=400, detail="Deposit is already liquidated")

    target["status"] = "LIQUIDATED"
    principal = target["principal_inr"]
    ACCOUNTS_DB[account_id]["balance_inr"] = round(ACCOUNTS_DB[account_id]["balance_inr"] + principal, 2)

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
        "new_balance_inr": ACCOUNTS_DB[account_id]["balance_inr"],
        "message": "Deposit liquidated and credited to savings."
    }
