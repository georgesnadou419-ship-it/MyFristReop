"""create phase1 tables

Revision ID: 20260506_0001
Revises:
Create Date: 2026-05-06 18:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260506_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column("gpu_quota", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("api_key", sa.String(length=128), nullable=True),
        sa.Column("credits", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("api_key"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "nodes",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("hostname", sa.String(length=128), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("agent_port", sa.Integer(), nullable=False, server_default="9000"),
        sa.Column("gpu_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gpu_model", sa.String(length=64), nullable=True),
        sa.Column("total_memory_mb", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="offline"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=False), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("ip"),
    )

    op.create_table(
        "gpu_devices",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("node_id", sa.String(length=36), nullable=False),
        sa.Column("gpu_index", sa.Integer(), nullable=False),
        sa.Column("gpu_model", sa.String(length=64), nullable=True),
        sa.Column("memory_total_mb", sa.Integer(), nullable=True),
        sa.Column("memory_used_mb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("utilization", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("temperature", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("power_usage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="idle"),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
        sa.UniqueConstraint("node_id", "gpu_index", name="uq_gpu_devices_node_index"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("task_type", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assigned_node_id", sa.String(length=36), nullable=True),
        sa.Column("assigned_gpu_indices", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("container_image", sa.String(length=256), nullable=True),
        sa.Column("container_command", sa.Text(), nullable=True),
        sa.Column("container_id", sa.String(length=64), nullable=True),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("billed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["assigned_node_id"], ["nodes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "task_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
    )
    op.create_table(
        "billing_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("resource_type", sa.String(length=20), nullable=False, server_default="gpu_time"),
        sa.Column("gpu_model", sa.String(length=64), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_credits", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
    )
    op.create_index("ix_billing_records_user_id", "billing_records", ["user_id"])
    op.create_index("ix_billing_records_task_id", "billing_records", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_billing_records_task_id", table_name="billing_records")
    op.drop_index("ix_billing_records_user_id", table_name="billing_records")
    op.drop_table("billing_records")
    op.drop_table("task_logs")
    op.drop_table("tasks")
    op.drop_table("gpu_devices")
    op.drop_table("nodes")
    op.drop_table("users")
