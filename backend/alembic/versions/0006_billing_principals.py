"""Add explicit billing principals for user and app usage.

Revision ID: 0006_billing_principals
Revises: 0005_ops_policy_obs
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_billing_principals"
down_revision = "0005_ops_policy_obs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usage_sessions", sa.Column("principal_type", sa.String(), server_default="user", nullable=False))
    op.add_column("usage_sessions", sa.Column("principal_id", sa.String(), nullable=True))
    op.add_column("usage_sessions", sa.Column("tenant_id", sa.String(), nullable=True))
    op.add_column("usage_sessions", sa.Column("app_id", sa.String(), nullable=True))
    op.execute("UPDATE usage_sessions SET principal_id = user_id WHERE principal_id IS NULL")
    op.create_index(op.f("ix_usage_sessions_principal_type"), "usage_sessions", ["principal_type"], unique=False)
    op.create_index(op.f("ix_usage_sessions_principal_id"), "usage_sessions", ["principal_id"], unique=False)
    op.create_index(op.f("ix_usage_sessions_tenant_id"), "usage_sessions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_usage_sessions_app_id"), "usage_sessions", ["app_id"], unique=False)

    op.add_column("ledger_entries", sa.Column("principal_type", sa.String(), server_default="user", nullable=False))
    op.add_column("ledger_entries", sa.Column("principal_id", sa.String(), nullable=True))
    op.add_column("ledger_entries", sa.Column("tenant_id", sa.String(), nullable=True))
    op.execute("UPDATE ledger_entries SET principal_id = user_id WHERE principal_id IS NULL")
    op.create_index(op.f("ix_ledger_entries_principal_type"), "ledger_entries", ["principal_type"], unique=False)
    op.create_index(op.f("ix_ledger_entries_principal_id"), "ledger_entries", ["principal_id"], unique=False)
    op.create_index(op.f("ix_ledger_entries_tenant_id"), "ledger_entries", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ledger_entries_tenant_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_principal_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_principal_type"), table_name="ledger_entries")
    op.drop_column("ledger_entries", "tenant_id")
    op.drop_column("ledger_entries", "principal_id")
    op.drop_column("ledger_entries", "principal_type")

    op.drop_index(op.f("ix_usage_sessions_app_id"), table_name="usage_sessions")
    op.drop_index(op.f("ix_usage_sessions_tenant_id"), table_name="usage_sessions")
    op.drop_index(op.f("ix_usage_sessions_principal_id"), table_name="usage_sessions")
    op.drop_index(op.f("ix_usage_sessions_principal_type"), table_name="usage_sessions")
    op.drop_column("usage_sessions", "app_id")
    op.drop_column("usage_sessions", "tenant_id")
    op.drop_column("usage_sessions", "principal_id")
    op.drop_column("usage_sessions", "principal_type")
