import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def _master_key() -> bytes:
    return hashlib.sha256(settings.MASTER_KEY.encode("utf-8")).digest()


def generate_file_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def encrypt_bytes(plain_bytes: bytes, file_key: bytes) -> tuple[bytes, str, str]:
    nonce = os.urandom(12)
    encrypted = AESGCM(file_key).encrypt(nonce, plain_bytes, None)
    return encrypted[:-16], _b64encode(nonce), _b64encode(encrypted[-16:])


def decrypt_bytes(ciphertext: bytes, file_key: bytes, nonce: str, auth_tag: str) -> bytes:
    encrypted = ciphertext + _b64decode(auth_tag)
    return AESGCM(file_key).decrypt(_b64decode(nonce), encrypted, None)


def wrap_file_key(file_key: bytes) -> str:
    nonce = os.urandom(12)
    wrapped = AESGCM(_master_key()).encrypt(nonce, file_key, None)
    return _b64encode(nonce + wrapped)


def unwrap_file_key(encrypted_file_key: str) -> bytes:
    payload = _b64decode(encrypted_file_key)
    nonce = payload[:12]
    wrapped = payload[12:]
    return AESGCM(_master_key()).decrypt(nonce, wrapped, None)
