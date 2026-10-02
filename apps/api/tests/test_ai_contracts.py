from app.ai.schemas import ExplainFindingOut


def test_explain_output_schema_parses():
    data = ExplainFindingOut(
        title="GSTIN mismatch — ABC Components",
        description="Supplier GSTIN differs across registers.",
        likely_reason="Supplier GSTIN differs between PR and 2B",
        recommended_action="Verify GSTIN on invoices",
        severity="high",
    )
    assert data.severity == "high"


def test_enrich_findings_with_injected_explain():
    from datetime import date
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.ai.enrich import enrich_findings_from_groups
    from app.models import AiFinding, Base, Client, Organization, ReconciliationRun
    from app.recon.group import ExceptionGroup

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
        status="ai_enriching",
    )
    db.add(run)
    db.commit()

    group = ExceptionGroup(
        category="gstin_mismatch",
        supplier_gstin="29ABCDE1234F1Z5",
        supplier_key="29ABCDE1234F1Z5",
        invoice_count=2,
        potential_itc=Decimal("180"),
        evidence={"invoice_numbers": ["A1", "A2"]},
    )

    def fake_explain(_payload):
        return ExplainFindingOut(
            title="GSTIN mismatch",
            description="Two invoices",
            likely_reason="Typo in GSTIN",
            recommended_action="Confirm with supplier",
            severity="high",
        )

    enrich_findings_from_groups(db, run, [group], explain_fn=fake_explain)
    db.commit()
    findings = db.query(AiFinding).filter(AiFinding.run_id == run.id).all()
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert "Typo" in findings[0].description
