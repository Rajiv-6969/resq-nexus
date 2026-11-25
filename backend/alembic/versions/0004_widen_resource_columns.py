"""Widen resources table column lengths for name, area, and region to String(255).

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("resources") as batch_op:
        batch_op.alter_column("name", type_=sa.String(255), existing_type=sa.String(120), existing_nullable=False)
        batch_op.alter_column("area", type_=sa.String(255), existing_type=sa.String(80), existing_nullable=True)
        batch_op.alter_column("region", type_=sa.String(255), existing_type=sa.String(60), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("resources") as batch_op:
        batch_op.alter_column("region", type_=sa.String(60), existing_type=sa.String(255), existing_nullable=True)
        batch_op.alter_column("area", type_=sa.String(80), existing_type=sa.String(255), existing_nullable=True)
        batch_op.alter_column("name", type_=sa.String(120), existing_type=sa.String(255), existing_nullable=False)
