"""drop provider default_base_url

Revision ID: 0002_drop_provider_url
Revises: 0001_initial_schema
Create Date: 2026-07-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_drop_provider_url"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("providers")}
    if "default_base_url" in columns:
        op.drop_column("providers", "default_base_url")


def downgrade() -> None:
    op.add_column("providers", sa.Column("default_base_url", sa.String(), nullable=True))
