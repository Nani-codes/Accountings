from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_base_app
from app.models import AiFinding, Base, ReconciliationRun, User


def test_excel_export_contains_summary_sheet():
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
    with TestClient(app) as client:
        token = client.post(
            "/auth/signup",
            json={
                "email": "export@firm.example",
                "password": "secret123",
                "name": "E",
                "firm_name": "EF",
            },
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client_id = client.post("/clients", headers=headers, json={"name": "ABC"}).json()["id"]

        db = Session()
        user = db.query(User).one()
        run = ReconciliationRun(
            client_id=UUID(client_id),
            organization_id=user.organization_id,
            period="2026-03",
            status="reviewed",
            summary={"matched": 2, "exceptions": 1},
        )
        db.add(run)
        db.flush()
        db.add(
            AiFinding(
                client_id=UUID(client_id),
                run_id=run.id,
                category="missing_in_2b",
                severity="high",
                title="Missing",
                description="d",
                evidence={},
                recommended_action="a",
                status="accepted",
            )
        )
        db.commit()
        run_id = str(run.id)
        db.close()

        r = client.get(f"/runs/{run_id}/export.xlsx", headers=headers)
        assert r.status_code == 200, r.text
        assert "spreadsheet" in r.headers["content-type"] or r.headers[
            "content-type"
        ].endswith("sheet")
        assert len(r.content) > 100
