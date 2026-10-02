import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_base_app
from app.models import Base


@pytest.fixture()
def client():
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
        yield c
    app.dependency_overrides.clear()


def test_signup_creates_org_and_user(client):
    r = client.post(
        "/auth/signup",
        json={
            "email": "ca@firm.example",
            "password": "secret123",
            "name": "Nani",
            "firm_name": "Nani & Co",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert "access_token" in body
    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "ca@firm.example"
    assert me.json()["organization"]["name"] == "Nani & Co"


def test_login_rejects_bad_password(client):
    client.post(
        "/auth/signup",
        json={
            "email": "ca2@firm.example",
            "password": "secret123",
            "name": "A",
            "firm_name": "F",
        },
    )
    r = client.post(
        "/auth/login", json={"email": "ca2@firm.example", "password": "wrong"}
    )
    assert r.status_code == 401
