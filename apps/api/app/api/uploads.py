from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, ClientDocument, ColumnMappingProfile, ReconciliationRun, User
from app.recon.templates import TEMPLATES
from app.services.auth import get_current_user
from app.services.storage import put_object

router = APIRouter(tags=["uploads"])

DOC_TYPES = {
    "purchase_register",
    "gstr2b",
    "sales_register",
    "previous_reconciliation",
    "bank_statement",
}


class RunCreate(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}$")


class RunOut(BaseModel):
    id: str
    client_id: str
    period: str
    status: str


class MappingProfileIn(BaseModel):
    mapping: dict[str, str]
    template_id: str | None = None


@router.get("/mapping/templates")
def list_templates() -> dict:
    return {"templates": TEMPLATES}


@router.put("/clients/{client_id}/mapping-profiles/{doc_type}")
def upsert_mapping_profile(
    client_id: UUID,
    doc_type: str,
    body: MappingProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.organization_id == user.organization_id)
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    profile = (
        db.query(ColumnMappingProfile)
        .filter(
            ColumnMappingProfile.client_id == client_id,
            ColumnMappingProfile.doc_type == doc_type,
        )
        .first()
    )
    if profile:
        profile.mapping = body.mapping
        profile.template_id = body.template_id
    else:
        profile = ColumnMappingProfile(
            client_id=client_id,
            doc_type=doc_type,
            mapping=body.mapping,
            template_id=body.template_id,
        )
        db.add(profile)
    db.commit()
    return {"client_id": str(client_id), "doc_type": doc_type, "mapping": profile.mapping}


@router.post("/clients/{client_id}/runs", response_model=RunOut, status_code=201)
def create_run(
    client_id: UUID,
    body: RunCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RunOut:
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.organization_id == user.organization_id)
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    run = ReconciliationRun(
        client_id=client.id,
        organization_id=user.organization_id,
        period=body.period,
        status="draft",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return RunOut(
        id=str(run.id),
        client_id=str(run.client_id),
        period=run.period,
        status=run.status,
    )


@router.post("/runs/{run_id}/documents", status_code=201)
async def upload_document(
    run_id: UUID,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if doc_type not in DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type: {doc_type}")
    run = (
        db.query(ReconciliationRun)
        .filter(
            ReconciliationRun.id == run_id,
            ReconciliationRun.organization_id == user.organization_id,
        )
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    data = await file.read()
    filename = file.filename or f"{doc_type}.bin"
    key = (
        f"org/{user.organization_id}/client/{run.client_id}/run/{run.id}/"
        f"{doc_type}/{uuid4().hex}_{filename}"
    )
    put_object(key, data, content_type=file.content_type or "application/octet-stream")

    parsed_stats = None
    if doc_type == "bank_statement":
        parsed_stats = {"stored_only": True}

    doc = ClientDocument(
        client_id=run.client_id,
        run_id=run.id,
        doc_type=doc_type,
        storage_key=key,
        filename=filename,
        parsed_stats=parsed_stats,
    )
    db.add(doc)
    if run.status == "draft":
        run.status = "uploading"
    db.commit()
    db.refresh(doc)
    return {
        "id": str(doc.id),
        "doc_type": doc.doc_type,
        "filename": doc.filename,
        "storage_key": doc.storage_key,
        "parsed_stats": doc.parsed_stats,
    }


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RunOut:
    run = (
        db.query(ReconciliationRun)
        .filter(
            ReconciliationRun.id == run_id,
            ReconciliationRun.organization_id == user.organization_id,
        )
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunOut(
        id=str(run.id),
        client_id=str(run.client_id),
        period=run.period,
        status=run.status,
    )


@router.post("/runs/{run_id}/start", response_model=RunOut)
def start_reconciliation(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RunOut:
    run = (
        db.query(ReconciliationRun)
        .filter(
            ReconciliationRun.id == run_id,
            ReconciliationRun.organization_id == user.organization_id,
        )
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    from app.services.run_pipeline import start_run

    started = start_run(db, run.id)
    return RunOut(
        id=str(started.id),
        client_id=str(started.client_id),
        period=started.period,
        status=started.status,
    )
