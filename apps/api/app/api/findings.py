from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AiFinding, ClientRequest, ReconciliationRun, User
from app.services.auth import get_current_user

router = APIRouter(tags=["findings"])

ALLOWED_FINDING = {"pending", "accepted", "edited", "dismissed"}
REQUEST_TRANSITIONS = {
    "draft": {"approved"},
    "approved": {"sent"},
    "sent": {"response_received", "resolved"},
    "response_received": {"resolved"},
}


class FindingOut(BaseModel):
    id: str
    run_id: str
    category: str
    severity: str
    title: str
    description: str
    evidence: dict
    recommended_action: str
    status: str


class FindingPatch(BaseModel):
    status: str
    title: str | None = None
    description: str | None = None
    recommended_action: str | None = None


class ClientRequestOut(BaseModel):
    id: str
    run_id: str
    finding_ids: list[str]
    body: str
    status: str
    response_note: str | None = None


class ClientRequestCreate(BaseModel):
    body: str | None = None


class ClientRequestPatch(BaseModel):
    status: str | None = None
    body: str | None = None
    response_note: str | None = None


def _finding_out(f: AiFinding) -> FindingOut:
    return FindingOut(
        id=str(f.id),
        run_id=str(f.run_id),
        category=f.category,
        severity=f.severity,
        title=f.title,
        description=f.description,
        evidence=f.evidence or {},
        recommended_action=f.recommended_action,
        status=f.status,
    )


def _maybe_mark_run_reviewed(db: Session, run: ReconciliationRun) -> None:
    pending = (
        db.query(AiFinding)
        .filter(AiFinding.run_id == run.id, AiFinding.status == "pending")
        .count()
    )
    if pending == 0:
        run.status = "reviewed"


@router.get("/runs/{run_id}/findings", response_model=list[FindingOut])
def list_findings(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[FindingOut]:
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
    rows = db.query(AiFinding).filter(AiFinding.run_id == run_id).all()
    return [_finding_out(f) for f in rows]


@router.patch("/findings/{finding_id}", response_model=FindingOut)
def patch_finding(
    finding_id: UUID,
    body: FindingPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FindingOut:
    finding = (
        db.query(AiFinding)
        .join(ReconciliationRun, AiFinding.run_id == ReconciliationRun.id)
        .filter(
            AiFinding.id == finding_id,
            ReconciliationRun.organization_id == user.organization_id,
        )
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    if body.status not in ALLOWED_FINDING:
        raise HTTPException(status_code=400, detail="Invalid status")

    text_changed = False
    if body.title is not None and body.title != finding.title:
        finding.title = body.title
        text_changed = True
    if body.description is not None and body.description != finding.description:
        finding.description = body.description
        text_changed = True
    if (
        body.recommended_action is not None
        and body.recommended_action != finding.recommended_action
    ):
        finding.recommended_action = body.recommended_action
        text_changed = True

    status = body.status
    if status == "accepted" and text_changed:
        status = "edited"
    finding.status = status
    db.flush()

    run = db.query(ReconciliationRun).filter(ReconciliationRun.id == finding.run_id).one()
    _maybe_mark_run_reviewed(db, run)
    db.commit()
    db.refresh(finding)
    return _finding_out(finding)


@router.post("/runs/{run_id}/client-requests", response_model=ClientRequestOut, status_code=201)
def create_client_request(
    run_id: UUID,
    body: ClientRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClientRequestOut:
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

    includable = (
        db.query(AiFinding)
        .filter(
            AiFinding.run_id == run_id,
            AiFinding.status.in_(("accepted", "edited")),
        )
        .all()
    )
    if not includable:
        raise HTTPException(
            status_code=400,
            detail="No accepted or edited findings available for client request",
        )

    lines = [f"• {f.title}" for f in includable]
    default_body = (
        "During our GST reconciliation we found items that need your confirmation:\n\n"
        + "\n".join(lines)
        + "\n\nPlease review and share corrected details/documents."
    )
    req = ClientRequest(
        client_id=run.client_id,
        run_id=run.id,
        finding_ids=[str(f.id) for f in includable],
        body=body.body or default_body,
        status="draft",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return ClientRequestOut(
        id=str(req.id),
        run_id=str(req.run_id),
        finding_ids=list(req.finding_ids),
        body=req.body,
        status=req.status,
        response_note=req.response_note,
    )


@router.patch("/client-requests/{request_id}", response_model=ClientRequestOut)
def patch_client_request(
    request_id: UUID,
    body: ClientRequestPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClientRequestOut:
    req = (
        db.query(ClientRequest)
        .join(ReconciliationRun, ClientRequest.run_id == ReconciliationRun.id)
        .filter(
            ClientRequest.id == request_id,
            ReconciliationRun.organization_id == user.organization_id,
        )
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Client request not found")
    if body.body is not None:
        req.body = body.body
    if body.response_note is not None:
        req.response_note = body.response_note
    if body.status is not None:
        allowed = REQUEST_TRANSITIONS.get(req.status, set())
        if body.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from {req.status} to {body.status}",
            )
        req.status = body.status
    db.commit()
    db.refresh(req)
    return ClientRequestOut(
        id=str(req.id),
        run_id=str(req.run_id),
        finding_ids=list(req.finding_ids),
        body=req.body,
        status=req.status,
        response_note=req.response_note,
    )
