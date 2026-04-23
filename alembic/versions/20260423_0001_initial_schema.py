"""initial schema"""

from alembic import op
import sqlalchemy as sa

revision = "20260423_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True, unique=True),
        sa.Column("dedup_key", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_dedup_key", "tasks", ["dedup_key"])

    op.create_table(
        "task_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("task_id", "attempt_no", name="uq_task_attempt"),
    )
    op.create_index("ix_task_attempts_task_id", "task_attempts", ["task_id"])

    op.create_table(
        "task_results",
        sa.Column("task_id", sa.String(length=64), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("final_outcome", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "provider_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_provider_runs_task_id", "provider_runs", ["task_id"])

    op.create_table(
        "validation_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_validation_reports_task_id", "validation_reports", ["task_id"])

    op.create_table(
        "scoring_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("max_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scoring_reports_task_id", "scoring_reports", ["task_id"])

    op.create_table(
        "system_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_system_events_event_type", "system_events", ["event_type"])
    op.create_index("ix_system_events_correlation_id", "system_events", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_system_events_correlation_id", table_name="system_events")
    op.drop_index("ix_system_events_event_type", table_name="system_events")
    op.drop_table("system_events")
    op.drop_index("ix_scoring_reports_task_id", table_name="scoring_reports")
    op.drop_table("scoring_reports")
    op.drop_index("ix_validation_reports_task_id", table_name="validation_reports")
    op.drop_table("validation_reports")
    op.drop_index("ix_provider_runs_task_id", table_name="provider_runs")
    op.drop_table("provider_runs")
    op.drop_table("task_results")
    op.drop_index("ix_task_attempts_task_id", table_name="task_attempts")
    op.drop_table("task_attempts")
    op.drop_index("ix_tasks_dedup_key", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_table("tasks")
