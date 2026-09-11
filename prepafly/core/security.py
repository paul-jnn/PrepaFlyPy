"""Verrou par code PIN : empreinte SHA-256 salée. Le PIN n'est jamais stocké en
clair, seulement son empreinte, que l'on recompare à la saisie."""
from __future__ import annotations

import hashlib

_SALT = b"mgi-prepaflypy-v1"


def hash_pin(pin: str) -> str:
    h = hashlib.sha256()
    h.update(_SALT)
    h.update(pin.encode("utf-8"))
    return h.hexdigest()
