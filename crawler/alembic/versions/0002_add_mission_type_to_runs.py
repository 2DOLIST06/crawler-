"""add mission_type to runs

Revision ID: 0002_add_mission_type_to_runs
Revises: 0001_init
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_mission_type_to_runs"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("runs", sa.Column("mission_type", sa.String(length=50), nullable=False, server_default="simple_crawl"))


def downgrade():
    op.drop_column("runs", "mission_type")
