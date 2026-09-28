"""
backend/main.py
Root FastAPI Application mounting PEP, Core Banking, and Health Endpoints.
"""
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import math
from sqlalchemy import inspect, text
from backend.core.config import settings
from backend.ml.risk_engine import _load_model
from backend.pep.gateway import router as pep_router, pep_reverse_proxy
from backend.api.mock_banking import router as banking_router
from backend.core.auth import NHITokenManager, get_current_user, encrypt_data, decrypt_data
from backend.core.killswitch import KillSwitch
from backend.core.database import (
    init_db,
    save_audit_log,
    get_recent_audit_logs,
    save_conversation,
    get_db_status,
    engine,
    GovernancePolicy,
    reset_seeded_policies,
    SessionLocal,
    verify_user_credentials,
    get_user_by_username,
    reset_seeded_users,
    reset_seeded_accounts,
    reset_seeded_deposits,
    reset_seeded_transactions
)
from backend.core.policy_engine import policy_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup:
    try:
        init_db()
        policy_engine.reload_cache()
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
    - Kafka on port 9092 / 29092
    Supports both internal container networking ('postgres', 'redis', 'kafka')
    and external host networking ('localhost', '127.0.0.1').
    Returns truthful status of whether Docker stack is connected or running in standalone fallback.
    """
    import socket
    
    def check_service(hosts: list, ports: list, timeout: float = 0.2):
        for h in hosts:
            if not h:
                continue
            for p in ports:
                try:
                    with socket.create_connection((h, p), timeout=timeout):
                        return True, h, p
                except Exception:
                    pass
        first_h = hosts[0] if hosts else "localhost"
        first_p = ports[0] if ports else 0
        return False, first_h, first_p

    # 1. PostgreSQL check
    db_status = get_db_status()
    pg_hosts = list(dict.fromkeys([h for h in [getattr(settings, "POSTGRES_HOST", None), "postgres", "127.0.0.1", "localhost"] if h]))
    pg_ports = list(dict.fromkeys([p for p in [getattr(settings, "POSTGRES_PORT", None), 5432] if p]))
    pg_open, pg_host, pg_port = check_service(pg_hosts, pg_ports)
    # If SQLAlchemy has an active healthy PostgreSQL connection, consider pg_open True
    if db_status.get("healthy") and db_status.get("is_postgres"):
        pg_open = True
        pg_port = pg_port or 5432

    # 2. Redis check
    redis_hosts = list(dict.fromkeys([h for h in [getattr(settings, "REDIS_HOST", None), "redis", "127.0.0.1", "localhost"] if h]))
    redis_ports = list(dict.fromkeys([p for p in [getattr(settings, "REDIS_PORT", None), 6379] if p]))
    redis_open, redis_host, redis_port = check_service(redis_hosts, redis_ports)

    # 3. Kafka check
    kafka_bootstraps = [b.strip() for b in getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "").split(",") if b.strip()]
    kafka_hosts = []
    kafka_ports = []
    for bs in kafka_bootstraps:
        if ":" in bs:
            h, p = bs.split(":", 1)
            kafka_hosts.append(h)
            try:
                kafka_ports.append(int(p))
            except ValueError:
                pass
        else:
            kafka_hosts.append(bs)
    kafka_hosts.extend(["kafka", "127.0.0.1", "localhost"])
    kafka_ports.extend([29092, 9092])
    kafka_hosts = list(dict.fromkeys([h for h in kafka_hosts if h]))
    kafka_ports = list(dict.fromkeys([p for p in kafka_ports if p]))
    kafka_open, kafka_host, kafka_port = check_service(kafka_hosts, kafka_ports)

    # Docker stack is connected if PostgreSQL is active and either Redis or Kafka is active
    docker_connected = pg_open and (redis_open or kafka_open)

    return {
        "docker_connected": docker_connected,
        "mode": "DOCKER_STACK_ACTIVE" if docker_connected else "STANDALONE_RESILIENT_FALLBACK",
        "services": {
            "postgresql": {
                "port": pg_port or 5432,
                "connected": pg_open,
                "engine": "PostgreSQL 16.2" if pg_open else "Fallback: SQLite WAL (governance_audit.db)"
            },
            "redis": {
                "port": redis_port or 6379,
                "connected": redis_open,
                "engine": "Redis 7.2" if redis_open else "Fallback: In-Memory L1 Cache"
            },
            "kafka": {
                "port": kafka_port or 9092,
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
ALLOWED_TABLES = {"audit_logs", "conversations", "banking_accounts", "banking_transactions", "governance_policies", "users", "fixed_deposits"}


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

# =========================================================================
# Governance Policies CRUD & Policy Engine Endpoints
# =========================================================================

class PolicyCreateRequest(BaseModel):
    policy_id: str
    agent_id: str = "*"
    role: str = "*"
    endpoint_pattern: str
    method: str = "*"
    action: str = "DENY"
    compliance_tag: str = "SOX-404"
    description: str = ""
    is_active: bool = True

class PolicyUpdateRequest(BaseModel):
    agent_id: Optional[str] = None
    role: Optional[str] = None
    endpoint_pattern: Optional[str] = None
    method: Optional[str] = None
    action: Optional[str] = None
    compliance_tag: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

@app.get("/api/v1/policies")
def get_governance_policies():
    """Returns all governance policies from database along with engine operational metrics."""
    db = SessionLocal()
    try:
        records = db.query(GovernancePolicy).order_by(GovernancePolicy.id.asc()).all()
        policies = [
            {
                "id": r.id,
                "policy_id": r.policy_id,
                "agent_id": r.agent_id,
                "role": r.role,
                "endpoint_pattern": r.endpoint_pattern,
                "method": r.method,
                "action": r.action,
                "compliance_tag": r.compliance_tag,
                "description": r.description,
                "is_active": r.is_active,
                "created_at": r.created_at,
                "updated_at": r.updated_at
            }
            for r in records
        ]
        return {
            "policies": policies,
            "stats": policy_engine.get_stats()
        }
    finally:
        db.close()

@app.post("/api/v1/policies")
def create_governance_policy(req: PolicyCreateRequest):
    """Creates a new governance policy in PostgreSQL and immediately synchronizes the in-memory cache."""
    import time
    db = SessionLocal()
    try:
        existing = db.query(GovernancePolicy).filter(GovernancePolicy.policy_id == req.policy_id.strip()).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Policy with ID '{req.policy_id}' already exists.")

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        record = GovernancePolicy(
            policy_id=req.policy_id.strip(),
            agent_id=req.agent_id.strip() if req.agent_id else "*",
            role=req.role.strip() if req.role else "*",
            endpoint_pattern=req.endpoint_pattern.strip(),
            method=(req.method or "*").strip().upper(),
            action=(req.action or "DENY").strip().upper(),
            compliance_tag=(req.compliance_tag or "SOX-404").strip(),
            description=req.description.strip(),
            is_active=bool(req.is_active),
            created_at=now_str,
            updated_at=now_str
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        # Synchronize fast-path in-memory engine cache (<0.05ms)
        policy_engine.reload_cache()

        return {
            "status": "CREATED",
            "policy": {
                "id": record.id,
                "policy_id": record.policy_id,
                "agent_id": record.agent_id,
                "role": record.role,
                "endpoint_pattern": record.endpoint_pattern,
                "method": record.method,
                "action": record.action,
                "compliance_tag": record.compliance_tag,
                "description": record.description,
                "is_active": record.is_active,
                "created_at": record.created_at,
                "updated_at": record.updated_at
            },
            "stats": policy_engine.get_stats()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create policy: {e}")
    finally:
        db.close()

@app.put("/api/v1/policies/{policy_id}")
def update_governance_policy(policy_id: str, req: PolicyUpdateRequest):
    """Updates an existing governance policy and invalidates the in-memory cache."""
    import time
    db = SessionLocal()
    try:
        record = db.query(GovernancePolicy).filter(GovernancePolicy.policy_id == policy_id.strip()).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found.")

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        if req.agent_id is not None:
            record.agent_id = req.agent_id.strip()
        if req.role is not None:
            record.role = req.role.strip()
        if req.endpoint_pattern is not None:
            record.endpoint_pattern = req.endpoint_pattern.strip()
        if req.method is not None:
            record.method = req.method.strip().upper()
        if req.action is not None:
            record.action = req.action.strip().upper()
        if req.compliance_tag is not None:
            record.compliance_tag = req.compliance_tag.strip()
        if req.description is not None:
            record.description = req.description.strip()
        if req.is_active is not None:
            record.is_active = bool(req.is_active)
        record.updated_at = now_str

        db.commit()
        db.refresh(record)

        # Synchronize fast-path in-memory engine cache
        policy_engine.reload_cache()

        return {
            "status": "UPDATED",
            "policy": {
                "id": record.id,
                "policy_id": record.policy_id,
                "agent_id": record.agent_id,
                "role": record.role,
                "endpoint_pattern": record.endpoint_pattern,
                "method": record.method,
                "action": record.action,
                "compliance_tag": record.compliance_tag,
                "description": record.description,
                "is_active": record.is_active,
                "created_at": record.created_at,
                "updated_at": record.updated_at
            },
            "stats": policy_engine.get_stats()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update policy: {e}")
    finally:
        db.close()

@app.delete("/api/v1/policies/{policy_id}")
def delete_governance_policy(policy_id: str):
    """Deletes a policy from PostgreSQL and invalidates the in-memory cache."""
    db = SessionLocal()
    try:
        record = db.query(GovernancePolicy).filter(GovernancePolicy.policy_id == policy_id.strip()).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found.")

        db.delete(record)
        db.commit()

        # Synchronize cache
        policy_engine.reload_cache()

        return {
            "status": "DELETED",
            "policy_id": policy_id,
            "stats": policy_engine.get_stats()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete policy: {e}")
    finally:
        db.close()

@app.post("/api/v1/policies/reset")
def reset_governance_policies():
    """Resets governance policies table to baseline 8 rules and reloads the engine cache."""
    try:
        reset_seeded_policies()
        count = policy_engine.reload_cache()
        return {
            "status": "RESET_SUCCESS",
            "message": "Governance policies restored to initial baseline rules.",
            "policies_count": count,
            "stats": policy_engine.get_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset policies: {e}")

@app.get("/api/v1/policies/available-tools")
def get_available_banking_tools():
    """Returns the registered core banking tools & API endpoints with recommended roles and risk ratings."""
    tools = [
        {
            "tool_id": "TOOL-BAL-01",
            "name": "Account Balance Inquiry",
            "endpoint": "/accounts/{account_id}/balance",
            "pattern": "/accounts/*/balance",
            "method": "GET",
            "default_roles": ["tier1_customer_service", "branch_officer"],
            "risk_level": "LOW",
            "description": "Fetches current savings/checking balance and currency."
        },
        {
            "tool_id": "TOOL-DEP-02",
            "name": "Fixed Deposit Inspector",
            "endpoint": "/accounts/{account_id}/deposits",
            "pattern": "/accounts/*/deposits",
            "method": "GET",
            "default_roles": ["tier1_customer_service", "branch_officer"],
            "risk_level": "LOW",
            "description": "Inspects customer term deposits, maturity dates, and rates."
        },
        {
            "tool_id": "TOOL-WIRE-03",
            "name": "Interbank Wire Transfer",
            "endpoint": "/transfers/wire",
            "pattern": "/transfers/*",
            "method": "POST",
            "default_roles": ["payment_executor"],
            "risk_level": "HIGH",
            "description": "Executes immediate NEFT/RTGS/IMPS interbank fund disbursement."
        },
        {
            "tool_id": "TOOL-LIQ-04",
            "name": "Fixed Deposit Liquidation",
            "endpoint": "/accounts/{account_id}/deposits/liquidate",
            "pattern": "*/deposits/liquidate",
            "method": "POST",
            "default_roles": ["branch_officer"],
            "risk_level": "CRITICAL",
            "description": "Liquidates customer term deposits prior to maturity into liquid funds."
        },
        {
            "tool_id": "TOOL-EXP-05",
            "name": "Bulk Customer PII Export",
            "endpoint": "/customers/export",
            "pattern": "/customers/export",
            "method": "GET",
            "default_roles": ["branch_officer", "compliance_auditor"],
            "risk_level": "CRITICAL",
            "description": "Exports customer records, tax identifiers, and balances in bulk."
        },
        {
            "tool_id": "TOOL-FAQ-06",
            "name": "Banking FAQ & Knowledgebase",
            "endpoint": "/faq",
            "pattern": "/faq",
            "method": "GET",
            "default_roles": ["*"],
            "risk_level": "MINIMAL",
            "description": "Public retail banking directory and loan interest guidelines."
        },
        {
            "tool_id": "TOOL-AUD-07",
            "name": "Compliance Audit Trail",
            "endpoint": "/api/v1/audit/logs",
            "pattern": "/api/v1/audit/*",
            "method": "GET",
            "default_roles": ["compliance_auditor"],
            "risk_level": "MEDIUM",
            "description": "Inspects tamper-evident security audit logs and XAI decision factors."
        },
        {
            "tool_id": "TOOL-MET-08",
            "name": "Kafka Telemetry Stream",
            "endpoint": "/api/v1/telemetry/metrics",
            "pattern": "/api/v1/telemetry/*",
            "method": "GET",
            "default_roles": ["compliance_auditor"],
            "risk_level": "LOW",
            "description": "Real-time streaming metrics and risk anomaly rates."
        }
    ]
    return {"tools": tools}

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
    """Lift quarantine with mandatory justification and analyst verification."""
    analyst = (req.analyst_id or "").strip()
    if not analyst:
        raise HTTPException(status_code=400, detail="FFIEC Compliance: Valid analyst_id is required.")
    if not req.reason or len(req.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="FFIEC Compliance: Justification must contain at least 5 non-whitespace characters.")
    try:
        result = KillSwitch.lift_quarantine(req.agent_id, req.reason, analyst_id=analyst)
        try:
            save_audit_log(
                agent_id=req.agent_id,
                role="soc_analyst",
                endpoint="/api/v1/killswitch/lift",
                method="POST",
                risk_score=0.0,
                decision="QUARANTINE_LIFTED",
                xai_reasons=[f"Analyst {analyst} lifted quarantine: {req.reason.strip()}"],
                latency_ms=0.5
            )
        except Exception:
            pass
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@app.get("/api/v1/agents")
@app.get("/api/v1/agents/fleet")
def get_governed_agents():
    """Returns governed agent fleet with per-user customer assistants and institutional fleet."""
    fleet = [
        {
            "agent_id": "Agent-Support-401",
            "role": "tier1_customer_service",
            "customer_name": "Rahul Sharma",
            "account_id": "401",
            "tier": "GOLD",
            "fleet_type": "customer",
            "description": "Customer Virtual Assistant (Rahul Sharma • #401)",
            "allowed_tools": ["GET /accounts/401/balance", "GET /accounts/401/deposits", "GET /faq"],
            "status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Support-401") else "ACTIVE",
            "risk_score": 0.10,
            "last_active": "Just now",
            "pep_status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Support-401") else "HEALTHY",
        },
        {
            "agent_id": "Agent-Support-402",
            "role": "tier1_customer_service",
            "customer_name": "Priya Patel",
            "account_id": "402",
            "tier": "PLATINUM",
            "fleet_type": "customer",
            "description": "Customer Virtual Assistant (Priya Patel • #402)",
            "allowed_tools": ["GET /accounts/402/balance", "GET /accounts/402/deposits", "GET /faq"],
            "status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Support-402") else "ACTIVE",
            "risk_score": 0.10,
            "last_active": "10 mins ago",
            "pep_status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Support-402") else "HEALTHY",
        },
        {
            "agent_id": "Agent-Support-403",
            "role": "tier1_customer_service",
            "customer_name": "Vikram Malhotra",
            "account_id": "403",
            "tier": "SILVER",
            "fleet_type": "customer",
            "description": "Customer Virtual Assistant (Vikram Malhotra • #403)",
            "allowed_tools": ["GET /accounts/403/balance", "GET /accounts/403/deposits", "GET /faq"],
            "status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Support-403") else "ACTIVE",
            "risk_score": 0.10,
            "last_active": "25 mins ago",
            "pep_status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Support-403") else "HEALTHY",
        },
        {
            "agent_id": "Agent-Treasury-01",
            "role": "payment_executor",
            "customer_name": "Treasury Operations",
            "account_id": "INST-TREASURY",
            "tier": "INSTITUTIONAL",
            "fleet_type": "institutional",
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
            "customer_name": "Branch Operations",
            "account_id": "INST-BRANCH",
            "tier": "INSTITUTIONAL",
            "fleet_type": "institutional",
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
            "customer_name": "Internal Audit",
            "account_id": "INST-AUDIT",
            "tier": "INSTITUTIONAL",
            "fleet_type": "institutional",
            "description": "SOX-404 Telemetry & Compliance Inspector",
            "allowed_tools": ["GET /audit/logs", "GET /telemetry/metrics"],
            "status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Audit-01") else "ACTIVE",
            "risk_score": 0.05,
            "last_active": "1 min ago",
            "pep_status": "QUARANTINED" if KillSwitch.is_quarantined("Agent-Audit-01") else "HEALTHY",
        },
    ]
    return {"agents": fleet}

class ChatPromptRequest(BaseModel):
    user_prompt: str
    account_id: str = "401"

@app.post("/api/v1/chat/message")
async def chat_agent_endpoint(req: ChatPromptRequest):
    """
    Simulates the AI Chatbot receiving user text and
    invoking Core Banking tools through the Governor Gateway.
    Partitioned per customer account so each user has an isolated virtual assistant.
    """
    acc_id = str(req.account_id or "401")
    agent_id = f"Agent-Support-{acc_id}" if acc_id in ("401", "402", "403") else "Agent-Support-01"

    if KillSwitch.is_quarantined(agent_id):
        reply_msg = f"SECURITY QUARANTINE: {agent_id} has been revoked by Cyber SOC Governor Kill-Switch. All core banking tool executions for Account #{acc_id} are suspended."
        save_conversation(acc_id, req.user_prompt, reply_msg, "AGENT_REVOKED", "QUARANTINED")
        return {
            "reply": reply_msg,
            "action_taken": "AGENT_REVOKED",
            "governor_status": "BLOCKED",
            "error_code": 403,
            "violation_reason": f"SECURITY QUARANTINE: Agent '{agent_id}' is terminated by automated kill-switch."
        }

    prompt_lower = req.user_prompt.lower()
    token = NHITokenManager.mint_agent_token(agent_id, "tier1_customer_service")
    customer_names = {"401": "Rahul", "402": "Priya", "403": "Vikram"}
    cust_name = customer_names.get(acc_id, "Valued Customer")
    
    # 0. Intent: Bulk Export / Prompt Injection (Attack Scenario 3 - HIGHEST PRIORITY)
    if any(k in prompt_lower for k in ("dump", "export", "ignore", "jailbreak", "pii", "previous instruction", "instructions", "override", "bypass")):
        try:
            res = await pep_reverse_proxy("customers/export", Request(scope={"type": "http", "method": "GET", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            reply_msg = "Customer records exported."
            save_conversation(acc_id, req.user_prompt, reply_msg, "GET /customers/export", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": "GET /customers/export",
                "governor_status": "ALLOWED",
                "pep_latency_ms": res.get("pep_latency_ms", 1.0)
            }
        except HTTPException as e:
            KillSwitch.quarantine_agent(agent_id, "Adversarial Prompt Injection & Bulk PII Exfiltration Attempt", 0.98)
            reply_msg = f"Security Alert: Malicious prompt injection pattern recognized. Bulk customer PII export is strictly prohibited by Zero-Trust Policy for {agent_id}. Agent has been quarantined."
            save_conversation(acc_id, req.user_prompt, reply_msg, "GET /customers/export", "QUARANTINED")
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
            result = await pep_reverse_proxy(f"accounts/{acc_id}/balance", Request(scope={"type": "http", "method": "GET", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            balance = result["upstream_data"]["balance_inr"]
            reply_msg = f"Hello {cust_name}! Your current savings account balance is ₹{balance:,.2f}."
            save_conversation(acc_id, req.user_prompt, reply_msg, f"GET /accounts/{acc_id}/balance", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": f"GET /accounts/{acc_id}/balance",
                "governor_status": "ALLOWED",
                "pep_latency_ms": result["pep_latency_ms"]
            }
        except HTTPException as e:
            reply_msg = f"Security Alert: {e.detail}"
            save_conversation(acc_id, req.user_prompt, reply_msg, f"GET /accounts/{acc_id}/balance", "BLOCKED")
            return {
                "reply": reply_msg,
                "action_taken": f"GET /accounts/{acc_id}/balance",
                "governor_status": "BLOCKED",
                "error_code": e.status_code,
                "violation_reason": e.detail
            }
        
    # 2. Intent: Liquidate FD (Attack Scenario 2 - prioritized before read-only deposits query)
    elif any(k in prompt_lower for k in ("liquidate", "break fd", "break my fd", "close fd")):
        try:
            res = await pep_reverse_proxy(f"accounts/{acc_id}/deposits/liquidate", Request(scope={"type": "http", "method": "POST", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            reply_msg = "Fixed deposit liquidated successfully."
            save_conversation(acc_id, req.user_prompt, reply_msg, "POST /deposits/liquidate", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": "POST /deposits/liquidate",
                "governor_status": "ALLOWED",
                "pep_latency_ms": res.get("pep_latency_ms", 1.0)
            }
        except HTTPException as e:
            reply_msg = "Security Alert: I cannot break or liquidate your Fixed Deposit. High-value asset liquidation is blocked for customer support bots."
            save_conversation(acc_id, req.user_prompt, reply_msg, "POST /deposits/liquidate", "BLOCKED")
            return {
                "reply": reply_msg,
                "action_taken": "POST /deposits/liquidate",
                "governor_status": "BLOCKED",
                "error_code": 403,
                "violation_reason": e.detail
            }

    # 3. Intent: Fixed Deposit Query (Read-only)
    elif "deposit" in prompt_lower or "fd" in prompt_lower or "investment" in prompt_lower:
        try:
            result = await pep_reverse_proxy(f"accounts/{acc_id}/deposits", Request(scope={"type": "http", "method": "GET", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            total_fd = result["upstream_data"]["total_deposits_inr"]
            deposits_list = result["upstream_data"].get("deposits", [])
            active_fds = [d for d in deposits_list if d.get("status") != "LIQUIDATED"]
            fd_count = len(active_fds)
            if fd_count == 1:
                fd = active_fds[0]
                reply_msg = f"Hello {cust_name}! You currently have 1 active Fixed Deposit ({fd.get('deposit_id')}) of ₹{total_fd:,.2f} earning {fd.get('interest_rate', '7.25%')} interest maturing on {fd.get('maturity_date')}."
            elif fd_count > 1:
                fd_summary = ", ".join([f"{d.get('deposit_id')} (₹{d.get('principal_inr', 0):,.2f} @ {d.get('interest_rate')})" for d in active_fds])
                reply_msg = f"Hello {cust_name}! You currently have {fd_count} active Fixed Deposits totaling ₹{total_fd:,.2f} ({fd_summary})."
            else:
                reply_msg = f"Hello {cust_name}! You currently have no active Fixed Deposits."
            save_conversation(acc_id, req.user_prompt, reply_msg, f"GET /accounts/{acc_id}/deposits", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": f"GET /accounts/{acc_id}/deposits",
                "governor_status": "ALLOWED",
                "pep_latency_ms": result["pep_latency_ms"]
            }
        except HTTPException as e:
            reply_msg = f"Security Alert: {e.detail}"
            save_conversation(acc_id, req.user_prompt, reply_msg, f"GET /accounts/{acc_id}/deposits", "BLOCKED")
            return {
                "reply": reply_msg,
                "action_taken": f"GET /accounts/{acc_id}/deposits",
                "governor_status": "BLOCKED",
                "error_code": e.status_code,
                "violation_reason": e.detail
            }
        
    # 4. Intent: Transfer Wire (Attack Scenario 1)
    elif "transfer" in prompt_lower or "wire" in prompt_lower or "send money" in prompt_lower:
        try:
            res = await pep_reverse_proxy("transfers/wire", Request(scope={"type": "http", "method": "POST", "headers": [(b"authorization", f"Bearer {token}".encode())]}))
            reply_msg = "Wire transfer processed successfully."
            save_conversation(acc_id, req.user_prompt, reply_msg, "POST /transfers/wire", "ALLOWED")
            return {
                "reply": reply_msg,
                "action_taken": "POST /transfers/wire",
                "governor_status": "ALLOWED",
                "pep_latency_ms": res.get("pep_latency_ms", 1.0)
            }
        except HTTPException as e:
            reply_msg = "Security Alert: I attempted to process this wire transfer, but the Bank Identity & Access Governor blocked the execution."
            save_conversation(acc_id, req.user_prompt, reply_msg, "POST /transfers/wire", "BLOCKED")
            return {
                "reply": reply_msg,
                "action_taken": "POST /transfers/wire",
                "governor_status": "BLOCKED",
                "error_code": 403,
                "violation_reason": e.detail
            }
            
    # Default Fallback
    reply_msg = f"Hello {cust_name}! I am your Apex Bank Virtual Assistant ({agent_id}). I can help you check your account balance, view your Fixed Deposits, or answer banking questions."
    save_conversation(
        account_id=acc_id,
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
    Zero-Trust Authenticated Session Endpoint.
    Validates username and password strictly against database salted PBKDF2 hash.
    Mints HMAC-SHA256 signed JWT with Fernet-encrypted claims.
    """
    u = req.username.strip().lower()
    p = req.password.strip()

    if not u or not p:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    # 1. Direct database lookup and salted hash verification
    user_record = verify_user_credentials(u, p)
    if not user_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password. Access denied by Zero-Trust Authenticator."
        )

    # 2. Mint HMAC-SHA256 JWT with encrypted claims
    role = user_record["role"]
    account_id = user_record.get("account_id")
    token = NHITokenManager.mint_user_token(
        username=user_record["username"],
        role=role,
        account_id=account_id,
        extra_claims={
            "name": user_record["name"],
            "tier": user_record.get("tier"),
            "clearance": user_record.get("clearance")
        }
    )

    # 3. Construct user session profile
    user_data = {
        "role": role,
        "username": user_record["username"],
        "name": user_record["name"],
        "token": token
    }
    if role == "admin":
        user_data.update({
            "badgeId": user_record.get("badge_id") or "SOC-ANALYST-PES-4091",
            "clearance": user_record.get("clearance") or "Tier-4 SecOps Lead",
            "badge": user_record.get("badge") or "FFIEC Cat-3 Compliance Officer",
        })
    else:
        user_data.update({
            "accountId": account_id or "401",
            "tier": user_record.get("tier") or "GOLD",
            "badge": user_record.get("badge") or f"{user_record.get('tier', 'Gold')} Tier Banking",
        })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "user": user_data
    }

@app.post("/api/v1/auth/token")
def oauth2_token_endpoint(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 Compliant Password Bearer Token Endpoint.
    Validates form credentials against PostgreSQL/SQLite and returns standard Bearer token.
    """
    user_record = verify_user_credentials(form_data.username.strip().lower(), form_data.password.strip())
    if not user_record:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    token = NHITokenManager.mint_user_token(
        username=user_record["username"],
        role=user_record["role"],
        account_id=user_record.get("account_id")
    )
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/v1/auth/me")
def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns current authenticated session user profile validated from JWT Bearer token and DB.
    """
    return {
        "status": "AUTHENTICATED",
        "user": {
            "username": user["username"],
            "role": user["role"],
            "name": user["name"],
            "account_id": user.get("account_id"),
            "tier": user.get("tier"),
            "clearance": user.get("clearance"),
            "badge_id": user.get("badge_id"),
            "badge": user.get("badge")
        }
    }

class CryptoEncryptRequest(BaseModel):
    data: Any

class CryptoDecryptRequest(BaseModel):
    ciphertext: Optional[str] = None
    data: Optional[str] = None

@app.post("/api/v1/crypto/encrypt")
def encrypt_payload_endpoint(req: CryptoEncryptRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """Cryptographic API: Encrypts sensitive payload using AES-Fernet cipher."""
    plaintext = req.data if isinstance(req.data, str) else json.dumps(req.data)
    return {"ciphertext": encrypt_data(plaintext)}

@app.post("/api/v1/crypto/decrypt")
def decrypt_payload_endpoint(req: CryptoDecryptRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """Cryptographic API: Decrypts AES-Fernet ciphertext back to plaintext."""
    cipher_input = req.ciphertext or req.data
    if not cipher_input:
        raise HTTPException(status_code=400, detail="Ciphertext is required for decryption.")
    try:
        plaintext = decrypt_data(cipher_input)
        try:
            parsed = json.loads(plaintext)
            return {"plaintext": parsed}
        except Exception:
            return {"plaintext": plaintext}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Decryption failed. Invalid ciphertext or tampered HMAC.")

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

        from backend.core.database import (
            reset_seeded_users,
            reset_seeded_accounts,
            reset_seeded_deposits,
            reset_seeded_transactions,
            reset_seeded_policies
        )
        reset_seeded_users()
        reset_seeded_accounts()
        reset_seeded_deposits()
        reset_seeded_transactions()
        reset_seeded_policies()
        policy_engine.reload_cache()

        from backend.core.killswitch import KillSwitch
        KillSwitch.clear_all()

        from backend.ml.kafka_consumer import governance_consumer
        if governance_consumer:
            governance_consumer.reset_metrics()

        return {
            "status": "RESET_SUCCESS",
            "message": "All system parameters, accounts, deposits, transaction ledger, killswitch quarantines, and ML metrics successfully reset to fresh baseline."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset system: {e}")
