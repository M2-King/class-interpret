"""Encrypt a small secret at rest. Stdlib only: PBKDF2 + HMAC + keystream XOR."""

from __future__ import annotations

import hmac
import os
from hashlib import pbkdf2_hmac, sha256

PREFIX = b"CI1."
_ROUNDS = 200_000


def _pepper() -> bytes:
    return "-".join(("cls", "int", "ds", "v1", "7f3a9c")).encode("ascii")


def _material(salt: bytes) -> tuple[bytes, bytes]:
    raw = pbkdf2_hmac("sha256", _pepper(), salt, _ROUNDS, dklen=64)
    return raw[:32], raw[32:]


def _keystream(key: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(sha256(key + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:length])


def _xor(data: bytes, key: bytes) -> bytes:
    stream = _keystream(key, len(data))
    return bytes(a ^ b for a, b in zip(data, stream))


def seal(plaintext: str, *, salt: bytes | None = None) -> bytes:
    text = (plaintext or "").strip().encode("utf-8")
    if not text:
        raise ValueError("empty secret")
    salt = salt or os.urandom(16)
    enc_key, mac_key = _material(salt)
    cipher = _xor(text, enc_key)
    digest = hmac.new(mac_key, salt + cipher, sha256).digest()
    return PREFIX + salt.hex().encode("ascii") + b"." + digest.hex().encode("ascii") + b"." + cipher.hex().encode("ascii")


def unseal(blob: bytes) -> str:
    raw = blob.strip()
    if not raw.startswith(PREFIX):
        raise ValueError("not a class-interpret secret")
    try:
        _, salt_hex, mac_hex, cipher_hex = raw.split(b".", 3)
        salt = bytes.fromhex(salt_hex.decode("ascii"))
        expected = bytes.fromhex(mac_hex.decode("ascii"))
        cipher = bytes.fromhex(cipher_hex.decode("ascii"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("corrupt secret") from exc
    enc_key, mac_key = _material(salt)
    actual = hmac.new(mac_key, salt + cipher, sha256).digest()
    if not hmac.compare_digest(actual, expected):
        raise ValueError("secret was altered")
    return _xor(cipher, enc_key).decode("utf-8")
