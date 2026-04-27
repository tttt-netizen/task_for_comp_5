"""initial schema

Revision ID: 20260425_0001
Revises:
Create Date: 2026-04-25 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260425_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "affiliates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("affiliate_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["affiliate_id"], ["affiliates.id"]),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_leads_created_at", "leads", ["created_at"], unique=False)
    op.create_index(
        "ix_leads_affiliate_created_at",
        "leads",
        ["affiliate_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_leads_dedup_window",
        "leads",
        ["name", "phone", "offer_id", "affiliate_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_leads_dedup_window", table_name="leads")
    op.drop_index("ix_leads_affiliate_created_at", table_name="leads")
    op.drop_index("ix_leads_created_at", table_name="leads")
    op.drop_table("leads")
    op.drop_table("affiliates")
    op.drop_table("offers")
