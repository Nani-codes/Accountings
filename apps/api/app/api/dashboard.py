from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AiFinding, Client, ClientRequest, ReconciliationRun, User
from app.schemas.clients import ActivityItem, DashboardOut
from app.services.auth import get_current_user

router = APIRouter(tags=["dashboard"])

ACTIVE_STATUSES = ("parsing", "reconciling", "ai_enriching", "needs_review")


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardOut:
    org_id = user.organization_id
    clients_count = db.query(Client).filter(Client.organization_id == org_id).count()
    active = (
        db.query(ReconciliationRun)
        .filter(
            ReconciliationRun.organization_id == org_id,
            ReconciliationRun.status.in_(ACTIVE_STATUSES),
        )
        .count()
    )
    exceptions = (
        db.query(AiFinding)
        .join(ReconciliationRun, AiFinding.run_id == ReconciliationRun.id)
        .filter(
            ReconciliationRun.organization_id == org_id,
            AiFinding.status == "pending",
        )
        .count()
    )
    pending_responses = (
        db.query(ClientRequest)
        .join(Client, ClientRequest.client_id == Client.id)
        .filter(Client.organization_id == org_id, ClientRequest.status == "sent")
        .count()
    )
    recent_runs = (
        db.query(ReconciliationRun, Client)
        .join(Client, ReconciliationRun.client_id == Client.id)
        .filter(ReconciliationRun.organization_id == org_id)
        .order_by(ReconciliationRun.created_at.desc())
        .limit(10)
        .all()
    )
    activity = [
        ActivityItem(
            client_id=str(client.id),
            client_name=client.name,
            label=f"GST reconciliation — {run.status}",
            run_id=str(run.id),
        )
        for run, client in recent_runs
    ]
    return DashboardOut(
        clients=clients_count,
        active_gst_reviews=active,
        exceptions=exceptions,
        client_responses_pending=pending_responses,
        recent_activity=activity,
    )
