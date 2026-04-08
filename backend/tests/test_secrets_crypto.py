import base64
import hashlib
import hmac
import secrets

import pytest

from app.core.secrets import decrypt_secret, encrypt_secret


def _legacy_keystream(root_key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: list[bytes] = []
    counter = 0
    while len(b"".join(blocks)) < length:
        counter_bytes = counter.to_bytes(4, "big")
        blocks.append(hmac.new(root_key, nonce + counter_bytes, hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def _legacy_encrypt(value: str) -> str:
    plaintext = value.encode("utf-8")
    root_key = hashlib.sha256(b"dev-secret:dev-token-salt").digest()
    nonce = secrets.token_bytes(16)
    stream = _legacy_keystream(root_key, nonce, len(plaintext))
    ciphertext = bytes(left ^ right for left, right in zip(plaintext, stream))
    tag = hmac.new(root_key, b"tag" + nonce + ciphertext, hashlib.sha256).digest()
    packed = b"v1:" + nonce + ciphertext + tag
    return base64.urlsafe_b64encode(packed).decode("ascii")


def test_encrypt_decrypt_roundtrip_uses_v2():
    token = encrypt_secret("sk-test")
    assert token.startswith("v2:")
    assert decrypt_secret(token) == "sk-test"


def test_decrypt_legacy_v1_token_is_still_supported():
    legacy = _legacy_encrypt("legacy-key")
    assert decrypt_secret(legacy) == "legacy-key"


def test_decrypt_tampered_v2_token_raises():
    token = encrypt_secret("sk-test")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ValueError):
        decrypt_secret(tampered)
