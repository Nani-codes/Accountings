from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas.tally import PairingOut, TallyStatusOut
from app.services import auth as auth_service
from app.services.tally_pairing import (
    connection_status_for_org,
    create_pairing_code,
    disconnect_org,
)

router = APIRouter(prefix="/tally", tags=["tally"])


def _get_live_session(organization_id):
    """Stub for Task 3 — returns None for now."""
    return None


@router.post("/pairing", response_model=PairingOut)
def create_pairing(
    user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    code, expires = create_pairing_code(db, user.organization_id)
    db.commit()
    return PairingOut(
        code=code,
        expires_at=expires.isoformat(),
        download_url=settings.tally_connector_download_url or None,
    )


@router.get("/status", response_model=TallyStatusOut)
def tally_status(
    user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    live = _get_live_session(user.organization_id)
    return TallyStatusOut(**connection_status_for_org(db, user.organization_id, live_session=live))


@router.post("/disconnect")
def tally_disconnect(
    user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    disconnect_org(db, user.organization_id)
    db.commit()
    return {"ok": True}
