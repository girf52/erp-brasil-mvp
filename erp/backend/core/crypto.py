"""Fernet encryption for sensitive fields (CPF/CNPJ)."""
from cryptography.fernet import Fernet
from core.config import settings

# Auto-generate key if not configured (dev only)
_key = settings.FERNET_KEY or Fernet.generate_key().decode()
_fernet = Fernet(_key.encode() if isinstance(_key, str) else _key)


def encrypt(value: str) -> str:
    """Encrypt a string value, return base64 token."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet token back to plaintext."""
    return _fernet.decrypt(token.encode()).decode()
