#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import secret_box

secret = "sk-test-class-interpret-not-real"
blob = secret_box.seal(secret)
assert blob.startswith(b"CI1."), blob[:20]
assert b"sk-test" not in blob
assert secret not in blob.decode("ascii", errors="ignore")
assert secret_box.unseal(blob) == secret
try:
    secret_box.unseal(blob[:-1] + b"x")
    raise SystemExit("tamper should fail")
except ValueError:
    pass
print("secret_box ok")
