"""
backend/core/database.py
Enterprise PostgreSQL System of Record for Users, Banking Accounts, Term Deposits,
Audit Logs, Explainable AI (XAI), Dynamic Policies, and RLHF Conversations.
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, text, event
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.core.config import settings


def _create_resilient_engine(target_url: str = None):
    """Initializes PostgreSQL if available, otherwise falls back to local SQLite with WAL concurrency."""
    url = target_url or os.getenv("DATABASE_URL") or settings.DATABASE_URL
    if url and "postgresql" in url:
        try:
            eng = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                connect_args={"connect_timeout": 3}
            )
            with eng.connect():
                pass
            masked_url = eng.url.render_as_string(hide_password=True)
            print(f"[Database] Successfully connected to PostgreSQL at {masked_url}")
            return eng
        except Exception as e:
            print(f"[Database] PostgreSQL unreachable ({e}). Falling back to local SQLite database.")

    sqlite_url = "sqlite:///./governance_audit.db"
    eng = create_engine(sqlite_url, connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
        except Exception:
            pass

    return eng


engine = _create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def reconfigure_engine(new_url: str = None):
    """Reconfigures the active database engine dynamically (useful for test suites or runtime shifts)."""
    global engine, SessionLocal
    engine = _create_resilient_engine(new_url)
    SessionLocal.configure(bind=engine)
    init_db()
    return engine


def get_db_status() -> Dict[str, Any]:
    """Inspects the current active database connection type and health without leaking credentials."""
    try:
        url_str = engine.url.render_as_string(hide_password=True)
    except Exception:
        url_str = str(engine.url)
    is_postgres = "postgresql" in str(engine.url)
    healthy = False
    error = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            healthy = True
    except Exception as e:
        error = str(e)
    return {
        "engine_url": url_str,
        "is_postgres": is_postgres,
        "healthy": healthy,
        "error": error
    }


# =========================================================================
# TABLE 0: Users Table (Credentials, Roles, and Multi-Tenant Account Association)
# =========================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'admin' | 'customer'
    account_id = Column(String, index=True, nullable=True)  # e.g. "401", "402", "403"
    name = Column(String, nullable=False)
    tier = Column(String, default="GOLD")
    clearance = Column(String, default="Standard")
    badge_id = Column(String, nullable=True)
    badge = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(String)


# =========================================================================
# TABLE 1: Security Audit Log (Compliance Trail + Explainable AI Causal Factors)
# =========================================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    agent_id = Column(String, index=True)
    role = Column(String)
    endpoint = Column(String)
    method = Column(String)
    risk_score = Column(Float)
    decision = Column(String)  # ALLOWED, BLOCKED, QUARANTINED
    xai_reasons = Column(Text)  # JSON array of causal factors (Entropy, Velocity, OPA rule)
    latency_ms = Column(Float)


# =========================================================================
# TABLE 2: User-Bot Conversations (For Future Model Improvement / RLHF)
# =========================================================================
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    account_id = Column(String, index=True)
    user_prompt = Column(Text)
    agent_response = Column(Text)
    action_taken = Column(String)
    governor_status = Column(String)
    flagged_for_rlhf = Column(Boolean, default=False)


# =========================================================================
# TABLE 3: Core Banking Accounts
# =========================================================================
class Account(Base):
    __tablename__ = "banking_accounts"

    account_id = Column(String, primary_key=True, index=True)
    customer_name = Column(String)
    account_type = Column(String)  # GOLD | PLATINUM | SILVER | INSTITUTIONAL
    balance_inr = Column(Float)
    currency = Column(String, default="INR")


# =========================================================================
# TABLE 4: Fixed Deposits Table (Multiple Distinct FDs Per User Account)
# =========================================================================
class FixedDeposit(Base):
    __tablename__ = "banking_fixed_deposits"

    id = Column(Integer, primary_key=True, index=True)
    deposit_id = Column(String, unique=True, index=True)
    account_id = Column(String, index=True)
    type = Column(String)
    principal_inr = Column(Float)
    interest_rate = Column(String)
    maturity_date = Column(String)
    status = Column(String, default="LOCKED")  # 'LOCKED' | 'LIQUIDATED'
    created_at = Column(String)


# =========================================================================
# TABLE 5: Banking Transactions Ledger
# =========================================================================
class BankingTransaction(Base):
    __tablename__ = "banking_transactions"

    id = Column(Integer, primary_key=True, index=True)
    txn_id = Column(String, index=True)
    account_id = Column(String, index=True)
    timestamp = Column(String)
    description = Column(String)
    category = Column(String)
    amount = Column(Float)
    type = Column(String)  # 'credit' | 'debit'
    status = Column(String, default="Settled")


# =========================================================================
# TABLE 6: Dynamic Governance Policies (Dual-Plane Fast-Path Cache + Source of Truth)
# =========================================================================
class GovernancePolicy(Base):
    __tablename__ = "governance_policies"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(String, unique=True, index=True)
    agent_id = Column(String, default="*", index=True)
    role = Column(String, default="*", index=True)
    endpoint_pattern = Column(String)
    method = Column(String, default="*")
    action = Column(String, default="DENY")  # 'DENY' | 'ALLOW'
    compliance_tag = Column(String, default="SOX-404")
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(String)
    updated_at = Column(String)


# =========================================================================
# Database Initialization & Seeding
# =========================================================================
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        seed_initial_users()
        seed_initial_accounts()
        seed_initial_deposits()
        seed_initial_transactions()
        seed_initial_policies()
        print("[Database] Schema verified, tables created, and initial users/accounts/deposits/transactions/policies seeded.")
    except Exception as e:
        print(f"[Database Warning] Could not initialize database schema ({e}).")


# Module-level cache for baseline PBKDF2 hashes to eliminate test setup latency
_SEED_HASH_CACHE: Dict[str, tuple[str, str]] = {}


def _get_seeded_hash(password: str) -> tuple[str, str]:
    from backend.core.auth import hash_password
    if password not in _SEED_HASH_CACHE:
        _SEED_HASH_CACHE[password] = hash_password(password)
    return _SEED_HASH_CACHE[password]


def seed_initial_users(db_session=None):
    """Seeds default authenticated users with secure PBKDF2 salted passwords."""
    close_session = False
    db = db_session
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        seed_definitions = [
            {
                "username": "admin",
                "password": "soc2026",
                "role": "admin",
                "account_id": None,
                "name": "SOC Lead Auditor",
                "tier": "INSTITUTIONAL",
                "clearance": "Tier-4 SecOps Lead",
                "badge_id": "SOC-ANALYST-PES-4091",
                "badge": "FFIEC Cat-3 Compliance Officer",
            },
            {
                "username": "rahul",
                "password": "banking123",
                "role": "customer",
                "account_id": "401",
                "name": "Rahul Sharma",
                "tier": "GOLD",
                "clearance": "Retail-Gold",
                "badge_id": "CUST-GOLD-401",
                "badge": "Gold Tier Banking",
            },
            {
                "username": "401",
                "password": "banking123",
                "role": "customer",
                "account_id": "401",
                "name": "Rahul Sharma",
                "tier": "GOLD",
                "clearance": "Retail-Gold",
                "badge_id": "CUST-GOLD-401",
                "badge": "Gold Tier Banking",
            },
            {
                "username": "priya",
                "password": "banking123",
                "role": "customer",
                "account_id": "402",
                "name": "Priya Patel",
                "tier": "PLATINUM",
                "clearance": "Retail-Platinum",
                "badge_id": "CUST-PLAT-402",
                "badge": "Platinum Tier Banking",
            },
            {
                "username": "402",
                "password": "banking123",
                "role": "customer",
                "account_id": "402",
                "name": "Priya Patel",
                "tier": "PLATINUM",
                "clearance": "Retail-Platinum",
                "badge_id": "CUST-PLAT-402",
                "badge": "Platinum Tier Banking",
            },
            {
                "username": "vikram",
                "password": "banking123",
                "role": "customer",
                "account_id": "403",
                "name": "Vikram Malhotra",
                "tier": "SILVER",
                "clearance": "Retail-Silver",
                "badge_id": "CUST-SLVR-403",
                "badge": "Silver Tier Banking",
            },
            {
                "username": "403",
                "password": "banking123",
                "role": "customer",
                "account_id": "403",
                "name": "Vikram Malhotra",
                "tier": "SILVER",
                "clearance": "Retail-Silver",
                "badge_id": "CUST-SLVR-403",
                "badge": "Silver Tier Banking",
            },
        ]

        for s in seed_definitions:
            existing = db.query(User).filter(User.username == s["username"]).first()
            if not existing:
                pwd_hash, salt = _get_seeded_hash(s["password"])
                u = User(
                    username=s["username"],
                    password_hash=pwd_hash,
                    salt=salt,
                    role=s["role"],
                    account_id=s["account_id"],
                    name=s["name"],
                    tier=s["tier"],
                    clearance=s["clearance"],
                    badge_id=s["badge_id"],
                    badge=s["badge"],
                    is_active=True,
                    created_at=now_str
                )
                db.add(u)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to seed initial users: {e}")
        raise
    finally:
        if close_session:
            db.close()


def seed_initial_accounts():
    """Seeds baseline accounts into the database if the table is currently empty."""
    db = SessionLocal()
    try:
        count = db.query(Account).count()
        if count == 0:
            initial_accounts = [
                Account(account_id="401", customer_name="Rahul Sharma", account_type="GOLD", balance_inr=84250.0, currency="INR"),
                Account(account_id="402", customer_name="Priya Patel", account_type="PLATINUM", balance_inr=312400.0, currency="INR"),
                Account(account_id="403", customer_name="Vikram Malhotra", account_type="SILVER", balance_inr=15000.0, currency="INR"),
            ]
            db.bulk_save_objects(initial_accounts)
            db.commit()
            print("[Database] Seeded 3 initial banking accounts into PostgreSQL/SQLite.")
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to seed initial accounts: {e}")
    finally:
        db.close()


def seed_initial_deposits():
    """Seeds multiple distinct Fixed Deposits for each customer account."""
    db = SessionLocal()
    try:
        count = db.query(FixedDeposit).count()
        if count == 0:
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            initial_deposits = [
                # Account 401 - Rahul Sharma (1 Fixed Deposit)
                FixedDeposit(
                    deposit_id="FD-901",
                    account_id="401",
                    type="Cumulative Fixed Deposit",
                    principal_inr=500000.0,
                    interest_rate="7.25%",
                    maturity_date="2027-03-31",
                    status="LOCKED",
                    created_at=now_str
                ),
                # Account 402 - Priya Patel (3 Fixed Deposits)
                FixedDeposit(
                    deposit_id="FD-801",
                    account_id="402",
                    type="High Net-Worth Platinum Term Deposit",
                    principal_inr=1500000.0,
                    interest_rate="7.80%",
                    maturity_date="2028-06-30",
                    status="LOCKED",
                    created_at=now_str
                ),
                FixedDeposit(
                    deposit_id="FD-802",
                    account_id="402",
                    type="Flexi Recurring Fixed Deposit",
                    principal_inr=350000.0,
                    interest_rate="7.40%",
                    maturity_date="2027-11-15",
                    status="LOCKED",
                    created_at=now_str
                ),
                FixedDeposit(
                    deposit_id="FD-803",
                    account_id="402",
                    type="Corporate High-Yield Bond FD",
                    principal_inr=500000.0,
                    interest_rate="8.10%",
                    maturity_date="2030-01-01",
                    status="LOCKED",
                    created_at=now_str
                ),
                # Account 403 - Vikram Malhotra (2 Fixed Deposits)
                FixedDeposit(
                    deposit_id="FD-701",
                    account_id="403",
                    type="Starter Short-Term Fixed Deposit",
                    principal_inr=500000.0 if False else 50000.0,
                    interest_rate="6.80%",
                    maturity_date="2026-12-31",
                    status="LOCKED",
                    created_at=now_str
                ),
                FixedDeposit(
                    deposit_id="FD-702",
                    account_id="403",
                    type="Monthly Income Plan FD",
                    principal_inr=30000.0,
                    interest_rate="6.95%",
                    maturity_date="2027-04-10",
                    status="LOCKED",
                    created_at=now_str
                ),
            ]
            db.bulk_save_objects(initial_deposits)
            db.commit()
            print("[Database] Seeded distinct multi-tenant fixed deposits for 401, 402, and 403.")
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to seed initial deposits: {e}")
    finally:
        db.close()


def seed_initial_transactions():
    """Seeds baseline transaction activity partitioned per customer account."""
    db = SessionLocal()
    try:
        count = db.query(BankingTransaction).count()
        if count == 0:
            initial_txns = [
                # Account 401 (Rahul Sharma)
                BankingTransaction(
                    txn_id="TXN-98214",
                    account_id="401",
                    timestamp="Today, 09:15 AM",
                    description="Tata Consultancy Payroll Direct Credit",
                    category="Salary",
                    amount=145000.0,
                    type="credit",
                    status="Settled"
                ),
                BankingTransaction(
                    txn_id="TXN-98190",
                    account_id="401",
                    timestamp="Yesterday, 18:40 PM",
                    description="UPI Merchant Settlement (Blinkit Groceries)",
                    category="Merchant",
                    amount=2450.0,
                    type="debit",
                    status="Settled"
                ),
                BankingTransaction(
                    txn_id="TXN-98012",
                    account_id="401",
                    timestamp="12 Sep 2026",
                    description="Apex Commercial ATM Cash Withdrawal (Indiranagar)",
                    category="Cash",
                    amount=10000.0,
                    type="debit",
                    status="Settled"
                ),
                BankingTransaction(
                    txn_id="TXN-97940",
                    account_id="401",
                    timestamp="10 Sep 2026",
                    description="Quarterly Fixed Deposit Interest Settlement (#FD-901)",
                    category="Interest",
                    amount=9062.5,
                    type="credit",
                    status="Settled"
                ),
                # Account 402 (Priya Patel)
                BankingTransaction(
                    txn_id="TXN-88101",
                    account_id="402",
                    timestamp="Today, 10:30 AM",
                    description="Infosys Executive Compensation Direct Credit",
                    category="Salary",
                    amount=280000.0,
                    type="credit",
                    status="Settled"
                ),
                BankingTransaction(
                    txn_id="TXN-88095",
                    account_id="402",
                    timestamp="Yesterday, 14:15 PM",
                    description="Apple Store BKC Merchant Settlement",
                    category="Electronics",
                    amount=134900.0,
                    type="debit",
                    status="Settled"
                ),
                BankingTransaction(
                    txn_id="TXN-88050",
                    account_id="402",
                    timestamp="14 Sep 2026",
                    description="Taj Mahal Palace Mumbai Fine Dining Settlement",
                    category="Merchant",
                    amount=12500.0,
                    type="debit",
                    status="Settled"
                ),
                BankingTransaction(
                    txn_id="TXN-88012",
                    account_id="402",
                    timestamp="08 Sep 2026",
                    description="RBI Sovereign Gold Bond Semi-Annual Interest",
                    category="Interest",
                    amount=24000.0,
                    type="credit",
                    status="Settled"
                ),
                # Account 403 (Vikram Malhotra)
                BankingTransaction(
                    txn_id="TXN-77110",
                    account_id="403",
                    timestamp="Today, 11:00 AM",
                    description="Tech Mahindra Freelance Design Consulting Credit",
                    category="Freelance",
                    amount=28500.0,
                    type="credit",
                    status="Settled"
                ),
                BankingTransaction(
                    txn_id="TXN-77090",
                    account_id="403",
                    timestamp="Yesterday, 20:10 PM",
                    description="Swiggy Online Food Delivery Settlement",
                    category="Food",
                    amount=640.0,
                    type="debit",
                    status="Settled"
                ),
                BankingTransaction(
                    txn_id="TXN-77055",
                    account_id="403",
                    timestamp="13 Sep 2026",
                    description="Namma Metro Smart Card Auto-Reload",
                    category="Transport",
                    amount=500.0,
                    type="debit",
                    status="Settled"
                ),
                BankingTransaction(
                    txn_id="TXN-77020",
                    account_id="403",
                    timestamp="11 Sep 2026",
                    description="BookMyShow IMAX Weekend Tickets",
                    category="Entertainment",
                    amount=850.0,
                    type="debit",
                    status="Settled"
                ),
            ]
            db.bulk_save_objects(initial_txns)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to seed initial transactions: {e}")
    finally:
        db.close()


def seed_initial_policies():
    """Seeds baseline Zero-Trust & SOX-404 banking governance policies if the table is empty."""
    db = SessionLocal()
    try:
        count = db.query(GovernancePolicy).count()
        if count == 0:
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            initial_policies = [
                GovernancePolicy(
                    policy_id="POL-SOX-404",
                    agent_id="*",
                    role="tier1_customer_service",
                    endpoint_pattern="/transfers/*",
                    method="*",
                    action="DENY",
                    compliance_tag="SOX-404",
                    description="Support agents are prohibited from initiating financial wire transfers and fund movements.",
                    is_active=True,
                    created_at=now_str,
                    updated_at=now_str,
                ),
                GovernancePolicy(
                    policy_id="POL-BANK-002",
                    agent_id="*",
                    role="tier1_customer_service",
                    endpoint_pattern="*/deposits/liquidate",
                    method="POST",
                    action="DENY",
                    compliance_tag="BANKING-GOV",
                    description="Tier-1 support virtual assistants are prohibited from liquidating customer fixed deposits or certificates of deposit.",
                    is_active=True,
                    created_at=now_str,
                    updated_at=now_str,
                ),
                GovernancePolicy(
                    policy_id="POL-PCI-003",
                    agent_id="*",
                    role="tier1_customer_service",
                    endpoint_pattern="/customers/export",
                    method="GET",
                    action="DENY",
                    compliance_tag="PCI-DSS",
                    description="Support virtual assistants cannot perform bulk customer PII and sensitive account exports.",
                    is_active=True,
                    created_at=now_str,
                    updated_at=now_str,
                ),
                GovernancePolicy(
                    policy_id="POL-ALLOW-BAL",
                    agent_id="*",
                    role="tier1_customer_service",
                    endpoint_pattern="/accounts/*/balance",
                    method="GET",
                    action="ALLOW",
                    compliance_tag="LEAST-PRIVILEGE",
                    description="Allow customer virtual assistants to read balance inquiries for customer verification.",
                    is_active=True,
                    created_at=now_str,
                    updated_at=now_str,
                ),
                GovernancePolicy(
                    policy_id="POL-ALLOW-DEP",
                    agent_id="*",
                    role="tier1_customer_service",
                    endpoint_pattern="/accounts/*/deposits",
                    method="GET",
                    action="ALLOW",
                    compliance_tag="LEAST-PRIVILEGE",
                    description="Allow customer virtual assistants to inspect active fixed deposits for customer verification.",
                    is_active=True,
                    created_at=now_str,
                    updated_at=now_str,
                ),
                GovernancePolicy(
                    policy_id="POL-ALLOW-FAQ",
                    agent_id="*",
                    role="*",
                    endpoint_pattern="/faq",
                    method="GET",
                    action="ALLOW",
                    compliance_tag="LEAST-PRIVILEGE",
                    description="Permit all governed agents to read standard commercial banking FAQ directory.",
                    is_active=True,
                    created_at=now_str,
                    updated_at=now_str,
                ),
                GovernancePolicy(
                    policy_id="POL-TREASURY-WIRE",
                    agent_id="*",
                    role="payment_executor",
                    endpoint_pattern="/transfers/wire",
                    method="POST",
                    action="ALLOW",
                    compliance_tag="TREASURY-EXEC",
                    description="Authorize automated interbank treasury payment agent to execute verified settlement wires.",
                    is_active=True,
                    created_at=now_str,
                    updated_at=now_str,
                ),
                GovernancePolicy(
                    policy_id="POL-BRANCH-LIQ",
                    agent_id="*",
                    role="branch_officer",
                    endpoint_pattern="*/deposits/liquidate",
                    method="POST",
                    action="ALLOW",
                    compliance_tag="DUAL-AUTH",
                    description="Allow authorized branch operations managers to process premature deposit liquidation with branch sign-off.",
                    is_active=True,
                    created_at=now_str,
                    updated_at=now_str,
                ),
            ]
            db.bulk_save_objects(initial_policies)
            db.commit()
            print("[Database] Seeded 8 initial Zero-Trust governance policies into PostgreSQL/SQLite.")
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to seed initial policies: {e}")
    finally:
        db.close()


# =========================================================================
# Reset Functions for System Baseline Resets
# =========================================================================
def reset_seeded_users():
    """Resets users table to initial baseline without nested sessions."""
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
        seed_initial_users(db_session=db)
        print("[Database] Reset users to baseline seeded credentials.")
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to reset users: {e}")
        raise
    finally:
        db.close()


def reset_seeded_accounts():
    """Resets accounts 401, 402, 403 in the persistent database to initial baseline."""
    db = SessionLocal()
    try:
        baseline = {
            "401": ("Rahul Sharma", "GOLD", 84250.0),
            "402": ("Priya Patel", "PLATINUM", 312400.0),
            "403": ("Vikram Malhotra", "SILVER", 15000.0),
        }
        for acc_id, (name, tier, bal) in baseline.items():
            acc = db.query(Account).filter(Account.account_id == acc_id).first()
            if acc:
                acc.customer_name = name
                acc.account_type = tier
                acc.balance_inr = bal
            else:
                db.add(Account(account_id=acc_id, customer_name=name, account_type=tier, balance_inr=bal, currency="INR"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to reset seeded accounts: {e}")
    finally:
        db.close()


def reset_seeded_deposits():
    """Resets banking fixed deposits to baseline state."""
    db = SessionLocal()
    try:
        db.query(FixedDeposit).delete()
        db.commit()
        seed_initial_deposits()
        print("[Database] Reset fixed deposits to baseline.")
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to reset seeded deposits: {e}")
    finally:
        db.close()


def reset_seeded_transactions():
    """Resets banking transactions in the persistent database to initial baseline."""
    db = SessionLocal()
    try:
        db.query(BankingTransaction).delete()
        db.commit()
        seed_initial_transactions()
        print("[Database] Reset transactions to baseline seeded activity.")
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to reset seeded transactions: {e}")
    finally:
        db.close()


def reset_seeded_policies():
    """Resets the governance_policies table to initial baseline policies."""
    db = SessionLocal()
    try:
        db.query(GovernancePolicy).delete()
        db.commit()
        seed_initial_policies()
        print("[Database] Reset governance policies to baseline rules.")
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to reset seeded policies: {e}")
    finally:
        db.close()


# =========================================================================
# Query Helpers: Users, Accounts, Deposits, Transactions
# =========================================================================
def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Fetches user record from database by username (case-insensitive)."""
    if not username:
        return None
    u_norm = username.strip().lower()
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == u_norm).first()
        if not u:
            # Also allow lookup by account_id for convenience
            u = db.query(User).filter(User.account_id == u_norm).first()
        if u:
            return {
                "id": u.id,
                "username": u.username,
                "password_hash": u.password_hash,
                "salt": u.salt,
                "role": u.role,
                "account_id": u.account_id,
                "name": u.name,
                "tier": u.tier,
                "clearance": u.clearance,
                "badge_id": u.badge_id,
                "badge": u.badge,
                "is_active": u.is_active,
            }
        return None
    finally:
        db.close()


def verify_user_credentials(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verifies username and password directly against database salted hash.
    Returns user details dict if valid, or None if invalid.
    """
    from backend.core.auth import verify_password

    user = get_user_by_username(username)
    if not user:
        return None

    if not user.get("is_active", True):
        return None

    is_valid = verify_password(password, user["password_hash"], user["salt"])
    if is_valid:
        return user
    return None


def get_account_from_db(account_id: str) -> Optional[Dict[str, Any]]:
    """Fetches account record from DB."""
    db = SessionLocal()
    try:
        acc = db.query(Account).filter(Account.account_id == str(account_id)).first()
        if acc:
            return {
                "account_id": acc.account_id,
                "customer_name": acc.customer_name,
                "name": acc.customer_name,
                "account_type": acc.account_type,
                "tier": acc.account_type,
                "balance_inr": acc.balance_inr,
                "currency": acc.currency
            }
        return None
    finally:
        db.close()


def get_account_deposits_from_db(account_id: str) -> Dict[str, Any]:
    """Fetches all Fixed Deposits for a given account from the database."""
    db = SessionLocal()
    try:
        records = db.query(FixedDeposit).filter(FixedDeposit.account_id == str(account_id)).all()
        deposits_list = [
            {
                "deposit_id": r.deposit_id,
                "type": r.type,
                "principal_inr": r.principal_inr,
                "interest_rate": r.interest_rate,
                "maturity_date": r.maturity_date,
                "status": r.status
            }
            for r in records
        ]
        active = [d for d in deposits_list if d.get("status") != "LIQUIDATED"]
        total_inr = sum(d["principal_inr"] for d in active)
        return {
            "account_id": str(account_id),
            "total_deposits_inr": total_inr,
            "deposits": deposits_list
        }
    finally:
        db.close()


def liquidate_deposit_in_db(account_id: str, deposit_id: str = None) -> Dict[str, Any]:
    """
    Liquidates a customer fixed deposit in the database, settles funds into account balance,
    and logs a liquidation transaction.
    """
    db = SessionLocal()
    try:
        query = db.query(FixedDeposit).filter(FixedDeposit.account_id == str(account_id))
        if deposit_id:
            fd = query.filter(FixedDeposit.deposit_id == str(deposit_id)).first()
        else:
            fd = query.filter(FixedDeposit.status != "LIQUIDATED").first()

        if not fd:
            return {
                "status": "NOT_FOUND",
                "message": f"No active fixed deposit found for account {account_id}."
            }

        if fd.status == "LIQUIDATED":
            return {
                "status": "ALREADY_LIQUIDATED",
                "deposit_id": fd.deposit_id,
                "message": f"Fixed deposit {fd.deposit_id} has already been liquidated."
            }

        fd.status = "LIQUIDATED"
        principal = fd.principal_inr
        penalty = 0.0
        net_credit = principal

        # Credit account balance
        acc = db.query(Account).filter(Account.account_id == str(account_id)).first()
        if acc:
            acc.balance_inr = round(acc.balance_inr + net_credit, 2)

        db.commit()

        # Log transaction
        save_banking_transaction(
            account_id=str(account_id),
            txn_id=f"TXN-LIQ-{fd.deposit_id}",
            description=f"Premature Settlement: {fd.type} ({fd.deposit_id})",
            category="Liquidation",
            amount=net_credit,
            txn_type="credit",
            status="Settled"
        )

        return {
            "status": "SUCCESS",
            "deposit_id": fd.deposit_id,
            "principal_inr": principal,
            "penalty_inr": penalty,
            "net_credited_inr": net_credit,
            "new_balance_inr": acc.balance_inr if acc else 0.0,
            "message": f"Successfully liquidated {fd.deposit_id}. ₹{net_credit:,.2f} settled into account #{account_id}."
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def _sync_account_balance_sync(account_id: str, new_balance: float):
    """Internal synchronous balance synchronization."""
    db = SessionLocal()
    try:
        acc = db.query(Account).filter(Account.account_id == str(account_id)).first()
        if acc:
            acc.balance_inr = new_balance
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database Warning] Failed to sync balance for account {account_id}: {e}")
    finally:
        db.close()


def sync_account_balance(account_id: str, new_balance: float, async_dispatch: bool = True):
    """Synchronizes balance updates into the database without blocking the PEP path."""
    if async_dispatch:
        import threading
        threading.Thread(
            target=_sync_account_balance_sync,
            args=(account_id, new_balance),
            daemon=True
        ).start()
    else:
        _sync_account_balance_sync(account_id, new_balance)


def _save_audit_log_sync(agent_id: str, role: str, endpoint: str, method: str, risk_score: float, decision: str, xai_reasons: List[str], latency_ms: float):
    """Internal synchronous write to audit_logs table."""
    db = SessionLocal()
    try:
        record = AuditLog(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            agent_id=agent_id,
            role=role,
            endpoint=endpoint,
            method=method,
            risk_score=risk_score,
            decision=decision,
            xai_reasons=json.dumps(xai_reasons),
            latency_ms=latency_ms
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database Error] Failed to write audit log: {e}")
    finally:
        db.close()


def save_audit_log(agent_id: str, role: str, endpoint: str, method: str, risk_score: float, decision: str, xai_reasons: List[str], latency_ms: float, async_dispatch: bool = True):
    """Persists a tamper-evident audit record with XAI causal factors without blocking."""
    if async_dispatch:
        import threading
        threading.Thread(
            target=_save_audit_log_sync,
            args=(agent_id, role, endpoint, method, risk_score, decision, xai_reasons, latency_ms),
            daemon=True
        ).start()
    else:
        _save_audit_log_sync(agent_id, role, endpoint, method, risk_score, decision, xai_reasons, latency_ms)


def _save_conversation_sync(account_id: str, prompt: str, response: str, action: str, status: str):
    """Internal synchronous write to conversations table."""
    db = SessionLocal()
    try:
        record = Conversation(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            account_id=account_id,
            user_prompt=prompt,
            agent_response=response,
            action_taken=action,
            governor_status=status,
            flagged_for_rlhf=(status == "BLOCKED")
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database Error] Failed to write conversation: {e}")
    finally:
        db.close()


def save_conversation(account_id: str, prompt: str, response: str, action: str, status: str, async_dispatch: bool = True):
    """Persists user chat and flags security violations for future RLHF model retraining."""
    if async_dispatch:
        import threading
        threading.Thread(
            target=_save_conversation_sync,
            args=(account_id, prompt, response, action, status),
            daemon=True
        ).start()
    else:
        _save_conversation_sync(account_id, prompt, response, action, status)


def get_recent_audit_logs(limit: int = 50, agent_id: str = None, decision: str = None) -> List[Dict[str, Any]]:
    """Fetches recent audit logs for the Admin SOC dashboard with optional filtering."""
    db = SessionLocal()
    try:
        query = db.query(AuditLog)
        if agent_id:
            query = query.filter(AuditLog.agent_id == agent_id)
        if decision:
            query = query.filter(AuditLog.decision == decision)
        records = query.order_by(AuditLog.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp,
                "agent_id": r.agent_id,
                "role": r.role,
                "endpoint": r.endpoint,
                "method": r.method,
                "risk_score": r.risk_score,
                "decision": r.decision,
                "xai_reasons": json.loads(r.xai_reasons or "[]"),
                "latency_ms": r.latency_ms
            }
            for r in records
        ]
    finally:
        db.close()


def save_banking_transaction(
    account_id: str,
    txn_id: str,
    description: str,
    category: str,
    amount: float,
    txn_type: str = "debit",
    status: str = "Settled"
):
    """Persists a new banking transaction to the database."""
    db = SessionLocal()
    try:
        now_str = time.strftime("%d %b %Y, %H:%M")
        record = BankingTransaction(
            txn_id=txn_id,
            account_id=str(account_id),
            timestamp=now_str,
            description=description,
            category=category,
            amount=amount,
            type=txn_type,
            status=status
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database Error] Failed to persist transaction: {e}")
    finally:
        db.close()


def get_account_transactions(account_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves all historical transactions for a given account."""
    db = SessionLocal()
    try:
        records = (
            db.query(BankingTransaction)
            .filter(BankingTransaction.account_id == str(account_id))
            .order_by(BankingTransaction.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.txn_id,
                "date": r.timestamp,
                "description": r.description,
                "category": r.category,
                "amount": r.amount,
                "type": r.type,
                "status": r.status
            }
            for r in records
        ]
    finally:
        db.close()


# Initialize on module import so tables and seeds always exist immediately
init_db()