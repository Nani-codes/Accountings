from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Client, ClientDocument, Organization, ReconciliationRun, User
from app.services.run_pipeline import start_run

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "recon" / "tiny_pair"


def test_run_pipeline_with_injected_bytes():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = Session()

    org = Organization(name="Firm")
    db.add(org)
    db.flush()
    user = User(organization_id=org.id, email="p@firm.example", name="P")
    db.add(user)
    client = Client(organization_id=org.id, name="ABC", services=["GST"])
    db.add(client)
    db.flush()
    run = ReconciliationRun(
        client_id=client.id,
        organization_id=org.id,
        period="2026-03",
        status="uploading",
    )
    db.add(run)
    db.flush()

    files = {
        "purchase_register": (FIXTURE / "purchase.csv").read_bytes(),
        "gstr2b": (FIXTURE / "gstr2b.csv").read_bytes(),
    }
    for doc_type, data in files.items():
        db.add(
            ClientDocument(
                client_id=client.id,
                run_id=run.id,
                doc_type=doc_type,
                storage_key=doc_type,
                filename=f"{doc_type}.csv",
            )
        )
    db.commit()

    started = start_run(db, run.id, load_bytes=lambda key: files[key])
    assert started.status == "needs_review"
    assert started.summary["matched"] == 2
    assert started.summary["exceptions"] == 1
    db.close()
