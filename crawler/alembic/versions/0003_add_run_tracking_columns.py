"""add run tracking columns

Revision ID: 0003_add_run_tracking_columns
Revises: 0002_add_mission_type_to_runs
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_add_run_tracking_columns"
down_revision = "0002_add_mission_type_to_runs"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(col["name"] == column_name for col in columns)


def upgrade() -> None:
    if not _has_table("runs"):
        return

    with op.batch_alter_table("runs") as batch_op:
        if not _has_column("runs", "last_crawled_url"):
            batch_op.add_column(sa.Column("last_crawled_url", sa.Text(), nullable=True))

        if not _has_column("runs", "updated_at"):
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                )
            )


def downgrade() -> None:
    if not _has_table("runs"):
        return

    with op.batch_alter_table("runs") as batch_op:
        if _has_column("runs", "updated_at"):
            batch_op.drop_column("updated_at")

        if _has_column("runs", "last_crawled_url"):
            batch_op.drop_column("last_crawled_url")
