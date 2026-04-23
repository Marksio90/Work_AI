"""rapidapi usage and payout reconciliation"""

from alembic import op
import sqlalchemy as sa

revision = "20260423_0003"
down_revision = "20260423_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscriber_id", sa.String(length=128), nullable=False),
        sa.Column("subscription_plan", sa.String(length=32), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("task_id", sa.String(length=64), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_units", sa.Integer(), nullable=False),
        sa.Column("estimated_revenue_usd", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_usage_events_subscriber_id", "api_usage_events", ["subscriber_id"])
    op.create_index("ix_api_usage_events_subscription_plan", "api_usage_events", ["subscription_plan"])
    op.create_index("ix_api_usage_events_created_at", "api_usage_events", ["created_at"])

    op.create_table(
        "payout_reconciliations",
        sa.Column("month", sa.String(length=7), primary_key=True),
        sa.Column("estimated_revenue_usd", sa.Float(), nullable=False),
        sa.Column("paid_amount_usd", sa.Float(), nullable=False),
        sa.Column("variance_usd", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("payout_reconciliations")
    op.drop_index("ix_api_usage_events_created_at", table_name="api_usage_events")
    op.drop_index("ix_api_usage_events_subscription_plan", table_name="api_usage_events")
    op.drop_index("ix_api_usage_events_subscriber_id", table_name="api_usage_events")
    op.drop_table("api_usage_events")
