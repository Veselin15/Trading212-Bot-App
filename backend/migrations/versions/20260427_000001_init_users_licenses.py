"""init users and licenses

Revision ID: 20260427_000001
Revises:
Create Date: 2026-04-27

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260427_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    license_status = postgresql.ENUM("active", "suspended", "expired", name="license_status")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=True)

    op.create_table(
        "licenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("license_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", license_status, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_ip_address", postgresql.INET(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_licenses_license_key", "licenses", ["license_key"], unique=True)
    op.create_index("ix_licenses_user_id", "licenses", ["user_id"], unique=False)
    op.create_index("ix_licenses_status", "licenses", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_licenses_status", table_name="licenses")
    op.drop_index("ix_licenses_user_id", table_name="licenses")
    op.drop_index("ix_licenses_license_key", table_name="licenses")
    op.drop_table("licenses")

    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS license_status")
