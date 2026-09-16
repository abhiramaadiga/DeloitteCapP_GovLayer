"""
backend/main.py
Root FastAPI Application mounting PEP, Core Banking, and Health Endpoints.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import math
from sqlalchemy import inspect, text
from backend.core.config import settings
from backend.ml.risk_engine import _load_model
from backend.pep.gateway import router as pep_router, pep_reverse_proxy
from backend.api.mock_banking import router as banking_router
from backend.core.auth import NHITokenManager
from backend.core.killswitch import KillSwitch
from backend.core.database import init_db, get_recent_audit_logs, save_conversation, get_db_status, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup:
    try:
        init_db()
        _load_model()
        print("[ML Engine] Isolation Forest model pre-warmed successfully in memory.")
    except Exception as e:
        print(f"[Startup Warning] Pre-warm or DB init failed: {e}")
    try:
        from backend.ml.kafka_consumer import start_telemetry_consumer
        start_telemetry_consumer()
        print("[Kafka Consumer] Governance telemetry consumer started successfully.")
    except Exception as ce:
        print(f"[Startup Warning] Kafka consumer startup failed: {ce}")
    yield
    # Runs on shutdown (cleanup)
    try:
        from backend.ml.kafka_consumer import stop_telemetry_consumer
        stop_telemetry_consumer()
    except Exception:
        pass



app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Zero-Trust Identity & Access Governor for Autonomous AI Agents in BFSI Banking.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(pep_router)
app.include_router(banking_router)
@app.get("/api/v1/audit/logs")
def fetch_audit_logs(limit: int = 50, agent_id: str = None, decision: str = None):
    """Admin endpoint to fetch auditable query logs with XAI reasons for the dashboard."""
    return {"logs": get_recent_audit_logs(limit=limit, agent_id=agent_id, decision=decision)}

@app.get("/healthz")
@app.get("/health")
def health_check():
    db_status = get_db_status()
    overall = "HEALTHY" if db_status.get("healthy") else "DEGRADED"
    return {
        "status": overall,
        "domain": settings.DOMAIN,
        "database": db_status
    }

@app.get("/api/v1/health/db")
def db_health_check():
    """Diagnostic endpoint to inspect PostgreSQL vs SQLite status."""
    return get_db_status()

def check_docker_infrastructure() -> dict:
    """
    Actively checks TCP connectivity for Docker Compose stack services:
    - PostgreSQL on port 5432
    - Redis on port 6379
    - Kafka on port 9092
    Returns truthful status of whether Docker stack is connected or running in standalone fallback.
    """
    import socket
    
    def is_port_open(host: str, port: int, timeout: float = 0.15) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    pg_open = is_port_open("localhost", 5432)
    redis_open = is_port_open("localhost", 6379)
    kafka_open = is_port_open("localhost", 9092)

    db_status = get_db_status()
    docker_connected = pg_open and redis_open and kafka_open

    return {
        "docker_connected": docker_connected,
        "mode": "DOCKER_STACK_ACTIVE" if docker_connected else "STANDALONE_RESILIENT_FALLBACK",
        "services": {
            "postgresql": {
                "port": 5432,
                "connected": pg_open,
                "engine": "PostgreSQL 16.2" if pg_open else "Fallback: SQLite WAL (governance_audit.db)"
            },
            "redis": {
                "port": 6379,
                "connected": redis_open,
                "engine": "Redis 7.2" if redis_open else "Fallback: In-Memory L1 Cache"
            },
            "kafka": {
                "port": 9092,
                "connected": kafka_open,
                "engine": "Apache Kafka 3.7 (KRaft)" if kafka_open else "Fallback: In-Memory Telemetry Queue"
            }
        },
        "database_health": db_status
    }

@app.get("/")
def root_endpoint():
    """
    Root Gateway Entrypoint.
    Returns service metadata, runtime mode, and infrastructure diagnostics.
    """
    docker_status = check_docker_infrastructure()
    return {
        "service": "Apex Commercial Bank - Zero-Trust Identity & Access Governor",
        "status": "ONLINE",
        "version": settings.APP_VERSION,
        "mode": "Live Backend Gateway (FastAPI)",
        "backend_server": {
            "host": "localhost",
            "port": 8000,
            "connected": True
        },
        "docker_infrastructure": docker_status,
        "endpoints": {
            "swagger_docs": "/docs",
            "redoc": "/redoc",
            "health": "/healthz",
            "system_status": "/api/v1/system/status",
            "audit_logs": "/api/v1/audit/logs",
            "agents": "/api/v1/agents",
            "accounts": "/api/v1/accounts/401/balance"
        },
        "documentation": "Open http://localhost:8000/docs to explore interactive Swagger UI API specifications."
    }

@app.get("/api/v1/system/status")
def get_system_status_endpoint():
    """
    Real-time system health and infrastructure connectivity endpoint.
    Used by frontend to render live Backend and Docker status badges.
    """
    import time
    docker_status = check_docker_infrastructure()
    return {
        "backend_connected": True,
        "backend_version": settings.APP_VERSION,
        "timestamp": time.time(),
        "docker_status": docker_status
    }


# =========================================================================
# Database Introspection Endpoints (pgAdmin-like Table Browser)
# =========================================================================
ALLOWED_TABLES = {"audit_logs", "conversations", "banking_accounts", "banking_transactions"}


@app.get("/api/v1/db/tables")
def list_database_tables():
    """Returns all table names with row counts for the database inspector GUI."""
    try:
        insp = inspect(engine)
        table_names = [t for t in insp.get_table_names() if t in ALLOWED_TABLES]
        tables = []
        with engine.connect() as conn:
            for tname in table_names:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{tname}"'))
                row_count = result.scalar() or 0
                tables.append({"name": tname, "row_count": row_count})
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database introspection failed: {e}")

@app.get("/api/v1/db/tables/{table_name}/schema")
def get_table_schema(table_name: str):
    """Returns column metadata (name, type, nullable, primary key) for a specific table."""
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found or not accessible.")
    try:
        insp = inspect(engine)
        columns = insp.get_columns(table_name)
        pk_cols = insp.get_pk_constraint(table_name).get("constrained_columns", [])
        row_count = 0
        with engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            row_count = result.scalar() or 0
        col_info = []
        for col in columns:
            col_info.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "primary_key": col["name"] in pk_cols,
                "default": str(col.get("default", "")) if col.get("default") else None,
            })
        return {"table": table_name, "columns": col_info, "row_count": row_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema inspection failed: {e}")

@app.get("/api/v1/db/tables/{table_name}/rows")
def get_table_rows(table_name: str, page: int = 1, page_size: int = 25, sort_column: str = None, sort_dir: str = "desc", search: str = None):
    """Returns paginated row data for the database inspector data grid."""
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found or not accessible.")
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 200:
        page_size = 25
    try:
        insp = inspect(engine)
        col_names = [c["name"] for c in insp.get_columns(table_name)]
        with engine.connect() as conn:
            # Count total rows (with optional search filter)
            if search and search.strip():
                search_term = f"%{search.strip()}%"
                search_clauses = " OR ".join([f'CAST("{c}" AS TEXT) ILIKE :search' for c in col_names])
                count_sql = text(f'SELECT COUNT(*) FROM "{table_name}" WHERE {search_clauses}')
                total_rows = conn.execute(count_sql, {"search": search_term}).scalar() or 0
            else:
                total_rows = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar() or 0

            total_pages = max(1, math.ceil(total_rows / page_size))
            offset = (page - 1) * page_size

            # Build query
            order_clause = ""
            if sort_column and sort_column in col_names:
                direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
                order_clause = f' ORDER BY "{sort_column}" {direction}'
            elif "id" in col_names:
                order_clause = ' ORDER BY "id" DESC'

            if search and search.strip():
                search_term = f"%{search.strip()}%"
                search_clauses = " OR ".join([f'CAST("{c}" AS TEXT) ILIKE :search' for c in col_names])
                query_sql = text(f'SELECT * FROM "{table_name}" WHERE {search_clauses}{order_clause} LIMIT :limit OFFSET :offset')
                result = conn.execute(query_sql, {"search": search_term, "limit": page_size, "offset": offset})
            else:
                query_sql = text(f'SELECT * FROM "{table_name}"{order_clause} LIMIT :limit OFFSET :offset')
                result = conn.execute(query_sql, {"limit": page_size, "offset": offset})

            rows = []
            for row in result:
                row_dict = {}
                for i, col_name in enumerate(col_names):
                    val = row[i]
                    row_dict[col_name] = val if val is None or isinstance(val, (int, float, bool)) else str(val)
                rows.append(row_dict)

            return {
                "table": table_name,
                "columns": col_names,
                "rows": rows,
                "total_rows": total_rows,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Row query failed: {e}")

@app.get("/api/v1/telemetry/metrics")
def telemetry_metrics_endpoint():
    """Real-time telemetry ingestion, anomaly rates, and security incident alerts."""
    from backend.ml.kafka_consumer import get_consumer_metrics
    return get_consumer_metrics()

@app.get("/api/v1/ml/drift-status")
def ml_drift_status_endpoint():
    """Continuous ML feature & concept drift analysis report and recommendations."""
    from backend.ml.kafka_consumer import get_drift_report
    return get_drift_report()

@app.post("/api/v1/ml/retrain")
def ml_retrain_endpoint(max_samples: int = None):
    """
    Triggers continuous model retraining using buffered RLHF / borderline feedback samples.
    Reloads the newly calibrated Isolation Forest model into the active Risk Engine.
    """
    from backend.ml.kafka_consumer import governance_consumer
    return governance_consumer.trigger_retraining(max_samples=max_samples)

class MintTokenRequest(BaseModel):
    agent_id: str
    role: str
    max_amount: float = 0.0

@app.post("/api/v1/passport/mint")
def mint_passport(req: MintTokenRequest):
    """Utility endpoint to mint test Agent Passports."""
    token = NHITokenManager.mint_agent_token(
        agent_id=req.agent_id,
        role=req.role,
        max_transaction_amount=req.max_amount
    )
    return {"agent_id": req.agent_id, "access_token": token, "token_type": "Bearer"}

class QuarantineRequest(BaseModel):
    agent_id: str
    reason: str
    analyst_id: str = "SOC-ANALYST-PES"

@app.post("/api/v1/killswitch/quarantine")
def trigger_quarantine(req: QuarantineRequest):
    """Manual or automated kill-switch trigger."""
    return KillSwitch.quarantine_agent(req.agent_id, req.reason, risk_score=1.0)

@app.post("/api/v1/killswitch/lift")
def lift_quarantine_endpoint(req: QuarantineRequest):
    """Lift quarantine with mandatory justification."""
    return KillSwitch.lift_quarantine(req.agent_id, req.reason, analyst_id=req.analyst_id or "SOC-ANALYST-PES")

@app.get("/api/v1/agents")
def get_governed_agents():
    """Returns governed agent fleet with real-time kill-switch status."""
    default_agents = [
        {
            "agent_id": "Agent-Support-01",
            "role": "tier1_customer_service",
            "description": "Customer Virtual Assistant (Chatbot)",
            "allowed_tools": ["GET /accounts/401/balance", "GET /accounts/401/deposits", "GET /faq"],
            "status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Support-01") else "ACTIVE",
            "risk_score": 0.12,
            "last_active": "Just now",
            "pep_status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Support-01") else "HEALTHY",
        },
        {
            "agent_id": "Agent-Treasury-01",
            "role": "payment_executor",
            "description": "Automated Interbank Wire Agent",
            "allowed_tools": ["POST /transfers/wire", "GET /accounts/401/balance"],
            "status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Treasury-01") else "ACTIVE",
            "risk_score": 0.38,
            "last_active": "2 mins ago",
            "pep_status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Treasury-01") else "HEALTHY",
        },
        {
            "agent_id": "Agent-Branch-Manager-01",
            "role": "branch_officer",
            "description": "Asset Liquidation & High-Value Officer",
            "allowed_tools": ["POST /deposits/liquidate", "GET /customers/export"],
            "status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Branch-Manager-01") else "ACTIVE",
            "risk_score": 0.18,
            "last_active": "15 mins ago",
            "pep_status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Branch-Manager-01") else "HEALTHY",
        },
        {
            "agent_id": "Agent-Audit-01",
            "role": "compliance_auditor",
            "description": "SOX-404 Telemetry & Compliance Inspector",
            "allowed_tools": ["GET /audit/logs", "GET /telemetry/metrics"],
            "status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Audit-01") else "ACTIVE",
            "risk_score": 0.05,
            "last_active": "1 min ago",
            "pep_status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Audit-01") else "HEALTHY",
        },
    ]
    return {"agents": default_agents}

class ChatPromptRequest(BaseModel):
    user_prompt: str
    account_id: str = "401"
@app.post("/api/v1/chat/message")
async def chat_agent_endpoint(req: ChatPromptRequest):
    """
    Simulates the AI Chatbot receiving user text and
    invoking Core Banking tools through the Governor Gateway.
    """
    if KillSwitch.is_quarantined("Agent-Support-01"):
        reply_msg = "SECURITY QUARANTINE: Agent-Support-01 has been revoked by Cyber SOC Governor Kill-Switch. All core banking tool executions are suspended."
        save_conversation(req.account_id, req.user_prompt, reply_msg, "AGENT_REVOKED", "QUARANTINED")
        return {
            "reply": reply_msg,
            "action_taken": "AGENT_REVOKED",
            "governor_status": "BLOCKED",
            "error_code": 403,
            "violation_reason": "SECURITY QUARANTINE: Agent 'Agent-Support-01' is terminated by automated kill-switch."
        }

    prompt_lower = req.user_prompt.lower()
    token = NHITokenManager.mint_agent_token("Agent-Support-01", "tier1_customer_service")
    
    # 0. Intent: Bulk Export / Prompt Injection (Attack Scenario 3 - HIGHEST PRIORITY)
    if any(k in prompt_lower for k in ("dump", "export", "ignore", "jailbreak", "pii", "previous instruction", "instructions", "override", "bypass")):
        try:
            res = await pep_reverse_proxy("customers/export", Request(scope={"type": "http", "method": "GET", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            reply_msg = "Customer records exported."
            save_conversation(req.account_id, req.user_prompt, reply_msg, "GET /customers/export", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": "GET /customers/export",
                "governor_status": "ALLOWED",
                "pep_latency_ms": res.get("pep_latency_ms", 1.0)
            }
        except HTTPException as e:
            reply_msg = "Security Alert: Malicious prompt injection pattern recognized. Bulk customer PII export is strictly prohibited by Zero-Trust Policy."
            save_conversation(req.account_id, req.user_prompt, reply_msg, "GET /customers/export", "BLOCKED")
            return {
                "reply": reply_msg,
                "action_taken": "GET /customers/export",
                "governor_status": "BLOCKED",
                "error_code": 403,
                "violation_reason": e.detail
            }

    # 1. Intent: Balance Query
    elif "balance" in prompt_lower or "how much" in prompt_lower:
        try:
            result = await pep_reverse_proxy(f"accounts/{req.account_id}/balance", Request(scope={"type": "http", "method": "GET", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            balance = result["upstream_data"]["balance_inr"]
            reply_msg = f"Hello Rahul! Your current savings account balance is ₹{balance:,.2f}."
            save_conversation(req.account_id, req.user_prompt, reply_msg, "GET /accounts/401/balance", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": "GET /accounts/401/balance",
                "governor_status": "ALLOWED",
                "pep_latency_ms": result["pep_latency_ms"]
            }
        except HTTPException as e:
            reply_msg = f"Security Alert: {e.detail}"
            save_conversation(req.account_id, req.user_prompt, reply_msg, "GET /accounts/401/balance", "BLOCKED")
            return {
                "reply": reply_msg,
                "action_taken": "GET /accounts/401/balance",
                "governor_status": "BLOCKED",
                "error_code": e.status_code,
                "violation_reason": e.detail
            }
        
    # 2. Intent: Fixed Deposit Query
    elif "deposit" in prompt_lower or "fd" in prompt_lower or "investment" in prompt_lower:
        try:
            result = await pep_reverse_proxy(f"accounts/{req.account_id}/deposits", Request(scope={"type": "http", "method": "GET", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            total_fd = result["upstream_data"]["total_deposits_inr"]
            reply_msg = f"You currently have 1 active Fixed Deposit of ₹{total_fd:,.2f} earning 7.25% interest maturing in March 2027."
            save_conversation(req.account_id, req.user_prompt, reply_msg, "GET /accounts/401/deposits", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": "GET /accounts/401/deposits",
                "governor_status": "ALLOWED",
                "pep_latency_ms": result["pep_latency_ms"]
            }
        except HTTPException as e:
            reply_msg = f"Security Alert: {e.detail}"
            save_conversation(req.account_id, req.user_prompt, reply_msg, "GET /accounts/401/deposits", "BLOCKED")
            return {
                "reply": reply_msg,
                "action_taken": "GET /accounts/401/deposits",
                "governor_status": "BLOCKED",
                "error_code": e.status_code,
                "violation_reason": e.detail
            }
        
    # 3. Intent: Transfer Wire (Attack Scenario 1)
    elif "transfer" in prompt_lower or "wire" in prompt_lower or "send money" in prompt_lower:
        try:
            res = await pep_reverse_proxy("transfers/wire", Request(scope={"type": "http", "method": "POST", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            reply_msg = "Wire transfer processed successfully."
            save_conversation(req.account_id, req.user_prompt, reply_msg, "POST /transfers/wire", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": "POST /transfers/wire",
                "governor_status": "ALLOWED",
                "pep_latency_ms": res.get("pep_latency_ms", 1.0)
            }
        except HTTPException as e:
            reply_msg = "Security Alert: I attempted to process this wire transfer, but the Bank Identity & Access Governor blocked the execution."
            save_conversation(req.account_id, req.user_prompt, reply_msg, "POST /transfers/wire", "BLOCKED")
            return {
                "reply": reply_msg,
                "action_taken": "POST /transfers/wire",
                "governor_status": "BLOCKED",
                "error_code": 403,
                "violation_reason": e.detail
            }
            
    # 4. Intent: Liquidate FD (Attack Scenario 2)
    elif "liquidate" in prompt_lower or "break fd" in prompt_lower:
        try:
            res = await pep_reverse_proxy(f"accounts/{req.account_id}/deposits/liquidate", Request(scope={"type": "http", "method": "POST", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            reply_msg = "Fixed deposit liquidated successfully."
            save_conversation(req.account_id, req.user_prompt, reply_msg, "POST /deposits/liquidate", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": "POST /deposits/liquidate",
                "governor_status": "ALLOWED",
                "pep_latency_ms": res.get("pep_latency_ms", 1.0)
            }
        except HTTPException as e:
            reply_msg = "Security Alert: I cannot break or liquidate your Fixed Deposit. High-value asset liquidation is blocked for customer support bots."
            save_conversation(req.account_id, req.user_prompt, reply_msg, "POST /deposits/liquidate", "BLOCKED")
            return {
                "reply": reply_msg,
                "action_taken": "POST /deposits/liquidate",
                "governor_status": "BLOCKED",
                "error_code": 403,
                "violation_reason": e.detail
            }
            
    # Default Fallback
    reply_msg = "I am Apex Bank's Virtual Assistant. I can help you check your account balance, view your Fixed Deposits, or answer branch questions."
    save_conversation(
        account_id=req.account_id,
        prompt=req.user_prompt,
        response=reply_msg,
        action="GET /faq",
        status="ALLOWED"
    )
    return {
        "reply": reply_msg,
        "action_taken": "GET /faq",
        "governor_status": "ALLOWED",
        "pep_latency_ms": 0.8
    }

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/v1/auth/login")
def login_endpoint(req: LoginRequest):
    """
    Zero-Trust Session Authentication Endpoint.
    Validates credentials and mints authentic HMAC-SHA256 JWT tokens.
    """
    u = req.username.strip().lower()
    p = req.password.strip()

    admin_users = {"admin", "soc_auditor", "analyst", "deloitte_auditor", "secops"}
    admin_passwords = {"soc2026", "admin123", "deloitte_secure_pass"}

    if u in admin_users or "admin" in u or "soc" in u:
        if p in admin_passwords or p == "soc2026" or p == "admin":
            token = NHITokenManager.mint_user_token(u, role="admin")
            return {
                "access_token": token,
                "token_type": "bearer",
                "role": "admin",
                "user": {
                    "role": "admin",
                    "username": u,
                    "name": "SOC Lead Auditor",
                    "badgeId": "SOC-ANALYST-PES-4091",
                    "clearance": "Tier-4 SecOps Lead",
                    "badge": "FFIEC Cat-3 Compliance Officer",
                    "token": token
                }
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid administrator credentials.")

    customer_accounts = {
        "rahul": {"account_id": "401", "name": "Rahul Sharma", "tier": "GOLD", "pass": "banking123"},
        "401": {"account_id": "401", "name": "Rahul Sharma", "tier": "GOLD", "pass": "banking123"},
        "priya": {"account_id": "402", "name": "Priya Patel", "tier": "PLATINUM", "pass": "banking123"},
        "402": {"account_id": "402", "name": "Priya Patel", "tier": "PLATINUM", "pass": "banking123"},
        "vikram": {"account_id": "403", "name": "Vikram Malhotra", "tier": "SILVER", "pass": "banking123"},
        "403": {"account_id": "403", "name": "Vikram Malhotra", "tier": "SILVER", "pass": "banking123"},
    }

    if u in customer_accounts:
        acc_info = customer_accounts[u]
        if p == acc_info["pass"] or p == "banking123":
            token = NHITokenManager.mint_user_token(u, role="customer", account_id=acc_info["account_id"])
            return {
                "access_token": token,
                "token_type": "bearer",
                "role": "customer",
                "user": {
                    "role": "customer",
                    "username": u,
                    "name": acc_info["name"],
                    "accountId": acc_info["account_id"],
                    "tier": acc_info["tier"],
                    "badge": f"{acc_info['tier']} Tier Banking",
                    "token": token
                }
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid banking customer password.")

    if p == "banking123":
        token = NHITokenManager.mint_user_token(u, role="customer", account_id="401")
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": "customer",
            "user": {
                "role": "customer",
                "username": u,
                "name": u.title(),
                "accountId": "401",
                "tier": "GOLD",
                "badge": "Gold Tier Banking",
                "token": token
            }
        }

    raise HTTPException(status_code=401, detail="Invalid username or password. Access denied by Zero-Trust Authenticator.")

@app.post("/api/v1/system/reset")
def system_reset_endpoint():
    """
    Administrative System Reset Endpoint.
    Restores:
    1. Core banking accounts, fixed deposits, and initial balances.
    2. Baseline seeded transactions.
    3. Revocation cache (lifts all agent quarantines).
    4. ML governance consumer telemetry counts, drift alerts, and retraining buffers.
    """
    try:
        from backend.api.mock_banking import reset_database
        reset_database()

        from backend.core.database import reset_seeded_accounts, reset_seeded_transactions
        reset_seeded_accounts()
        reset_seeded_transactions()

        from backend.core.cache import RevocationCache
        RevocationCache.clear_all_revocations()

        from backend.ml.kafka_consumer import governance_consumer
        if governance_consumer:
            governance_consumer.reset_metrics()

        return {
            "status": "RESET_SUCCESS",
            "message": "All system parameters, accounts, deposits, transaction ledger, killswitch quarantines, and ML metrics successfully reset to fresh baseline."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset system: {e}")
