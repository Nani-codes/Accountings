import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas.tally import ConnectorPairIn, ConnectorPairOut, PairingOut, TallyStatusOut
from app.services import auth as auth_service
from app.services.tally_pairing import (
    connection_status_for_org,
    consume_pairing_code,
    create_pairing_code,
    disconnect_org,
    find_connection_by_device_token,
)
from app.services.tally_sessions import (
    LiveSession,
    drop_live_session,
    get_live_session,
    register_live_session,
)

router = APIRouter(prefix="/tally", tags=["tally"])


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
    live = get_live_session(user.organization_id)
    return TallyStatusOut(**connection_status_for_org(db, user.organization_id, live_session=live))


@router.post("/disconnect")
def tally_disconnect(
    user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    disconnect_org(db, user.organization_id)
    db.commit()
    drop_live_session(user.organization_id)
    return {"ok": True}


@router.post("/connector/pair", response_model=ConnectorPairOut)
def connector_pair(body: ConnectorPairIn, db: Session = Depends(get_db)):
    try:
        conn, token = consume_pairing_code(db, body.code, label=body.label)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Public WS path relative to API origin
    return ConnectorPairOut(
        device_id=str(conn.device_id),
        device_token=token,
        ws_url="/tally/connector/ws",
    )


@router.websocket("/connector/ws")
async def connector_ws(websocket: WebSocket, db: Session = Depends(get_db)):
    auth = websocket.headers.get("authorization") or ""
    token = auth.removeprefix("Bearer ").strip()
    conn = find_connection_by_device_token(db, token)
    if conn is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    org_id = conn.organization_id
    session = LiveSession(organization_id=org_id)

    async def send_json(payload: dict):
        await websocket.send_text(json.dumps(payload))

    session.send_json = send_json
    register_live_session(org_id, session)
    try:
        while True:
            text = await websocket.receive_text()
            msg = json.loads(text)
            mtype = msg.get("type")
            if mtype == "heartbeat":
                session.tally_ok = bool(msg.get("tally_ok"))
                conn.last_seen_at = datetime.now(timezone.utc)
                if session.tally_ok:
                    conn.last_tally_ok_at = conn.last_seen_at
                db.add(conn)
                db.commit()
            elif mtype == "response":
                session.resolve_response(str(msg.get("id")), msg)
    except WebSocketDisconnect:
        pass
    finally:
        drop_live_session(org_id)
