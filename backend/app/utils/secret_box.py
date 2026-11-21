import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

V2_PREFIX = "v2:"
LEGACY_FORMAT_MSG = "旧版加密格式已下线，请在后台重新保存该配置项"


def _derive_key() -> bytes:
    raw = (settings.ENCRYPTION_KEY or settings.SECRET_KEY).encode("utf-8")
    return hashlib.sha256(raw).digest()


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    key = _derive_key()
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plain.encode("utf-8"), None)
    blob = nonce + ciphertext
    return V2_PREFIX + base64.urlsafe_b64encode(blob).decode("ascii")


def decrypt_secret(enc: str) -> str:
    if not enc:
        return ""
    if not enc.startswith(V2_PREFIX):
        raise ValueError(LEGACY_FORMAT_MSG)
    blob = base64.urlsafe_b64decode(enc[len(V2_PREFIX) :].encode("ascii"))
    nonce, ciphertext = blob[:12], blob[12:]
    plain = AESGCM(_derive_key()).decrypt(nonce, ciphertext, None)
    return plain.decode("utf-8")


def mask_secret(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return value[:visible] + "*" * (len(value) - visible * 2) + value[-visible:]
