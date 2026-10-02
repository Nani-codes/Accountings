from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_base_app
from app.models import AiFinding, Base, Client, ReconciliationRun, User


def _auth_app():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = create_base_app()
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    token = client.post(
        "/auth/signup",
        json={
            "email": "findings@firm.example",
            "password": "secret123",
            "name": "F",
            "firm_name": "FF",
        },
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, Session


def _seed_run_with_findings(Session, statuses: list[str]):
    db = Session()
    user = db.query(User).one()
    client = Client(organization_id=user.organization_id, name="ABC", services=["GST"])
    db.add(client)
    db.flush()
    run = ReconciliationRun(
        client_id=client.id,
        organization_id=user.organization_id,
        period="2026-03",
        status="needs_review",
    )
    db.add(run)
    db.flush()
    ids = []
    for i, status in enumerate(statuses):
        f = AiFinding(
            client_id=client.id,
            run_id=run.id,
            category="missing_in_2b",
            severity="high",
            title=f"Finding {i}",
            description="desc",
            evidence={},
            recommended_action="act",
            status=status,
        )
        db.add(f)
        db.flush()
        ids.append(str(f.id))
    db.commit()
    run_id = str(run.id)
    db.close()
    return run_id, ids


def test_client_request_rejects_pending_only():
    client, Session = _auth_app()
    run_id, _ = _seed_run_with_findings(Session, ["pending"])
    r = client.post(f"/runs/{run_id}/client-requests", json={})
    assert r.status_code == 400


def test_accept_all_marks_run_reviewed():
    client, Session = _auth_app()
    run_id, finding_ids = _seed_run_with_findings(Session, ["pending", "pending"])
    for fid in finding_ids:
        patch = client.patch(f"/findings/{fid}", json={"status": "accepted"})
        assert patch.status_code == 200, patch.text
    run = client.get(f"/runs/{run_id}")
    assert run.status_code == 200
    assert run.json()["status"] == "reviewed"


def test_sent_request_counts_on_dashboard():
    client, Session = _auth_app()
    run_id, finding_ids = _seed_run_with_findings(Session, ["pending"])
    client.patch(f"/findings/{finding_ids[0]}", json={"status": "accepted"})
    created = client.post(f"/runs/{run_id}/client-requests", json={})
    assert created.status_code == 201, created.text
    req_id = created.json()["id"]
    assert client.patch(f"/client-requests/{req_id}", json={"status": "approved"}).status_code == 200
    assert client.patch(f"/client-requests/{req_id}", json={"status": "sent"}).status_code == 200
    d = client.get("/dashboard").json()
    assert d["client_responses_pending"] == 1
