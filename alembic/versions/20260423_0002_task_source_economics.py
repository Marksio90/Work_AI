"""task source + economics tables"""

from alembic import op
import sqlalchemy as sa

revision = "20260423_0002"
down_revision = "20260423_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("external_task_id", sa.String(length=128), nullable=False),
        sa.Column("internal_task_id", sa.String(length=64), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expected_payout_usd", sa.Float(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("expected_margin_usd", sa.Float(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source_name", "external_task_id", name="uq_external_task_source_id"),
    )
    op.create_index("ix_external_tasks_status", "external_tasks", ["status"])

    op.create_table(
        "task_economics",
        sa.Column("task_id", sa.String(length=64), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("expected_payout_usd", sa.Float(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("actual_payout_usd", sa.Float(), nullable=True),
        sa.Column("expected_success_probability", sa.Float(), nullable=False),
        sa.Column("margin_usd", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_task_economics_status", "task_economics", ["status"])


def downgrade() -> None:
    op.drop_index("ix_task_economics_status", table_name="task_economics")
    op.drop_table("task_economics")
    op.drop_index("ix_external_tasks_status", table_name="external_tasks")
    op.drop_table("external_tasks")
