"""encrypt note bodies at rest

Revision ID: 0023_encrypt_note_bodies
Revises: 0022_vault_notes
Create Date: 2026-11-19 18:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from app.services.encryption_service import TEXT_PREFIX, decrypt_text, encrypt_text

revision: str = "0023_encrypt_note_bodies"
down_revision: str | None = "0022_vault_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PURPOSE = "notes.body"


def upgrade() -> None:
    bind = op.get_bind()
    for note_id, body in bind.execute(sa.text("SELECT id, body FROM notes")).all():
        if not body.startswith(TEXT_PREFIX):
            # updated_at is left alone: encrypting is not an edit.
            bind.execute(sa.text("UPDATE notes SET body = :body WHERE id = :id"), {"body": encrypt_text(body, PURPOSE), "id": note_id})


def downgrade() -> None:
    bind = op.get_bind()
    for note_id, body in bind.execute(sa.text("SELECT id, body FROM notes")).all():
        if body.startswith(TEXT_PREFIX):
            bind.execute(sa.text("UPDATE notes SET body = :body WHERE id = :id"), {"body": decrypt_text(body, PURPOSE), "id": note_id})
