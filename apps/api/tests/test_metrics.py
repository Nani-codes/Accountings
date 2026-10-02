from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AiFinding, Base, Client, Organization, ReconciliationRun
from app.services.metrics import finding_accept_edit_rate


def test_accept_edit_rate():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    org = Organization(name="O")
    db.add(org)
    db.flush()
    client = Client(organization_id=org.id, name="C", services=["GST"])
    db.add(client)
    db.flush()
    run = ReconciliationRun(
        client_id=client.id,
        organization_id=org.id,
        period="2026-03",
        status="reviewed",
    )
    db.add(run)
    db.flush()
    for status in ("accepted", "edited", "dismissed"):
        db.add(
            AiFinding(
                client_id=client.id,
                run_id=run.id,
                category="x",
                severity="low",
                title="t",
                description="d",
                evidence={},
                recommended_action="a",
                status=status,
            )
        )
    db.commit()
    rate = finding_accept_edit_rate(db, org.id)
    assert rate == 2 / 3
