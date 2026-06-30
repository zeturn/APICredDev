from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


CATALOG_DIR = Path(__file__).resolve().parent


def _load_yaml(name: str) -> dict[str, Any]:
    path = CATALOG_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"catalog file must contain a mapping: {path}")
    return data


@lru_cache(maxsize=1)
def load_default_providers() -> dict[str, Any]:
    return _load_yaml("default_providers.yaml")


@lru_cache(maxsize=1)
def load_default_models() -> dict[str, Any]:
    return _load_yaml("default_models.yaml")


@lru_cache(maxsize=1)
def load_default_routes() -> dict[str, Any]:
    return _load_yaml("default_routes.yaml")
