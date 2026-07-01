"""add audit llm messages

Revision ID: 0003_audit_llm_messages
Revises: 0002_drop_provider_default_base_url
Create Date: 2026-07-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_audit_llm_messages"
down_revision: str | None = "0002_drop_provider_default_base_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_llm_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("usage_session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("upstream_provider", sa.String(), nullable=True),
        sa.Column("upstream_credential_id", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("message_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_llm_messages_model_id"), "audit_llm_messages", ["model_id"], unique=False)
    op.create_index(op.f("ix_audit_llm_messages_request_id"), "audit_llm_messages", ["request_id"], unique=False)
    op.create_index(op.f("ix_audit_llm_messages_role"), "audit_llm_messages", ["role"], unique=False)
    op.create_index(op.f("ix_audit_llm_messages_source"), "audit_llm_messages", ["source"], unique=False)
    op.create_index(op.f("ix_audit_llm_messages_usage_session_id"), "audit_llm_messages", ["usage_session_id"], unique=False)
    op.create_index(op.f("ix_audit_llm_messages_user_deleted_at"), "audit_llm_messages", ["user_deleted_at"], unique=False)
    op.create_index(op.f("ix_audit_llm_messages_user_id"), "audit_llm_messages", ["user_id"], unique=False)
    op.create_index(
        "ix_audit_llm_messages_user_session_sequence",
        "audit_llm_messages",
        ["user_id", "usage_session_id", "sequence"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_llm_messages_user_session_sequence", table_name="audit_llm_messages")
    op.drop_index(op.f("ix_audit_llm_messages_user_id"), table_name="audit_llm_messages")
    op.drop_index(op.f("ix_audit_llm_messages_user_deleted_at"), table_name="audit_llm_messages")
    op.drop_index(op.f("ix_audit_llm_messages_usage_session_id"), table_name="audit_llm_messages")
    op.drop_index(op.f("ix_audit_llm_messages_source"), table_name="audit_llm_messages")
    op.drop_index(op.f("ix_audit_llm_messages_role"), table_name="audit_llm_messages")
    op.drop_index(op.f("ix_audit_llm_messages_request_id"), table_name="audit_llm_messages")
    op.drop_index(op.f("ix_audit_llm_messages_model_id"), table_name="audit_llm_messages")
    op.drop_table("audit_llm_messages")
