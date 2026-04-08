from urllib.parse import urlparse


ALLOWED_UPSTREAM_SCHEMES = {"http", "https"}


def normalize_upstream_base_url(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme == "file":
        raise ValueError("file_url_not_allowed")
    if scheme and scheme not in ALLOWED_UPSTREAM_SCHEMES:
        raise ValueError("unsupported_url_scheme")
    if scheme in ALLOWED_UPSTREAM_SCHEMES and not parsed.netloc:
        raise ValueError("invalid_base_url")
    return raw.rstrip("/")
