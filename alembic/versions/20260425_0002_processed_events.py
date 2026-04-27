"""add processed_events table

Revision ID: 20260425_0002
Revises: 20260425_0001
Create Date: 2026-04-25 00:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260425_0002"
down_revision: str | None = "20260425_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_processed_events_event_id"),
    )
    op.create_index(
        "ix_processed_events_processed_at",
        "processed_events",
        ["processed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_processed_events_processed_at", table_name="processed_events")
    op.drop_table("processed_events")
