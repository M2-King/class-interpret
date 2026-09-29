"""Use macOS Keychain / certifi so python.org Python can download models."""

from __future__ import annotations

import os
import ssl
import subprocess
import sys
from pathlib import Path


def _keychain_bundle() -> Path:
    override = os.environ.get("CLASS_INTERPRET_CERTS")
    if override:
        return Path(override)
    support = os.environ.get("CLASS_INTERPRET_DATA")
    if support:
        return Path(support).parent / "certs.pem"
    return Path.home() / "Library/Application Support/ClassInterpret/certs.pem"


def export_macos_keychain(dest: Path) -> Path | None:
    if sys.platform != "darwin":
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    chains = (
        "/System/Library/Keychains/SystemRootCertificates.keychain",
        "/Library/Keychains/System.keychain",
        str(Path.home() / "Library/Keychains/login.keychain-db"),
        str(Path.home() / "Library/Keychains/login.keychain"),
    )
    pieces: list[bytes] = []
    for chain in chains:
        if not Path(chain).exists():
            continue
        try:
            pieces.append(
                subprocess.check_output(
                    ["security", "find-certificate", "-a", "-p", chain],
                    stderr=subprocess.DEVNULL,
                )
            )
        except (OSError, subprocess.CalledProcessError):
            continue
    if not pieces:
        fallback = Path("/etc/ssl/cert.pem")
        if fallback.is_file():
            dest.write_bytes(fallback.read_bytes())
            return dest
        return None
    dest.write_bytes(b"\n".join(item for item in pieces if item))
    return dest if dest.stat().st_size else None


def apply() -> str | None:
    """Point ssl/requests/pip at a CA bundle that actually contains public CAs."""
    candidates: list[str] = []
    if sys.platform == "darwin":
        dumped = export_macos_keychain(_keychain_bundle())
        if dumped:
            candidates.append(str(dumped))
    for key in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "PIP_CERT"):
        value = os.environ.get(key)
        if value:
            candidates.append(value)
    try:
        import certifi

        candidates.append(certifi.where())
    except Exception:
        pass
    for item in (
        "/etc/ssl/cert.pem",
        "/private/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
    ):
        if Path(item).is_file():
            candidates.append(item)

    seen: set[str] = set()
    for cafile in candidates:
        if not cafile or cafile in seen:
            continue
        seen.add(cafile)
        path = Path(cafile)
        if not path.is_file() or path.stat().st_size == 0:
            continue
        try:
            context = ssl.create_default_context(cafile=cafile)
        except ssl.SSLError:
            continue
        os.environ["SSL_CERT_FILE"] = cafile
        os.environ["REQUESTS_CA_BUNDLE"] = cafile
        os.environ["CURL_CA_BUNDLE"] = cafile
        os.environ["PIP_CERT"] = cafile
        ssl._create_default_https_context = lambda _ctx=context: _ctx
        return cafile
    return None
