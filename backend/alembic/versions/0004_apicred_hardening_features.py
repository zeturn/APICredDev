"""apicred hardening features

Revision ID: 0004_apicred_hardening_features
Revises: 0003_audit_llm_messages
Create Date: 2026-07-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_apicred_hardening_features"
down_revision: str | None = "0003_audit_llm_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    op.create_table(
        "quota_ledger_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("usage_session_id", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_id", sa.String(), nullable=False),
        sa.Column("public_model_id", sa.String(), nullable=False),
        sa.Column("public_model_name", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("upstream_model", sa.String(), nullable=True),
        sa.Column("provider_credential_id", sa.String(), nullable=True),
        sa.Column("quota_unit", sa.String(), nullable=False),
        sa.Column("reserved_delta", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_credits", sa.Numeric(20, 6), nullable=False),
        sa.Column("final_cost_credits", sa.Numeric(20, 6), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quota_ledger_entries_created_at"), "quota_ledger_entries", ["created_at"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_provider"), "quota_ledger_entries", ["provider"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_provider_credential_id"), "quota_ledger_entries", ["provider_credential_id"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_public_model_id"), "quota_ledger_entries", ["public_model_id"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_public_model_name"), "quota_ledger_entries", ["public_model_name"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_request_id"), "quota_ledger_entries", ["request_id"], unique=True)
    op.create_index(op.f("ix_quota_ledger_entries_settled_at"), "quota_ledger_entries", ["settled_at"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_status"), "quota_ledger_entries", ["status"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_token_id"), "quota_ledger_entries", ["token_id"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_upstream_model"), "quota_ledger_entries", ["upstream_model"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_usage_session_id"), "quota_ledger_entries", ["usage_session_id"], unique=False)
    op.create_index(op.f("ix_quota_ledger_entries_user_id"), "quota_ledger_entries", ["user_id"], unique=False)

    op.add_column("provider_credentials", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("provider_credentials", sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("provider_credentials", sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("provider_credentials", sa.Column("last_error_code", sa.String(), nullable=True))
    op.add_column("provider_credentials", sa.Column("last_error_message", sa.String(), nullable=True))
    op.add_column("provider_credentials", sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"))
    if not is_sqlite:
        op.alter_column("provider_credentials", "consecutive_failures", server_default=None)

    op.add_column("audit_llm_messages", sa.Column("content_hash", sa.String(), nullable=True))
    op.add_column("audit_llm_messages", sa.Column("content_preview", sa.String(), nullable=True))
    op.add_column("audit_llm_messages", sa.Column("redaction_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("audit_llm_messages", sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True))
    if not is_sqlite:
        op.alter_column("audit_llm_messages", "redaction_applied", server_default=None)
    op.create_index(op.f("ix_audit_llm_messages_content_hash"), "audit_llm_messages", ["content_hash"], unique=False)
    op.create_index(op.f("ix_audit_llm_messages_retention_expires_at"), "audit_llm_messages", ["retention_expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_llm_messages_retention_expires_at"), table_name="audit_llm_messages")
    op.drop_index(op.f("ix_audit_llm_messages_content_hash"), table_name="audit_llm_messages")
    op.drop_column("audit_llm_messages", "retention_expires_at")
    op.drop_column("audit_llm_messages", "redaction_applied")
    op.drop_column("audit_llm_messages", "content_preview")
    op.drop_column("audit_llm_messages", "content_hash")

    op.drop_column("provider_credentials", "consecutive_failures")
    op.drop_column("provider_credentials", "last_error_message")
    op.drop_column("provider_credentials", "last_error_code")
    op.drop_column("provider_credentials", "last_failure_at")
    op.drop_column("provider_credentials", "last_success_at")
    op.drop_column("provider_credentials", "last_checked_at")

    op.drop_index(op.f("ix_quota_ledger_entries_user_id"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_usage_session_id"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_upstream_model"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_token_id"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_status"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_settled_at"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_request_id"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_public_model_name"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_public_model_id"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_provider_credential_id"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_provider"), table_name="quota_ledger_entries")
    op.drop_index(op.f("ix_quota_ledger_entries_created_at"), table_name="quota_ledger_entries")
    op.drop_table("quota_ledger_entries")
