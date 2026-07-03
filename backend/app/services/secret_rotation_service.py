from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.secrets import decrypt_secret, encrypt_secret, secret_version
from app.db.models.provider_credential import ProviderCredential


def _target_version() -> str:
    version = str(settings.apicred_encryption_key_id or "").strip().lower()
    return version or "v3"


async def rotate_provider_credentials(db: AsyncSession, *, dry_run: bool) -> dict[str, Any]:
    rows = list((await db.execute(select(ProviderCredential).order_by(ProviderCredential.created_at.asc()))).scalars().all())
    report: list[dict[str, Any]] = []
    changed = 0
    failed = 0
    for credential in rows:
        encrypted = credential.secret_encrypted or ""
        if not encrypted:
            report.append(
                {
                    "credential_id": credential.id,
                    "old_version": "none",
                    "new_version": "none",
                    "status": "skipped_empty",
                }
            )
            continue
        old_version = secret_version(encrypted)
        if old_version == _target_version():
            report.append(
                {
                    "credential_id": credential.id,
                    "old_version": old_version,
                    "new_version": old_version,
                    "status": "noop",
                }
            )
            continue
        try:
            plain = decrypt_secret(encrypted)
            rotated = encrypt_secret(plain)
            new_version = secret_version(rotated)
        except Exception:
            failed += 1
            report.append(
                {
                    "credential_id": credential.id,
                    "old_version": old_version,
                    "new_version": old_version,
                    "status": "failed",
                }
            )
            continue
        if rotated == encrypted:
            report.append(
                {
                    "credential_id": credential.id,
                    "old_version": old_version,
                    "new_version": old_version,
                    "status": "noop",
                }
            )
            continue
        changed += 1
        report.append(
            {
                "credential_id": credential.id,
                "old_version": old_version,
                "new_version": new_version,
                "status": "rotated" if not dry_run else "would_rotate",
            }
        )
        if not dry_run:
            credential.secret_encrypted = rotated
            credential.secret_last4 = plain[-4:] if plain else None
    if not dry_run and changed > 0:
        await db.commit()
    return {"dry_run": dry_run, "total": len(rows), "changed": changed, "failed": failed, "items": report}
