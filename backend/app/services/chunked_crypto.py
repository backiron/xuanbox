"""Chunk-by-chunk AES-256-GCM for large XuanDrop files.

Each record is a 12-byte nonce, a 4-byte big-endian ciphertext length and the ciphertext. The file id,
chunk index and a "last chunk" flag are authenticated as associated data, so records cannot be moved
between files, reordered, dropped or cut off without the decryption failing. Files of any size are
written and read without holding more than one chunk in memory.
"""

import os
import struct
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT_SINGLE = "single"
FORMAT_CHUNKED = "chunked-v1"
_HEADER = 16


def _aad(file_id: UUID, index: int, last: bool) -> bytes:
    return file_id.bytes + struct.pack(">QB", index, 1 if last else 0)


def encrypt_chunk(key: bytes, file_id: UUID, index: int, last: bool, data: bytes) -> bytes:
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, data, _aad(file_id, index, last))
    return nonce + struct.pack(">I", len(ciphertext)) + ciphertext


def iter_decrypt(path: Path | str, key: bytes, file_id: UUID) -> Iterator[bytes]:
    aes = AESGCM(key)
    with open(path, "rb") as reader:
        index = 0
        header = reader.read(_HEADER)
        while header:
            if len(header) != _HEADER:
                raise ValueError("Encrypted file is truncated")
            nonce, length = header[:12], struct.unpack(">I", header[12:])[0]
            ciphertext = reader.read(length)
            following = reader.read(_HEADER)
            yield aes.decrypt(nonce, ciphertext, _aad(file_id, index, not following))
            header = following
            index += 1
