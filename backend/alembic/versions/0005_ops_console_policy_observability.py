"""ops console policy observability

Revision ID: 0005_ops_console_policy_observability
Revises: 0004_apicred_hardening_features
Create Date: 2026-07-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_ops_console_policy_observability"
down_revision: str | None = "0004_apicred_hardening_features"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "access_policies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("scope_type", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("allowed_public_models_json", sa.JSON(), nullable=False),
        sa.Column("blocked_public_models_json", sa.JSON(), nullable=False),
        sa.Column("allowed_providers_json", sa.JSON(), nullable=False),
        sa.Column("blocked_providers_json", sa.JSON(), nullable=False),
        sa.Column("max_requests_per_minute", sa.Integer(), nullable=True),
        sa.Column("max_requests_per_day", sa.Integer(), nullable=True),
        sa.Column("max_tokens_per_day", sa.Integer(), nullable=True),
        sa.Column("max_cost_credits_per_day", sa.Numeric(20, 6), nullable=True),
        sa.Column("max_cost_credits_per_month", sa.Numeric(20, 6), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_access_policies_enabled"), "access_policies", ["enabled"], unique=False)
    op.create_index(op.f("ix_access_policies_name"), "access_policies", ["name"], unique=False)
    op.create_index(op.f("ix_access_policies_scope_id"), "access_policies", ["scope_id"], unique=False)
    op.create_index(op.f("ix_access_policies_scope_type"), "access_policies", ["scope_type"], unique=False)

    op.create_table(
        "provider_benchmark_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("public_model", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("runs", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.String(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_benchmark_runs_provider"), "provider_benchmark_runs", ["provider"], unique=False)
    op.create_index(op.f("ix_provider_benchmark_runs_public_model"), "provider_benchmark_runs", ["public_model"], unique=False)
    op.create_index(op.f("ix_provider_benchmark_runs_status"), "provider_benchmark_runs", ["status"], unique=False)

    op.create_table(
        "provider_benchmark_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("credential_id", sa.String(), nullable=True),
        sa.Column("upstream_model", sa.String(), nullable=True),
        sa.Column("success_rate", sa.Numeric(10, 4), nullable=False),
        sa.Column("avg_latency_ms", sa.Numeric(20, 6), nullable=True),
        sa.Column("p95_latency_ms", sa.Numeric(20, 6), nullable=True),
        sa.Column("error_rate", sa.Numeric(10, 4), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(20, 6), nullable=False),
        sa.Column("health_state_before", sa.String(), nullable=True),
        sa.Column("health_state_after", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_benchmark_results_credential_id"), "provider_benchmark_results", ["credential_id"], unique=False)
    op.create_index(op.f("ix_provider_benchmark_results_provider"), "provider_benchmark_results", ["provider"], unique=False)
    op.create_index(op.f("ix_provider_benchmark_results_run_id"), "provider_benchmark_results", ["run_id"], unique=False)
    op.create_index(op.f("ix_provider_benchmark_results_upstream_model"), "provider_benchmark_results", ["upstream_model"], unique=False)

    op.add_column("usage_sessions", sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.add_column("usage_sessions", sa.Column("upstream_latency_ms", sa.Integer(), nullable=True))
    op.add_column("usage_sessions", sa.Column("error_code", sa.String(), nullable=True))
    op.add_column("usage_sessions", sa.Column("error_message", sa.Text(), nullable=True))
    op.create_index(op.f("ix_usage_sessions_error_code"), "usage_sessions", ["error_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_sessions_error_code"), table_name="usage_sessions")
    op.drop_column("usage_sessions", "error_message")
    op.drop_column("usage_sessions", "error_code")
    op.drop_column("usage_sessions", "upstream_latency_ms")
    op.drop_column("usage_sessions", "latency_ms")

    op.drop_index(op.f("ix_provider_benchmark_results_upstream_model"), table_name="provider_benchmark_results")
    op.drop_index(op.f("ix_provider_benchmark_results_run_id"), table_name="provider_benchmark_results")
    op.drop_index(op.f("ix_provider_benchmark_results_provider"), table_name="provider_benchmark_results")
    op.drop_index(op.f("ix_provider_benchmark_results_credential_id"), table_name="provider_benchmark_results")
    op.drop_table("provider_benchmark_results")

    op.drop_index(op.f("ix_provider_benchmark_runs_status"), table_name="provider_benchmark_runs")
    op.drop_index(op.f("ix_provider_benchmark_runs_public_model"), table_name="provider_benchmark_runs")
    op.drop_index(op.f("ix_provider_benchmark_runs_provider"), table_name="provider_benchmark_runs")
    op.drop_table("provider_benchmark_runs")

    op.drop_index(op.f("ix_access_policies_scope_type"), table_name="access_policies")
    op.drop_index(op.f("ix_access_policies_scope_id"), table_name="access_policies")
    op.drop_index(op.f("ix_access_policies_name"), table_name="access_policies")
    op.drop_index(op.f("ix_access_policies_enabled"), table_name="access_policies")
    op.drop_table("access_policies")
