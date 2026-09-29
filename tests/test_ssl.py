#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ssl_certs

path = ssl_certs.apply()
assert path, "expected a CA bundle"
print(f"ssl_certs ok: {path}")
