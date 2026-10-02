import json
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Organization, TallyConnection
from app.ai.tally_tools import TallyTools
from app.services.tally_crypto import hash_secret
from app.services.tally_sessions import LiveSession, register_live_session, drop_live_session


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


def test_status_not_connected(db, monkeypatch):
    monkeypatch.setenv("TALLY_TOKEN_PEPPER", "test-pepper")
    from app.config import Settings
    import app.services.tally_crypto as crypto
    crypto.settings = Settings(_env_file=None)
    org = Organization(name="F")
    db.add(org)
    db.flush()
    tools = TallyTools(db=db, organization_id=org.id)
    out = json.loads(tools.tally_connection_status())
    assert out["status"] == "not_connected"


def test_ledger_balance_via_fake_session(db, monkeypatch):
    monkeypatch.setenv("TALLY_TOKEN_PEPPER", "test-pepper")
    from app.config import Settings
    import app.services.tally_crypto as crypto
    crypto.settings = Settings(_env_file=None)
    org = Organization(name="F")
    db.add(org)
    db.flush()
    db.add(
        TallyConnection(
            organization_id=org.id,
            token_hash=hash_secret("tok"),
            status="paired",
            label="pc",
        )
    )
    db.flush()
    sess = LiveSession(organization_id=org.id, tally_ok=True)

    async def fake_rpc(op, args, timeout=25.0):
        assert op == "ledger_balance"
        return {"ledger": args["ledger"], "balance": "1234.00"}

    sess.rpc = fake_rpc  # type: ignore
    register_live_session(org.id, sess)
    tools = TallyTools(db=db, organization_id=org.id)
    out = json.loads(tools.tally_ledger_balance(ledger="Cash"))
    assert out["balance"] == "1234.00"
    drop_live_session(org.id)
