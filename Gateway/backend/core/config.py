"""
backend/core/config.py
Central configuration management for the Agentic-AI Governor.
"""
import os
from pydantic import BaseModel

class Settings(BaseModel):
    # App Information
    APP_NAME: str = "Agentic-AI Identity & Access Governor"
    APP_VERSION: str = "1.0.0"
    DOMAIN: str = "BFSI Retail Banking"
    
    # Security & Cryptography
    # In production, this is loaded from AWS Secrets Manager or HashiCorp Vault
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "deloitte-capstone-2026-secret-key-pes-university")
    JWT_ALGORITHM: str = "HS256"
    TOKEN_EXPIRY_SECONDS: int = 3600  # 1 Hour
    
    # Latency & SLA Targets (Deloitte Rubric)
    MAX_PEP_LATENCY_MS: float = 5.0      # SLA: <5ms inline overhead
    MAX_KILLSWITCH_MTTR_MS: float = 200.0 # SLA: <200ms Mean-Time-To-Remediate
    
    # Risk Engine Thresholds
    QUARANTINE_RISK_THRESHOLD: float = 0.75  # Auto-kill if risk >= 0.75
    
    # Redis Cache Settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PREFIX: str = "agentic_iam:"

settings = Settings()