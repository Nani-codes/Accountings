from __future__ import annotations

import io
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AiFinding,
    ClientDocument,
    ColumnMappingProfile,
    Invoice,
    ReconciliationResult,
    ReconciliationRun,
)
from app.recon.group import group_exceptions
from app.recon.mapper import apply_mapping
from app.recon.match import reconcile
from app.recon.normalize import to_invoice
from app.recon.templates import TEMPLATES
from app.services.storage import _client


def _load_bytes(storage_key: str) -> bytes:
    obj = _client().get_object(Bucket=settings.s3_bucket, Key=storage_key)
    return obj["Body"].read()


def _mapping_for(db: Session, client_id: UUID, doc_type: str) -> dict[str, str]:
    profile = (
        db.query(ColumnMappingProfile)
        .filter(
            ColumnMappingProfile.client_id == client_id,
            ColumnMappingProfile.doc_type == doc_type,
        )
        .first()
    )
    if profile:
        return profile.mapping
    if doc_type in ("purchase_register", "sales_register"):
        return TEMPLATES["generic_purchase"]
    if doc_type == "gstr2b":
        return TEMPLATES["generic_gstr2b"]
    raise HTTPException(status_code=400, detail=f"No mapping for {doc_type}")


def _read_tabular(data: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    return pd.read_excel(io.BytesIO(data))


def enrich_findings_stub(db: Session, run: ReconciliationRun, groups) -> None:
    for group in groups:
        db.add(
            AiFinding(
                client_id=run.client_id,
                run_id=run.id,
                category=group.category,
                severity="medium",
                title=f"{group.category.replace('_', ' ').title()} — {group.supplier_key}",
                description=f"{group.invoice_count} invoices affected.",
                evidence=group.evidence,
                recommended_action="Review supporting documents with the client.",
                status="pending",
            )
        )


def start_run(
    db: Session,
    run_id: UUID,
    *,
    load_bytes=_load_bytes,
) -> ReconciliationRun:
    run = db.query(ReconciliationRun).filter(ReconciliationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    docs = db.query(ClientDocument).filter(ClientDocument.run_id == run.id).all()
    by_type = {d.doc_type: d for d in docs}
    if "purchase_register" not in by_type or "gstr2b" not in by_type:
        raise HTTPException(
            status_code=400,
            detail="Purchase Register and GSTR-2B are required before starting",
        )

    try:
        run.status = "parsing"
        db.commit()

        def parse_doc(doc_type: str, source: str) -> list:
            doc = by_type[doc_type]
            data = load_bytes(doc.storage_key)
            df = _read_tabular(data, doc.filename)
            mapping = _mapping_for(db, run.client_id, doc_type)
            rows = apply_mapping(df, mapping)
            domains = []
            for row in rows:
                domain = to_invoice(row)
                db.add(
                    Invoice(
                        run_id=run.id,
                        source=source,
                        invoice_number=domain.invoice_number,
                        invoice_date=domain.invoice_date,
                        supplier_gstin=domain.supplier_gstin,
                        recipient_gstin=domain.recipient_gstin,
                        taxable_value=domain.taxable_value,
                        igst=domain.igst,
                        cgst=domain.cgst,
                        sgst=domain.sgst,
                        cess=domain.cess,
                        total=domain.total,
                        raw=row,
                    )
                )
                domains.append(domain)
            db.flush()
            return domains

        parse_doc("purchase_register", "purchase")
        parse_doc("gstr2b", "gstr2b")
        if "sales_register" in by_type:
            sales = parse_doc("sales_register", "sales")
            by_type["sales_register"].parsed_stats = {
                "invoice_count": len(sales),
                "taxable_total": str(sum((s.taxable_value for s in sales), Decimal("0"))),
            }
        if "bank_statement" in by_type:
            by_type["bank_statement"].parsed_stats = {"stored_only": True}
        if "previous_reconciliation" in by_type:
            by_type["previous_reconciliation"].parsed_stats = {
                "stored_only": True,
                "note": "Parsed only when export schema matches",
            }

        run.status = "reconciling"
        db.commit()

        purchase_orm = (
            db.query(Invoice)
            .filter(Invoice.run_id == run.id, Invoice.source == "purchase")
            .all()
        )
        gstr_orm = (
            db.query(Invoice)
            .filter(Invoice.run_id == run.id, Invoice.source == "gstr2b")
            .all()
        )

        def to_domain(i: Invoice):
            return to_invoice(
                {
                    "invoice_number": i.invoice_number,
                    "invoice_date": i.invoice_date,
                    "supplier_gstin": i.supplier_gstin,
                    "recipient_gstin": i.recipient_gstin,
                    "taxable_value": i.taxable_value,
                    "igst": i.igst,
                    "cgst": i.cgst,
                    "sgst": i.sgst,
                    "cess": i.cess,
                    "total": i.total,
                },
                source_id=str(i.id),
            )

        out = reconcile(
            [to_domain(i) for i in purchase_orm],
            [to_domain(i) for i in gstr_orm],
        )
        for result in out.results:
            db.add(
                ReconciliationResult(
                    run_id=run.id,
                    purchase_invoice_id=UUID(result.purchase.source_id),
                    gstr_invoice_id=(
                        UUID(result.gstr.source_id) if result.gstr and result.gstr.source_id else None
                    ),
                    match_status=result.match_status,
                    match_score=result.match_score,
                    difference_amount=result.difference_amount,
                    difference_type=result.difference_type,
                )
            )

        groups = group_exceptions(out.results)
        run.status = "ai_enriching"
        db.commit()
        try:
            from app.ai.enrich import enrich_findings_from_groups

            enrich_findings_from_groups(db, run, groups)
            out.summary["ai_incomplete"] = False
        except Exception:
            enrich_findings_stub(db, run, groups)
            out.summary["ai_incomplete"] = True
        run.summary = out.summary
        run.status = "needs_review"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run
    except HTTPException:
        raise
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Reconciliation failed: {exc}") from exc
