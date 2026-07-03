import base64
import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


LEGACY_PREFIX = b"v1:"
LEGACY_DERIVED_VERSION = "v2"
DEFAULT_CURRENT_VERSION = "v3"


def _root_key() -> bytes:
    material = f"{settings.app_secret}:{settings.token_salt}".encode("utf-8")
    return hashlib.sha256(material).digest()


def _legacy_fernet() -> Fernet:
    key = base64.urlsafe_b64encode(_root_key())
    return Fernet(key)


def _normalized_version(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    if not value:
        return DEFAULT_CURRENT_VERSION
    if ":" in value:
        value = value.split(":", 1)[0]
    return value


def _decode_explicit_key(raw: str) -> bytes:
    if not raw:
        raise ValueError("missing encryption key")
    try:
        decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
    except Exception as exc:
        raise ValueError("invalid encryption key encoding") from exc
    if len(decoded) != 32:
        raise ValueError("invalid encryption key length")
    return base64.urlsafe_b64encode(decoded)


def _explicit_keyring() -> dict[str, Fernet]:
    keyring: dict[str, Fernet] = {}
    current_key = str(settings.encryption_key or "").strip()
    if current_key:
        keyring[_normalized_version(settings.apicred_encryption_key_id)] = Fernet(_decode_explicit_key(current_key))

    previous = str(settings.apicred_previous_encryption_keys or "").strip()
    if not previous:
        return keyring
    for entry in previous.split(","):
        pair = entry.strip()
        if not pair or ":" not in pair:
            continue
        version_raw, key_raw = pair.split(":", 1)
        version = _normalized_version(version_raw)
        key = key_raw.strip()
        if not key or version in keyring:
            continue
        keyring[version] = Fernet(_decode_explicit_key(key))
    return keyring


def _current_version_and_fernet() -> tuple[str, Fernet]:
    keyring = _explicit_keyring()
    current_version = _normalized_version(settings.apicred_encryption_key_id)
    explicit = keyring.get(current_version)
    if explicit is not None:
        return current_version, explicit
    return LEGACY_DERIVED_VERSION, _legacy_fernet()


def _keystream(root_key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: list[bytes] = []
    counter = 0
    while len(b"".join(blocks)) < length:
        counter_bytes = counter.to_bytes(4, "big")
        blocks.append(hmac.new(root_key, nonce + counter_bytes, hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def encrypt_secret(value: str) -> str:
    version, fernet = _current_version_and_fernet()
    token = fernet.encrypt(value.encode("utf-8")).decode("ascii")
    return f"{version}:{token}"


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
    if ":" in token:
        version, fernet_token = token.split(":", 1)
        normalized_version = _normalized_version(version)
        if normalized_version == LEGACY_DERIVED_VERSION:
            fernet = _explicit_keyring().get(normalized_version) or _legacy_fernet()
        else:
            fernet = _explicit_keyring().get(normalized_version)
            if fernet is None:
                raise ValueError("unsupported_secret_version")
        try:
            return fernet.decrypt(fernet_token.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("secret_integrity_check_failed") from exc
    return _decrypt_legacy_v1(token)


def secret_version(token: str | None) -> str:
    if not token:
        return "unknown"
    if ":" in token:
        return _normalized_version(token.split(":", 1)[0])
    return "v1"
