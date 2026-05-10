"""newsfeed_comments: bình luận ẩn danh theo signal_entries

Revision ID: 011
Revises: 010
Create Date: 2026-05-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "newsfeed_comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("signal_entry_id", sa.Integer(), nullable=False),
        sa.Column("commenter_id", UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["signal_entry_id"],
            ["signal_entries.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_newsfeed_comments_signal_entry_id",
        "newsfeed_comments",
        ["signal_entry_id"],
    )
    op.create_index(
        "ix_newsfeed_comments_commenter_id",
        "newsfeed_comments",
        ["commenter_id"],
    )
    op.create_index(
        "ix_newsfeed_comments_deleted_at",
        "newsfeed_comments",
        ["deleted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_newsfeed_comments_deleted_at", table_name="newsfeed_comments")
    op.drop_index("ix_newsfeed_comments_commenter_id", table_name="newsfeed_comments")
    op.drop_index("ix_newsfeed_comments_signal_entry_id", table_name="newsfeed_comments")
    op.drop_table("newsfeed_comments")
