from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_base_app
from app.models import Base
import app.api.uploads as uploads_mod


def test_create_run_and_upload_with_stubbed_storage(monkeypatch):
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

    monkeypatch.setattr(
        uploads_mod, "put_object", lambda key, data, content_type="": key
    )

    app = create_base_app()
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        token = client.post(
            "/auth/signup",
            json={
                "email": "upload@firm.example",
                "password": "secret123",
                "name": "U",
                "firm_name": "UF",
            },
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client_id = client.post(
            "/clients", headers=headers, json={"name": "ABC"}
        ).json()["id"]
        run = client.post(
            f"/clients/{client_id}/runs",
            headers=headers,
            json={"period": "2026-03"},
        )
        assert run.status_code == 201, run.text
        run_id = run.json()["id"]
        UUID(run_id)

        upload = client.post(
            f"/runs/{run_id}/documents",
            headers=headers,
            data={"doc_type": "purchase_register"},
            files={"file": ("pr.csv", b"invoice_number,total\nA1,1\n", "text/csv")},
        )
        assert upload.status_code == 201, upload.text
        assert upload.json()["doc_type"] == "purchase_register"

        templates = client.get("/mapping/templates", headers=headers)
        assert templates.status_code == 200
        assert "generic_purchase" in templates.json()["templates"]
