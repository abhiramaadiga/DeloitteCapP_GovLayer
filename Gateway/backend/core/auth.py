"""
backend/core/auth.py
Zero-dependency HMAC-SHA256 Non-Human Identity (NHI) Passport Manager.
"""
import hmac
import hashlib
import base64
import json
import time
from typing import Dict, Any, Optional
from backend.core.config import settings

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))

class NHITokenManager:
    """Mints and validates Agent Passports for autonomous identities."""
    
    @staticmethod
    def mint_agent_token(
        agent_id: str,
        role: str,
        max_transaction_amount: float = 0.0,
        risk_tier: str = "TIER_1_LOW"
    ) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        payload = {
            "sub": agent_id,
            "agent_id": agent_id,
            "role": role,
            "max_transaction_amount": max_transaction_amount,
            "risk_tier": risk_tier,
            "iat": now,
            "exp": now + settings.TOKEN_EXPIRY_SECONDS,
            "iss": "Agentic-IAM-Governor-PES"
        }
        
        header_b64 = _b64_encode(json.dumps(header).encode("utf-8"))
        payload_b64 = _b64_encode(json.dumps(payload).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        
        signature = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()
        
        signature_b64 = _b64_encode(signature)
        return f"{header_b64}.{payload_b64}.{signature_b64}"

    @staticmethod
    def verify_agent_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, sig_b64 = parts
            signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
            
            expected_sig = hmac.new(
                settings.JWT_SECRET_KEY.encode("utf-8"),
                signing_input,
                hashlib.sha256
            ).digest()
            
            actual_sig = _b64_decode(sig_b64)
            if not hmac.compare_digest(expected_sig, actual_sig):
                return None  # Signature mismatch (Tampering detected!)
                
            payload = json.loads(_b64_decode(payload_b64).decode("utf-8"))
            
            # Check expiration
            if time.time() > payload.get("exp", 0):
                return None
                
            return payload
        except Exception:
            return None

    @staticmethod
    def mint_user_token(
        username: str,
        role: str,
        account_id: Optional[str] = None
    ) -> str:
        """Mints signed JWT for human/client session authentication."""
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        payload = {
            "sub": username,
            "username": username,
            "role": role,
            "account_id": account_id,
            "iat": now,
            "exp": now + settings.TOKEN_EXPIRY_SECONDS,
            "iss": "Apex-ZeroTrust-AuthGate"
        }
        header_b64 = _b64_encode(json.dumps(header).encode("utf-8"))
        payload_b64 = _b64_encode(json.dumps(payload).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()
        return f"{header_b64}.{payload_b64}.{_b64_encode(signature)}"

    @staticmethod
    def verify_user_token(token: str) -> Optional[Dict[str, Any]]:
        """Verifies HMAC signature and expiration on client session tokens."""
        return NHITokenManager.verify_agent_token(token)