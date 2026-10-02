from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AiFinding, AuditLog


def write_audit(
    db: Session,
    *,
    organization_id: UUID,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    payload: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
    )


def finding_accept_edit_rate(db: Session, organization_id: UUID) -> float | None:
    from app.models import ReconciliationRun

    rows = (
        db.query(AiFinding)
        .join(ReconciliationRun, AiFinding.run_id == ReconciliationRun.id)
        .filter(ReconciliationRun.organization_id == organization_id)
        .all()
    )
    if not rows:
        return None
    good = sum(1 for f in rows if f.status in ("accepted", "edited"))
    decided = sum(1 for f in rows if f.status != "pending")
    if decided == 0:
        return None
    return good / decided
