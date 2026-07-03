from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.provider_credential import ProviderCredential
from app.services.audit_service import purge_expired_audit_messages
from app.services.provider_health_service import health_check_all, health_check_by_id
from app.services.provider_benchmark_service import run_provider_benchmark
from app.services.quota_ledger_service import reconcile_quota_ledger
from app.services.secret_rotation_service import rotate_provider_credentials


async def _run_with_db(coro):
    async with SessionLocal() as db:
        return await coro(db)


async def _cmd_rotate_provider_credentials(args: argparse.Namespace) -> None:
    result = await _run_with_db(lambda db: rotate_provider_credentials(db, dry_run=bool(args.dry_run)))
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _cmd_quota_reconcile(args: argparse.Namespace) -> None:
    result = await _run_with_db(lambda db: reconcile_quota_ledger(db, dry_run=bool(args.dry_run)))
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _cmd_audit_purge(args: argparse.Namespace) -> None:
    result = await _run_with_db(lambda db: purge_expired_audit_messages(db, dry_run=bool(args.dry_run)))
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _cmd_provider_health_check(args: argparse.Namespace) -> None:
    if args.dry_run:
        if args.all:
            rows = await _run_with_db(
                lambda db: db.execute(select(ProviderCredential.id, ProviderCredential.display_name).order_by(ProviderCredential.created_at.asc()))
            )
            items = [{"credential_id": row.id, "credential_name": row.display_name} for row in rows.all()]
            print(json.dumps({"dry_run": True, "all": True, "items": items}, ensure_ascii=False, indent=2))
            return
        print(json.dumps({"dry_run": True, "credential_id": args.credential_id, "provider": args.provider}, ensure_ascii=False, indent=2))
        return
    if args.all:
        result = await _run_with_db(lambda db: health_check_all(db, provider_slug=args.provider))
    else:
        if not args.credential_id:
            raise SystemExit("--credential-id is required unless --all is provided")
        result = await _run_with_db(lambda db: health_check_by_id(db, args.credential_id))
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _cmd_provider_benchmark(args: argparse.Namespace) -> None:
    result = await _run_with_db(
        lambda db: run_provider_benchmark(
            db,
            public_model=args.public_model,
            provider=args.provider,
            runs=max(int(args.runs or 1), 1),
            dry_run=bool(args.dry_run),
            mock_mode=bool(args.mock_mode),
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    secrets = sub.add_parser("secrets")
    secrets_sub = secrets.add_subparsers(dest="secrets_command", required=True)
    rotate = secrets_sub.add_parser("rotate-provider-credentials")
    rotate.add_argument("--dry-run", action="store_true")
    rotate.set_defaults(func=_cmd_rotate_provider_credentials)

    quota = sub.add_parser("quota")
    quota_sub = quota.add_subparsers(dest="quota_command", required=True)
    reconcile = quota_sub.add_parser("reconcile")
    reconcile.add_argument("--dry-run", action="store_true")
    reconcile.set_defaults(func=_cmd_quota_reconcile)

    providers = sub.add_parser("providers")
    providers_sub = providers.add_subparsers(dest="providers_command", required=True)
    health = providers_sub.add_parser("health-check")
    health.add_argument("--provider", default=None)
    health.add_argument("--credential-id", default=None)
    health.add_argument("--all", action="store_true")
    health.add_argument("--dry-run", action="store_true")
    health.set_defaults(func=_cmd_provider_health_check)
    benchmark = providers_sub.add_parser("benchmark")
    benchmark.add_argument("--public-model", default=None)
    benchmark.add_argument("--provider", default=None)
    benchmark.add_argument("--runs", type=int, default=5)
    benchmark.add_argument("--dry-run", action="store_true")
    benchmark.add_argument("--mock-mode", action="store_true")
    benchmark.set_defaults(func=_cmd_provider_benchmark)

    audit = sub.add_parser("audit")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    purge = audit_sub.add_parser("purge-expired")
    purge.add_argument("--dry-run", action="store_true")
    purge.set_defaults(func=_cmd_audit_purge)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
