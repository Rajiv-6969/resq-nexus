"""Initial schema: users, providers, resources, sos_requests with PostGIS locations.

Revision ID: 0001
Revises: None
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# spatial_index=False: the GiST indexes are created explicitly below so they have stable names.
POINT = Geometry(geometry_type="POINT", srid=4326, spatial_index=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(80), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "providers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("organisation_name", sa.String(120), nullable=False),
        sa.Column("organisation_type", sa.String(20), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("location", POINT),
        sa.Column("address", sa.String(160)),
        sa.Column("region", sa.String(60)),
        sa.Column("approval_status", sa.String(12), nullable=False),
        sa.Column("review_note", sa.String(200)),
        sa.Column("reviewed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_providers_approval_status", "providers", ["approval_status"])
    op.create_index("idx_providers_location", "providers", ["location"], postgresql_using="gist")

    op.create_table(
        "resources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(20), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("location", POINT),
        sa.Column("area", sa.String(80)),
        sa.Column("region", sa.String(60)),
        sa.Column("contact_phone", sa.String(20)),
        sa.Column("capacity_total", sa.Integer, nullable=False),
        sa.Column("capacity_available", sa.Integer, nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("provider_id", sa.Integer, sa.ForeignKey("providers.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_resources_resource_type", "resources", ["resource_type"])
    op.create_index("ix_resources_region", "resources", ["region"])
    op.create_index("ix_resources_provider_id", "resources", ["provider_id"])
    op.create_index("idx_resources_location", "resources", ["location"], postgresql_using="gist")

    op.create_table(
        "sos_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("citizen_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("location", POINT),
        sa.Column("location_source", sa.String(8), nullable=False),
        sa.Column("accuracy_m", sa.Float),
        sa.Column("emergency_type", sa.String(20)),
        sa.Column("people_affected", sa.Integer),
        sa.Column("injuries", sa.String(10)),
        sa.Column("needs", sa.JSON, nullable=False),
        sa.Column("vulnerable", sa.JSON, nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("contact_phone", sa.String(20)),
        sa.Column("details_submitted_at", sa.DateTime),
        sa.Column("status", sa.String(14), nullable=False),
        sa.Column("assigned_provider_id", sa.Integer, sa.ForeignKey("providers.id", ondelete="SET NULL")),
        sa.Column("assigned_at", sa.DateTime),
        sa.Column("acknowledged_at", sa.DateTime),
        sa.Column("dispatched_at", sa.DateTime),
        sa.Column("resolved_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_sos_requests_citizen_id", "sos_requests", ["citizen_id"])
    op.create_index("ix_sos_requests_status", "sos_requests", ["status"])
    op.create_index("ix_sos_requests_assigned_provider_id", "sos_requests", ["assigned_provider_id"])
    op.create_index("idx_sos_requests_location", "sos_requests", ["location"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_table("sos_requests")
    op.drop_table("resources")
    op.drop_table("providers")
    op.drop_table("users")
