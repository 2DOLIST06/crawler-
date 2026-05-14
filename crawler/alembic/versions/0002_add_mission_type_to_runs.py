"""add mission_type to runs

Revision ID: 0002_add_mission_type_to_runs
Revises: 0001
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_mission_type_to_runs"
down_revision = "0001"
branch_labels = None
depends_on = None


DEFAULT_MISSION_TYPE = "simple_crawl"


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(col["name"] == column_name for col in columns)


def upgrade():
    if not _has_table("runs") or _has_column("runs", "mission_type"):
        return

    with op.batch_alter_table("runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "mission_type",
                sa.String(length=50),
                nullable=False,
                server_default=sa.text(f"'{DEFAULT_MISSION_TYPE}'"),
            )
        )

    op.get_bind().execute(
        sa.text("UPDATE runs SET mission_type = :default_value WHERE mission_type IS NULL"),
        {"default_value": DEFAULT_MISSION_TYPE},
    )


def downgrade():
    if not _has_table("runs") or not _has_column("runs", "mission_type"):
        return

    with op.batch_alter_table("runs") as batch_op:
        batch_op.drop_column("mission_type")
