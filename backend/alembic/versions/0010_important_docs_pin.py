"""important docs pin

Revision ID: 0010_important_docs_pin
Revises: 0009_xuandrop_public_token
Create Date: 2026-05-10 23:40:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0010_important_docs_pin"
down_revision: str | None = "0009_xuandrop_public_token"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("vault_pin_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("vault_pin_failed_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("vault_pin_locked_until", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("users", "vault_pin_failed_attempts", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "vault_pin_locked_until")
    op.drop_column("users", "vault_pin_failed_attempts")
    op.drop_column("users", "vault_pin_hash")
