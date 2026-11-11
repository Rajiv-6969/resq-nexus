"""Resources remember where they came from (synthetic seed, OpenStreetMap, a user).

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resources", sa.Column("source", sa.String(10), nullable=False, server_default="seed"))
    op.add_column("resources", sa.Column("osm_id", sa.String(20)))


def downgrade() -> None:
    op.drop_column("resources", "osm_id")
    op.drop_column("resources", "source")
