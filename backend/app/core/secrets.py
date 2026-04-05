import base64
import hashlib
import hmac
import secrets

from app.core.config import settings


def _root_key() -> bytes:
    return hashlib.sha256(settings.app_secret.encode("utf-8")).digest()


def _keystream(root_key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: list[bytes] = []
    counter = 0
    while len(b"".join(blocks)) < length:
        counter_bytes = counter.to_bytes(4, "big")
        blocks.append(hmac.new(root_key, nonce + counter_bytes, hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def encrypt_secret(value: str) -> str:
    plaintext = value.encode("utf-8")
    nonce = secrets.token_bytes(16)
    root_key = _root_key()
    stream = _keystream(root_key, nonce, len(plaintext))
    ciphertext = bytes(left ^ right for left, right in zip(plaintext, stream))
    tag = hmac.new(root_key, b"tag" + nonce + ciphertext, hashlib.sha256).digest()
    packed = b"v1:" + nonce + ciphertext + tag
    return base64.urlsafe_b64encode(packed).decode("ascii")


def decrypt_secret(token: str | None) -> str:
    if not token:
        return ""
    packed = base64.urlsafe_b64decode(token.encode("ascii"))
    if not packed.startswith(b"v1:"):
        raise ValueError("unsupported_secret_version")
    payload = packed[3:]
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
