"""account plan and auth client type

Revision ID: 0012_account_plan_client
Revises: 0011_share_archives
Create Date: 2026-05-12 23:20:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0012_account_plan_client"
down_revision: str | None = "0011_share_archives"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("plan", sa.String(length=32), nullable=False, server_default="internal"))
    op.add_column("auth_sessions", sa.Column("client_type", sa.String(length=32), nullable=False, server_default="user_app"))
    op.alter_column("users", "plan", server_default=None)
    op.alter_column("auth_sessions", "client_type", server_default=None)


def downgrade() -> None:
    op.drop_column("auth_sessions", "client_type")
    op.drop_column("users", "plan")
