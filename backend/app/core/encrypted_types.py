from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


class EncryptedText(TypeDecorator):
    """Text encrypted at rest (AES-256-GCM, key derived from MASTER_KEY); code sees plain strings.

    The database, its dumps and backups only hold ciphertext, so these columns cannot be searched with
    SQL: filter after loading instead.
    """

    impl = Text
    cache_ok = True

    def __init__(self, purpose: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.purpose = purpose

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        from app.services.encryption_service import encrypt_text

        return encrypt_text(value, self.purpose)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        from app.services.encryption_service import decrypt_text

        return decrypt_text(value, self.purpose)
