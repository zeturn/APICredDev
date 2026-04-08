import base64
import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


LEGACY_PREFIX = b"v1:"
CURRENT_PREFIX = "v2:"


def _root_key() -> bytes:
    material = f"{settings.app_secret}:{settings.token_salt}".encode("utf-8")
    return hashlib.sha256(material).digest()


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(_root_key())
    return Fernet(key)


def _keystream(root_key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: list[bytes] = []
    counter = 0
    while len(b"".join(blocks)) < length:
        counter_bytes = counter.to_bytes(4, "big")
        blocks.append(hmac.new(root_key, nonce + counter_bytes, hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def encrypt_secret(value: str) -> str:
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{CURRENT_PREFIX}{token}"


def _decrypt_legacy_v1(token: str) -> str:
    packed = base64.urlsafe_b64decode(token.encode("ascii"))
    if not packed.startswith(LEGACY_PREFIX):
        raise ValueError("unsupported_secret_version")
    payload = packed[len(LEGACY_PREFIX):]
    nonce = payload[:16]
    tag = payload[-32:]
    ciphertext = payload[16:-32]
    root_key = _root_key()
    expected_tag = hmac.new(root_key, b"tag" + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("secret_integrity_check_failed")
    stream = _keystream(root_key, nonce, len(ciphertext))
    plaintext = bytes(left ^ right for left, right in zip(ciphertext, stream))
    return plaintext.decode("utf-8")


def decrypt_secret(token: str | None) -> str:
    if not token:
        return ""
    if token.startswith(CURRENT_PREFIX):
        fernet_token = token[len(CURRENT_PREFIX):]
        try:
            return _fernet().decrypt(fernet_token.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("secret_integrity_check_failed") from exc
    return _decrypt_legacy_v1(token)
