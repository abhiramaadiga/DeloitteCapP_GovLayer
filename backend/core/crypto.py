"""
backend/core/crypto.py
AES-Fernet Cryptographic Engine for Payload Confidentiality and Integrity.
"""
import base64
import hashlib
import json
from cryptography.fernet import Fernet
from backend.core.config import settings

# Derive deterministic 32-byte Fernet key from the JWT_SECRET_KEY
_FERNET_KEY = base64.urlsafe_b64encode(
    hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
)
_CIPHER = Fernet(_FERNET_KEY)


def encrypt_data(plaintext: str) -> str:
    """Encrypts plaintext string using AES-CBC/HMAC-SHA256 authenticated Fernet cipher."""
    if not isinstance(plaintext, str):
        plaintext = json.dumps(plaintext)
    encrypted_bytes = _CIPHER.encrypt(plaintext.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_data(ciphertext: str) -> str:
    """Decrypts ciphertext back to string using Fernet cipher."""
    decrypted_bytes = _CIPHER.decrypt(ciphertext.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")
