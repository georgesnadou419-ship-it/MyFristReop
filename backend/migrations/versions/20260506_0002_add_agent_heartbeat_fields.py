"""add agent heartbeat fields

Revision ID: 20260506_0002
Revises: 20260506_0001
Create Date: 2026-05-06 19:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260506_0002"
down_revision = "20260506_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nodes", sa.Column("cpu_percent", sa.Float(), nullable=False, server_default="0"))
    op.add_column("nodes", sa.Column("memory_percent", sa.Float(), nullable=False, server_default="0"))

    op.add_column("gpu_devices", sa.Column("gpu_uuid", sa.String(length=128), nullable=True))
    op.add_column("gpu_devices", sa.Column("memory_free_mb", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("gpu_devices", sa.Column("utilization_memory", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("gpu_devices", sa.Column("power_limit", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("gpu_devices", sa.Column("processes", sa.JSON(), nullable=True))

    op.create_table(
        "running_containers",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("node_id", sa.String(length=36), nullable=False),
        sa.Column("container_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("image", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("gpu_indices", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
        sa.UniqueConstraint("container_id"),
    )
    op.create_index("ix_running_containers_task_id", "running_containers", ["task_id"])

    op.create_table(
        "gpu_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("node_id", sa.String(length=36), nullable=False),
        sa.Column("gpu_index", sa.Integer(), nullable=False),
        sa.Column("utilization", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("memory_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("memory_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("temperature", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("power_usage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
    )
    op.create_index("ix_gpu_metrics_node_id", "gpu_metrics", ["node_id"])
    op.create_index("ix_gpu_metrics_gpu_index", "gpu_metrics", ["gpu_index"])
    op.create_index("ix_gpu_metrics_timestamp", "gpu_metrics", ["timestamp"])
    op.create_index("idx_gpu_metrics_node_time", "gpu_metrics", ["node_id", "timestamp"])


def downgrade() -> None:
    op.drop_index("idx_gpu_metrics_node_time", table_name="gpu_metrics")
    op.drop_index("ix_gpu_metrics_timestamp", table_name="gpu_metrics")
    op.drop_index("ix_gpu_metrics_gpu_index", table_name="gpu_metrics")
    op.drop_index("ix_gpu_metrics_node_id", table_name="gpu_metrics")
    op.drop_table("gpu_metrics")
    op.drop_index("ix_running_containers_task_id", table_name="running_containers")
    op.drop_table("running_containers")
    op.drop_column("gpu_devices", "processes")
    op.drop_column("gpu_devices", "power_limit")
    op.drop_column("gpu_devices", "utilization_memory")
    op.drop_column("gpu_devices", "memory_free_mb")
    op.drop_column("gpu_devices", "gpu_uuid")
    op.drop_column("nodes", "memory_percent")
    op.drop_column("nodes", "cpu_percent")
