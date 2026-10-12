"""Encrypted backup container.

Layout: MAGIC | 16-byte salt | chunks. Each chunk is a 12-byte nonce, a 4-byte big-endian ciphertext
length and AES-256-GCM ciphertext. The chunk index and a "last chunk" flag are authenticated as
associated data, so chunks cannot be reordered, dropped or the file truncated without detection.
The key is derived from MASTER_KEY with HKDF, so a backup restores only where MASTER_KEY is known;
without MASTER_KEY the stored files cannot be decrypted anyway.
"""

import os
import struct
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings

MAGIC = b"XBBACKUP1\n"
CHUNK_SIZE = 4 * 1024 * 1024
ENCRYPTED_SUFFIX = ".xbenc"


def _key(salt: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b"xuanbox-backup-v1").derive(settings.MASTER_KEY.encode("utf-8"))


def _aad(index: int, last: bool) -> bytes:
    return struct.pack(">QB", index, 1 if last else 0)


def encrypt_file(source: Path, target: Path) -> None:
    salt = os.urandom(16)
    aes = AESGCM(_key(salt))
    with source.open("rb") as reader, target.open("wb") as writer:
        writer.write(MAGIC + salt)
        index = 0
        chunk = reader.read(CHUNK_SIZE)
        while True:
            following = reader.read(CHUNK_SIZE)
            last = not following
            nonce = os.urandom(12)
            ciphertext = aes.encrypt(nonce, chunk, _aad(index, last))
            writer.write(nonce + struct.pack(">I", len(ciphertext)) + ciphertext)
            if last:
                break
            chunk = following
            index += 1


def decrypt_file(source: Path, target: Path) -> None:
    with source.open("rb") as reader, target.open("wb") as writer:
        if reader.read(len(MAGIC)) != MAGIC:
            raise ValueError("Not an encrypted XuanBox backup")
        aes = AESGCM(_key(reader.read(16)))
        index = 0
        header = reader.read(16)
        while header:
            if len(header) != 16:
                raise ValueError("Backup file is truncated")
            nonce, length = header[:12], struct.unpack(">I", header[12:])[0]
            ciphertext = reader.read(length)
            following = reader.read(16)
            last = not following
            # Raises InvalidTag if the data, order or ending was tampered with.
            writer.write(aes.decrypt(nonce, ciphertext, _aad(index, last)))
            header = following
            index += 1
        if index == 0:
            raise ValueError("Backup file is empty")
