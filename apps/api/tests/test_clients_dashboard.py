from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_base_app
from app.models import Base, ClientRequest, ReconciliationRun, User


@pytest.fixture()
def auth_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_base_app()
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        r = c.post(
            "/auth/signup",
            json={
                "email": "owner@firm.example",
                "password": "secret123",
                "name": "Owner",
                "firm_name": "Owner Firm",
            },
        )
        token = r.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c, TestingSessionLocal
    app.dependency_overrides.clear()


def test_create_and_list_clients(auth_client):
    client, _ = auth_client
    r = client.post(
        "/clients", json={"name": "ABC Pvt Ltd", "gstin": "29ABCDE1234F1Z5"}
    )
    assert r.status_code == 201, r.text
    listed = client.get("/clients")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["name"] == "ABC Pvt Ltd"


def test_dashboard_counts_sent_requests(auth_client):
    client, SessionLocal = auth_client
    create = client.post("/clients", json={"name": "XYZ Industries"})
    assert create.status_code == 201
    client_id = create.json()["id"]

    db = SessionLocal()
    try:
        user = db.query(User).one()
        run = ReconciliationRun(
            client_id=UUID(client_id),
            organization_id=user.organization_id,
            period="2026-03",
            status="needs_review",
        )
        db.add(run)
        db.flush()
        req = ClientRequest(
            client_id=UUID(client_id),
            run_id=run.id,
            finding_ids=[],
            body="Please confirm",
            status="sent",
        )
        db.add(req)
        db.commit()
    finally:
        db.close()

    d = client.get("/dashboard")
    assert d.status_code == 200, d.text
    body = d.json()
    assert body["clients"] == 1
    assert body["client_responses_pending"] == 1
    assert body["active_gst_reviews"] == 1
