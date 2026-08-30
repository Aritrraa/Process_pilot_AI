import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Derive a valid 32-byte url-safe base64 Fernet key from the app's SECRET_KEY
_key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
_fernet = Fernet(base64.urlsafe_b64encode(_key_bytes))

def encrypt_key(plain_text: str) -> str:
    """Encrypts an API key for storage in the database."""
    if not plain_text:
        return plain_text
    try:
        return _fernet.encrypt(plain_text.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return plain_text

def decrypt_key(cipher_text: str) -> str:
    """Decrypts an API key. Falls back to returning the plaintext if decryption fails (for legacy keys)."""
    if not cipher_text:
        return cipher_text
    try:
        return _fernet.decrypt(cipher_text.encode()).decode()
    except Exception:
        # If decryption fails, assume it's a legacy plaintext key
        return cipher_text
