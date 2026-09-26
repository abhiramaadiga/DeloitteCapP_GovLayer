"""
backend/core/auth.py
Zero-Trust HMAC-SHA256 Non-Human Identity (NHI) & Authenticated OAuth2/JWT Session Manager.
Includes PBKDF2-HMAC salted password hashing and AES-Fernet cryptographic payload encryption/decryption.
"""
import hmac
import hashlib
import base64
import json
import time
import secrets
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from fastapi import Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from backend.core.config import settings
from backend.core.crypto import _FERNET_KEY, _CIPHER, encrypt_data, decrypt_data

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Computes a secure PBKDF2-HMAC-SHA256 salted password hash with 100,000 iterations.
    Returns (hex_hash, salt).
    """
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    )
    return dk.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Constant-time comparison verifying plaintext password against stored PBKDF2 salt and hash.
    """
    if not password or not password_hash or not salt:
        return False
    calculated_hash, _ = hash_password(password, salt=salt)
    return hmac.compare_digest(calculated_hash, password_hash)


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


class NHITokenManager:
    """Mints and validates Agent Passports and User JWTs with encrypted claims."""

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
        account_id: Optional[str] = None,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Mints signed JWT for human/client session authentication with Fernet-encrypted claims payload.
        """
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())

        # Sensitive claims that are encrypted inside the token
        sensitive_claims = {
            "sub": username,
            "username": username,
            "role": role,
            "account_id": account_id,
            "issued_at": now,
            **(extra_claims or {})
        }
        enc_claims = encrypt_data(json.dumps(sensitive_claims))

        payload = {
            "sub": username,
            "username": username,
            "role": role,
            "account_id": account_id,
            "enc_claims": enc_claims,
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
        """
        Verifies HMAC signature, expiration, and decrypts embedded Fernet claims on client session tokens.
        """
        payload = NHITokenManager.verify_agent_token(token)
        if not payload:
            return None

        # Verify and unpack encrypted claims if present
        enc_claims = payload.get("enc_claims")
        if enc_claims:
            try:
                decrypted_str = decrypt_data(enc_claims)
                decrypted_claims = json.loads(decrypted_str)
                # Confirm decrypted subject matches unencrypted subject
                if decrypted_claims.get("sub") != payload.get("sub"):
                    return None
                payload["decrypted_claims"] = decrypted_claims
            except Exception:
                return None

        return payload


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    FastAPI dependency for authenticating JWT session tokens.
    Verifies token signature, decrypts claims, and verifies existence against database.
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing Bearer authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    claims = NHITokenManager.verify_user_token(token)
    if not claims:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    username = claims.get("username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Malformed session claims.")

    # Lazy-import to prevent circular imports
    from backend.core.database import get_user_by_username
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Authenticated user no longer exists in database.")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User account is deactivated.")

    return user


# Module-level aliases
mint_user_token = NHITokenManager.mint_user_token
verify_user_token = NHITokenManager.verify_user_token
mint_agent_token = NHITokenManager.mint_agent_token
verify_agent_token = NHITokenManager.verify_agent_token