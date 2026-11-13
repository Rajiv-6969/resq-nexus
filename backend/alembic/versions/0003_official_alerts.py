"""Add official_alerts table.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "official_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_code", sa.String(32), unique=True, index=True, nullable=False),
        sa.Column("sender", sa.String(100), nullable=False),
        sa.Column("headline", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("urgency", sa.String(20), nullable=False, server_default="Immediate"),
        sa.Column("certainty", sa.String(20), nullable=False, server_default="Observed"),
        sa.Column("disaster_type", sa.String(30), index=True, nullable=False),
        sa.Column("area_desc", sa.String(120), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location", Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True),
        sa.Column("source", sa.String(40), nullable=False, server_default="official-imd"),
        sa.Column("status", sa.String(20), index=True, nullable=False, server_default="ACTIVE"),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_by", sa.String(80), nullable=True),
        sa.Column("escalated_at", sa.DateTime(), nullable=True),
        sa.Column("escalation_timeout_mins", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("official_alerts")
