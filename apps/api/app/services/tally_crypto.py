from __future__ import annotations

import hashlib
import hmac

from app.config import settings


def hash_secret(raw: str) -> str:
    msg = f"{settings.tally_token_pepper}:{raw}".encode("utf-8")
    return hashlib.sha256(msg).hexdigest()


def secrets_equal(raw: str, digest: str) -> bool:
    return hmac.compare_digest(hash_secret(raw), digest)
