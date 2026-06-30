"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("icon_slug", sa.String(), nullable=True),
        sa.Column("icon_url", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_brands_name"), "brands", ["name"], unique=True)
    op.create_index(op.f("ix_brands_slug"), "brands", ["slug"], unique=True)

    op.create_table(
        "providers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("default_base_url", sa.String(), nullable=True),
        sa.Column("icon_slug", sa.String(), nullable=True),
        sa.Column("icon_url", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_providers_name"), "providers", ["name"], unique=True)
    op.create_index(op.f("ix_providers_slug"), "providers", ["slug"], unique=True)

    op.create_table(
        "public_models",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("pricing", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_public_models_slug"), "public_models", ["slug"], unique=True)

    op.create_table(
        "recharge_codes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("amount_credits", sa.Numeric(20, 6), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("used_by_user_id", sa.String(), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recharge_codes_code_hash"), "recharge_codes", ["code_hash"], unique=True)

    op.create_table(
        "stripe_events",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("basalt_user_id", sa.String(), nullable=True),
        sa.Column("basalt_tenant_id", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_basalt_tenant_id"), "users", ["basalt_tenant_id"], unique=False)
    op.create_index(op.f("ix_users_basalt_user_id"), "users", ["basalt_user_id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("entry_type", sa.String(), nullable=False),
        sa.Column("amount_credits", sa.Numeric(20, 6), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("ref_type", sa.String(), nullable=False),
        sa.Column("ref_id", sa.String(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ref_type", "ref_id", "entry_type", name="uq_ledger_ref"),
    )
    op.create_index(op.f("ix_ledger_entries_user_id"), "ledger_entries", ["user_id"], unique=False)

    op.create_table(
        "models",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("brand_id", sa.String(), nullable=True),
        sa.Column("icon_slug", sa.String(), nullable=True),
        sa.Column("icon_url", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("multiplier", sa.Numeric(20, 6), nullable=False),
        sa.Column("pricing", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_models_brand_id"), "models", ["brand_id"], unique=False)
    op.create_index(op.f("ix_models_name"), "models", ["name"], unique=True)

    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("secret_encrypted", sa.String(), nullable=True),
        sa.Column("secret_last4", sa.String(), nullable=True),
        sa.Column("secret_ref", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("health_state", sa.String(), nullable=False),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "name", name="uq_provider_credential_name"),
    )
    op.create_index(op.f("ix_provider_credentials_provider_id"), "provider_credentials", ["provider_id"], unique=False)

    op.create_table(
        "provider_endpoints",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("endpoint_type", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("health_state", sa.String(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "name", name="uq_provider_endpoint_name"),
    )
    op.create_index(op.f("ix_provider_endpoints_provider_id"), "provider_endpoints", ["provider_id"], unique=False)

    op.create_table(
        "provider_keys",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("key_name", sa.String(), nullable=False),
        sa.Column("secret_encrypted", sa.String(), nullable=True),
        sa.Column("secret_last4", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("health_state", sa.String(), nullable=False),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_keys_provider_id"), "provider_keys", ["provider_id"], unique=False)

    op.create_table(
        "upstream_models",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("upstream_name", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "upstream_name", name="uq_upstream_model_provider_name"),
    )
    op.create_index(op.f("ix_upstream_models_provider_id"), "upstream_models", ["provider_id"], unique=False)
    op.create_index(op.f("ix_upstream_models_upstream_name"), "upstream_models", ["upstream_name"], unique=False)

    op.create_table(
        "wallets",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("balance_credits", sa.Numeric(20, 6), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "api_tokens",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_tokens_token_hash"), "api_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_api_tokens_user_id"), "api_tokens", ["user_id"], unique=False)

    op.create_table(
        "model_provider_keys",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("provider_key_id", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("quota_unit", sa.String(), nullable=False),
        sa.Column("quota_rules", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
        sa.ForeignKeyConstraint(["provider_key_id"], ["provider_keys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_model_provider_keys_model_id"), "model_provider_keys", ["model_id"], unique=False)
    op.create_index(op.f("ix_model_provider_keys_provider_key_id"), "model_provider_keys", ["provider_key_id"], unique=False)

    op.create_table(
        "model_routes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("public_model_id", sa.String(), nullable=False),
        sa.Column("upstream_model_id", sa.String(), nullable=False),
        sa.Column("provider_credential_id", sa.String(), nullable=True),
        sa.Column("provider_endpoint_id", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("quota_unit", sa.String(), nullable=False),
        sa.Column("quota_rules", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_credential_id"], ["provider_credentials.id"]),
        sa.ForeignKeyConstraint(["provider_endpoint_id"], ["provider_endpoints.id"]),
        sa.ForeignKeyConstraint(["public_model_id"], ["public_models.id"]),
        sa.ForeignKeyConstraint(["upstream_model_id"], ["upstream_models.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_model_id", "upstream_model_id", "provider_credential_id", name="uq_model_route_target"),
    )
    op.create_index(op.f("ix_model_routes_provider_credential_id"), "model_routes", ["provider_credential_id"], unique=False)
    op.create_index(op.f("ix_model_routes_provider_endpoint_id"), "model_routes", ["provider_endpoint_id"], unique=False)
    op.create_index(op.f("ix_model_routes_public_model_id"), "model_routes", ["public_model_id"], unique=False)
    op.create_index(op.f("ix_model_routes_upstream_model_id"), "model_routes", ["upstream_model_id"], unique=False)

    op.create_table(
        "usage_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("estimated_cost_credits", sa.Numeric(20, 6), nullable=False),
        sa.Column("final_cost_credits", sa.Numeric(20, 6), nullable=True),
        sa.Column("upstream_provider", sa.String(), nullable=True),
        sa.Column("upstream_key_id", sa.String(), nullable=True),
        sa.Column("request_messages", sa.JSON(), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("usage", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_sessions_model_id"), "usage_sessions", ["model_id"], unique=False)
    op.create_index(op.f("ix_usage_sessions_request_id"), "usage_sessions", ["request_id"], unique=True)
    op.create_index(op.f("ix_usage_sessions_token_id"), "usage_sessions", ["token_id"], unique=False)
    op.create_index(op.f("ix_usage_sessions_user_id"), "usage_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_sessions_user_id"), table_name="usage_sessions")
    op.drop_index(op.f("ix_usage_sessions_token_id"), table_name="usage_sessions")
    op.drop_index(op.f("ix_usage_sessions_request_id"), table_name="usage_sessions")
    op.drop_index(op.f("ix_usage_sessions_model_id"), table_name="usage_sessions")
    op.drop_table("usage_sessions")
    op.drop_index(op.f("ix_model_routes_upstream_model_id"), table_name="model_routes")
    op.drop_index(op.f("ix_model_routes_public_model_id"), table_name="model_routes")
    op.drop_index(op.f("ix_model_routes_provider_endpoint_id"), table_name="model_routes")
    op.drop_index(op.f("ix_model_routes_provider_credential_id"), table_name="model_routes")
    op.drop_table("model_routes")
    op.drop_index(op.f("ix_model_provider_keys_provider_key_id"), table_name="model_provider_keys")
    op.drop_index(op.f("ix_model_provider_keys_model_id"), table_name="model_provider_keys")
    op.drop_table("model_provider_keys")
    op.drop_index(op.f("ix_api_tokens_user_id"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_token_hash"), table_name="api_tokens")
    op.drop_table("api_tokens")
    op.drop_table("wallets")
    op.drop_index(op.f("ix_upstream_models_upstream_name"), table_name="upstream_models")
    op.drop_index(op.f("ix_upstream_models_provider_id"), table_name="upstream_models")
    op.drop_table("upstream_models")
    op.drop_index(op.f("ix_provider_keys_provider_id"), table_name="provider_keys")
    op.drop_table("provider_keys")
    op.drop_index(op.f("ix_provider_endpoints_provider_id"), table_name="provider_endpoints")
    op.drop_table("provider_endpoints")
    op.drop_index(op.f("ix_provider_credentials_provider_id"), table_name="provider_credentials")
    op.drop_table("provider_credentials")
    op.drop_index(op.f("ix_models_name"), table_name="models")
    op.drop_index(op.f("ix_models_brand_id"), table_name="models")
    op.drop_table("models")
    op.drop_index(op.f("ix_ledger_entries_user_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_basalt_user_id"), table_name="users")
    op.drop_index(op.f("ix_users_basalt_tenant_id"), table_name="users")
    op.drop_table("users")
    op.drop_table("stripe_events")
    op.drop_index(op.f("ix_recharge_codes_code_hash"), table_name="recharge_codes")
    op.drop_table("recharge_codes")
    op.drop_index(op.f("ix_public_models_slug"), table_name="public_models")
    op.drop_table("public_models")
    op.drop_index(op.f("ix_providers_slug"), table_name="providers")
    op.drop_index(op.f("ix_providers_name"), table_name="providers")
    op.drop_table("providers")
    op.drop_index(op.f("ix_brands_slug"), table_name="brands")
    op.drop_index(op.f("ix_brands_name"), table_name="brands")
    op.drop_table("brands")
