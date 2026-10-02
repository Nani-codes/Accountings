from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Organization, TallyPairingCode
from app.services.tally_pairing import (
    connection_status_for_org,
    consume_pairing_code,
    create_pairing_code,
    disconnect_org,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


def _patch_pepper(monkeypatch):
    monkeypatch.setenv("TALLY_TOKEN_PEPPER", "test-pepper")
    from app.config import Settings
    import app.services.tally_crypto as crypto
    import app.services.tally_pairing as pairing

    s = Settings(_env_file=None)
    crypto.settings = s
    pairing.settings = s


def test_create_and_consume_pairing(db, monkeypatch):
    _patch_pepper(monkeypatch)

    org = Organization(name="Firm")
    db.add(org)
    db.flush()
    code, expires = create_pairing_code(db, org.id)
    db.commit()
    assert len(code) >= 6
    assert expires > datetime.now(timezone.utc)

    conn, token = consume_pairing_code(db, code, label="desk-pc")
    db.commit()
    assert conn.organization_id == org.id
    assert conn.status == "paired"
    assert token
    assert connection_status_for_org(db, org.id, live_session=None)["status"] == "offline"

    disconnect_org(db, org.id)
    db.commit()
    assert (
        connection_status_for_org(db, org.id, live_session=None)["status"]
        == "not_connected"
    )


def test_expired_code_rejected(db, monkeypatch):
    _patch_pepper(monkeypatch)

    org = Organization(name="Firm")
    db.add(org)
    db.flush()
    code, _ = create_pairing_code(db, org.id)
    row = db.query(TallyPairingCode).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    with pytest.raises(ValueError, match="expired|invalid"):
        consume_pairing_code(db, code)
