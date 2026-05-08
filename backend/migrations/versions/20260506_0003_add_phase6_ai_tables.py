"""add phase6 ai tables

Revision ID: 20260506_0003
Revises: 20260506_0002
Create Date: 2026-05-06 18:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260506_0003"
down_revision = "20260506_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "models",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("model_type", sa.String(length=32), nullable=True),
        sa.Column("framework", sa.String(length=32), nullable=True),
        sa.Column("model_path", sa.String(length=512), nullable=True),
        sa.Column("container_image", sa.String(length=256), nullable=True),
        sa.Column("launch_command", sa.Text(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="offline"),
        sa.Column("replicas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("gpu_requirement", sa.String(length=64), nullable=True),
        sa.Column("api_format", sa.String(length=32), nullable=False, server_default="openai"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "model_instances",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("model_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=36), nullable=False),
        sa.Column("container_id", sa.String(length=64), nullable=True),
        sa.Column("assigned_gpu_indices", sa.JSON(), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="starting"),
        sa.Column("api_endpoint", sa.String(length=256), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
    )
    op.create_index("ix_model_instances_model_id", "model_instances", ["model_id"])
    op.create_index("ix_model_instances_node_id", "model_instances", ["node_id"])

    op.create_table(
        "api_calls",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("api_key", sa.String(length=128), nullable=True),
        sa.Column("model_name", sa.String(length=64), nullable=True),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_api_calls_user_id", "api_calls", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_api_calls_user_id", table_name="api_calls")
    op.drop_table("api_calls")
    op.drop_index("ix_model_instances_node_id", table_name="model_instances")
    op.drop_index("ix_model_instances_model_id", table_name="model_instances")
    op.drop_table("model_instances")
    op.drop_table("models")
