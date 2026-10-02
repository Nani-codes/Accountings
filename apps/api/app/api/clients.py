from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, ReconciliationRun, User
from app.schemas.clients import ClientCreate, ClientOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/clients", tags=["clients"])

ACTIVE_STATUSES = ("parsing", "reconciling", "ai_enriching", "needs_review")


def _latest_run_status(db: Session, client_id: UUID) -> str | None:
    run = (
        db.query(ReconciliationRun)
        .filter(ReconciliationRun.client_id == client_id)
        .order_by(ReconciliationRun.created_at.desc())
        .first()
    )
    return run.status if run else None


def _to_out(db: Session, client: Client) -> ClientOut:
    return ClientOut(
        id=str(client.id),
        name=client.name,
        gstin=client.gstin,
        services=list(client.services or ["GST"]),
        gst_review_status=_latest_run_status(db, client.id),
    )


@router.get("", response_model=list[ClientOut])
def list_clients(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ClientOut]:
    rows = (
        db.query(Client)
        .filter(Client.organization_id == user.organization_id)
        .order_by(Client.name.asc())
        .all()
    )
    return [_to_out(db, c) for c in rows]


@router.post("", response_model=ClientOut, status_code=201)
def create_client(
    body: ClientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClientOut:
    client = Client(
        organization_id=user.organization_id,
        name=body.name,
        gstin=body.gstin,
        services=body.services or ["GST"],
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return _to_out(db, client)


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClientOut:
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.organization_id == user.organization_id)
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return _to_out(db, client)
