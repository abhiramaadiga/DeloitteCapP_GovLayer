"""
backend/core/config.py
Central configuration management for the Agentic-AI Governor.
"""
import os
from pydantic import BaseModel

# Automatically discover and load .env from project root or current directory
_env_path = os.getenv("ENV_FILE") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
)
if os.path.exists(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except Exception:
        # Fallback parser if python-dotenv is not installed
        with open(_env_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    _v = _v.strip().strip("'\"")
                    os.environ.setdefault(_k.strip(), _v)

class Settings(BaseModel):
    # App Information
    APP_NAME: str = os.getenv("APP_NAME", "Agentic-AI Identity & Access Governor")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DOMAIN: str = os.getenv("DOMAIN", "BFSI Retail Banking")
    GATEWAY_PORT: int = int(os.getenv("GATEWAY_PORT", "8000"))
    
    # Security & Cryptography
    # In production, this is loaded from AWS Secrets Manager or HashiCorp Vault
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "deloitte-capstone-2026-secret-key-pes-university")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    TOKEN_EXPIRY_SECONDS: int = int(os.getenv("TOKEN_EXPIRY_SECONDS", "3600"))
    
    # Latency & SLA Targets (Deloitte Rubric)
    MAX_PEP_LATENCY_MS: float = float(os.getenv("MAX_PEP_LATENCY_MS", "5.0"))
    MAX_KILLSWITCH_MTTR_MS: float = float(os.getenv("MAX_KILLSWITCH_MTTR_MS", "200.0"))
    
    # Risk Engine Thresholds
    QUARANTINE_RISK_THRESHOLD: float = float(os.getenv("QUARANTINE_RISK_THRESHOLD", "0.75"))
    
    # Redis Cache Settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PREFIX: str = os.getenv("REDIS_PREFIX", "agentic_iam:")

    # PostgreSQL Database Settings
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "governor_admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "deloitte_secure_pass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "governance_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://governor_admin:deloitte_secure_pass@localhost:5432/governance_db"
    )

    # Kafka Telemetry & Alerts Event Bus Settings
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_TELEMETRY: str = os.getenv("KAFKA_TOPIC_TELEMETRY", "agentic-iam.telemetry")
    KAFKA_TOPIC_ALERTS: str = os.getenv("KAFKA_TOPIC_ALERTS", "agentic-iam.alerts")
    KAFKA_GROUP_ID: str = os.getenv("KAFKA_GROUP_ID", "agentic-iam-ml-risk-engine")

settings = Settings()