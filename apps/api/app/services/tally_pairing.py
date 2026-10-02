from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models import TallyConnection, TallyPairingCode
from app.services.tally_crypto import hash_secret, secrets_equal

PAIRING_TTL = timedelta(minutes=15)
CODE_ALPHABET = string.ascii_uppercase + string.digits


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_code(n: int = 8) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(n))


def create_pairing_code(db: Session, organization_id: UUID) -> tuple[str, datetime]:
    for _ in range(8):
        code = _generate_code()
        digest = hash_secret(code)
        if db.query(TallyPairingCode).filter(TallyPairingCode.code_hash == digest).first():
            continue
        expires = _now() + PAIRING_TTL
        db.add(
            TallyPairingCode(
                organization_id=organization_id,
                code_hash=digest,
                expires_at=expires,
            )
        )
        db.flush()
        return code, expires
    raise RuntimeError("could not allocate pairing code")


def consume_pairing_code(
    db: Session, code: str, *, label: str | None = None
) -> tuple[TallyConnection, str]:
    raw = (code or "").strip().upper()
    if not raw:
        raise ValueError("invalid pairing code")
    digest = hash_secret(raw)
    row = (
        db.query(TallyPairingCode)
        .filter(TallyPairingCode.code_hash == digest)
        .one_or_none()
    )
    if row is None or row.consumed_at is not None:
        raise ValueError("invalid pairing code")
    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < _now():
        raise ValueError("pairing code expired")
    row.consumed_at = _now()
    existing = (
        db.query(TallyConnection)
        .filter(
            TallyConnection.organization_id == row.organization_id,
            TallyConnection.status == "paired",
        )
        .all()
    )
    for c in existing:
        c.status = "revoked"
        c.revoked_at = _now()
    device_token = secrets.token_urlsafe(32)
    conn = TallyConnection(
        organization_id=row.organization_id,
        token_hash=hash_secret(device_token),
        label=label,
        status="paired",
    )
    db.add(conn)
    db.flush()
    return conn, device_token


def disconnect_org(db: Session, organization_id: UUID) -> None:
    rows = (
        db.query(TallyConnection)
        .filter(
            TallyConnection.organization_id == organization_id,
            TallyConnection.status == "paired",
        )
        .all()
    )
    for c in rows:
        c.status = "revoked"
        c.revoked_at = _now()
    db.flush()


def connection_status_for_org(
    db: Session, organization_id: UUID, *, live_session
) -> dict:
    conn = (
        db.query(TallyConnection)
        .filter(
            TallyConnection.organization_id == organization_id,
            TallyConnection.status == "paired",
        )
        .order_by(TallyConnection.created_at.desc())
        .first()
    )
    if conn is None:
        return {"status": "not_connected"}
    base = {
        "device_label": conn.label,
        "last_seen_at": conn.last_seen_at.isoformat() if conn.last_seen_at else None,
        "last_tally_ok_at": conn.last_tally_ok_at.isoformat()
        if conn.last_tally_ok_at
        else None,
    }
    if live_session is None:
        return {"status": "offline", **base}
    if not getattr(live_session, "tally_ok", False):
        return {"status": "tally_unreachable", **base}
    return {"status": "online", **base}


def find_connection_by_device_token(db: Session, token: str) -> TallyConnection | None:
    raw = (token or "").strip()
    if not raw:
        return None
    rows = db.query(TallyConnection).filter(TallyConnection.status == "paired").all()
    for row in rows:
        if secrets_equal(raw, row.token_hash):
            return row
    return None
