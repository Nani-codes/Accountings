# TallyPrime Hosted Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a CA firm pair a Windows connector to TallyPrime so Advisor can answer read-only book questions via org-scoped `TallyTools` (no firm-hosted MCP).

**Architecture:** Cloud FastAPI owns pairing, device auth, WebSocket relay, and a whitelisted Tally gateway. A Windows connector dials out over WSS and proxies named ops to local Tally XML (`:9000`). Advisor uses `TallyTools` (same org-resolution pattern as `WorkbenchTools`). Remove env-based firm MCP wiring.

**Tech Stack:** FastAPI, SQLAlchemy + Alembic, Agno Toolkit, Next.js 15, Python connector (`httpx` + `websockets`), TallyPrime XML HTTP.

**Spec:** `docs/superpowers/specs/2026-10-03-tallyprime-hosted-connector-design.md`

## Global Constraints

- Read-only only — never send write/import/alter Tally XML.
- LLM never sends raw XML — named tools with structured args only.
- Every relay hop bound to `organization_id` from the authenticated connector session.
- One primary device per org in v1.
- Pairing codes ~15 minutes, single-use; store only hashes of codes and device tokens.
- API paths follow existing routers (`/tally/...`), not a new `/api` prefix.
- Connector OS v1: Windows; default Tally `127.0.0.1:9000`.
- Recon/uploads remain the source of truth; Tally is Advisor lookups only.
- Worktree: `.worktrees/ai-gst-mvp` on branch `feature/ai-gst-mvp`.
- Tests: `cd apps/api && uv run pytest …`

---

## File map

| Path | Responsibility |
| --- | --- |
| `apps/api/app/models/__init__.py` | Add `TallyConnection`, `TallyPairingCode` |
| `apps/api/alembic/versions/*_tally_connector.py` | Migration |
| `apps/api/app/config.py` | Replace `TALLY_MCP_*` with connector settings |
| `apps/api/app/services/tally_crypto.py` | Hash/verify pairing codes + device tokens |
| `apps/api/app/services/tally_pairing.py` | Create/consume pairing; disconnect; status |
| `apps/api/app/services/tally_sessions.py` | In-process live connector session registry + RPC |
| `apps/api/app/services/tally_gateway.py` | Whitelist ops; build XML; parse to JSON (or pass through connector-parsed JSON) |
| `apps/api/app/schemas/tally.py` | Pydantic request/response models |
| `apps/api/app/api/tally.py` | CA + connector HTTP/WS routes |
| `apps/api/app/ai/tally_tools.py` | `TallyTools` Toolkit |
| `apps/api/app/ai/agents.py` | Update CA Advisor instructions |
| `apps/api/app/main.py` | Mount router; register `TallyTools`; drop firm MCP |
| Delete `apps/api/app/ai/tally_mcp.py`, `apps/api/tests/test_tally_mcp.py` | Remove firm-MCP path |
| `apps/web/src/app/(app)/settings/tally/page.tsx` | Settings → Tally UI |
| `apps/web/src/lib/api.ts` | Client helpers |
| `apps/web/src/app/(app)/layout.tsx` | Nav link to Settings |
| `apps/tally-connector/` | Windows connector (Python) |
| `.env.example`, `README.md` | Docs |

---

### Task 1: Models, migration, crypto helpers

**Files:**
- Modify: `apps/api/app/models/__init__.py`
- Create: `apps/api/alembic/versions/<rev>_tally_connector.py` (generate via alembic)
- Create: `apps/api/app/services/tally_crypto.py`
- Modify: `apps/api/app/config.py` (add `tally_token_pepper`, `tally_connector_download_url`; remove `tally_mcp_*`)
- Test: `apps/api/tests/test_tally_crypto.py`

**Interfaces:**
- Produces: `TallyConnection`, `TallyPairingCode` models; `hash_secret(raw: str) -> str`; `secrets_equal(raw: str, digest: str) -> bool`; settings `tally_token_pepper: str`, `tally_connector_download_url: str`

- [ ] **Step 1: Write failing crypto tests**

```python
# apps/api/tests/test_tally_crypto.py
from app.services.tally_crypto import hash_secret, secrets_equal


def test_hash_secret_stable(monkeypatch):
    monkeypatch.setenv("TALLY_TOKEN_PEPPER", "test-pepper")
    from app.config import Settings
    import app.services.tally_crypto as crypto
    crypto.settings = Settings(_env_file=None)
    a = hash_secret("abc-123")
    b = hash_secret("abc-123")
    assert a == b
    assert a != "abc-123"
    assert secrets_equal("abc-123", a) is True
    assert secrets_equal("wrong", a) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/test_tally_crypto.py -v`  
Expected: FAIL (module missing)

- [ ] **Step 3: Implement crypto + settings**

```python
# apps/api/app/services/tally_crypto.py
from __future__ import annotations
import hashlib
import hmac
from app.config import settings

def hash_secret(raw: str) -> str:
    msg = f"{settings.tally_token_pepper}:{raw}".encode("utf-8")
    return hashlib.sha256(msg).hexdigest()

def secrets_equal(raw: str, digest: str) -> bool:
    return hmac.compare_digest(hash_secret(raw), digest)
```

In `config.py`: remove `tally_mcp_enabled`, `tally_mcp_transport`, `tally_mcp_url`, `tally_mcp_command`, `tally_mcp_auth_token` and their validator. Add:

```python
tally_token_pepper: str = "dev-tally-pepper-change-me"
tally_connector_download_url: str = ""  # optional; UI can show “coming soon” if empty
tally_heartbeat_stale_seconds: int = 60
tally_rpc_timeout_seconds: float = 25.0
```

- [ ] **Step 4: Add models**

Append to `apps/api/app/models/__init__.py`:

```python
class TallyConnection(Base):
    __tablename__ = "tally_connections"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[uuid.UUID] = mapped_column(UuidType, nullable=False, unique=True, default=_uuid)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="paired")  # paired|revoked
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_tally_ok_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tally_host: Mapped[str] = mapped_column(String(255), nullable=False, default="127.0.0.1")
    tally_port: Mapped[int] = mapped_column(nullable=False, default=9000)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TallyPairingCode(Base):
    __tablename__ = "tally_pairing_codes"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

Use `sa.Integer` for `tally_port` if needed — import `Integer` from sqlalchemy.

- [ ] **Step 5: Alembic migration**

Run: `cd apps/api && uv run alembic revision --autogenerate -m "tally_connector"`  
Review then: `uv run alembic upgrade head`

- [ ] **Step 6: Run crypto tests**

Run: `cd apps/api && uv run pytest tests/test_tally_crypto.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/models/__init__.py apps/api/app/config.py \
  apps/api/app/services/tally_crypto.py apps/api/tests/test_tally_crypto.py \
  apps/api/alembic/versions/*tally_connector*.py
git commit -m "feat(tally): add connection models and token hashing"
```

---

### Task 2: Pairing service + CA HTTP API

**Files:**
- Create: `apps/api/app/services/tally_pairing.py`
- Create: `apps/api/app/schemas/tally.py`
- Create: `apps/api/app/api/tally.py` (CA routes only for now)
- Modify: `apps/api/app/main.py` (include router)
- Test: `apps/api/tests/test_tally_pairing.py`

**Interfaces:**
- Consumes: `TallyConnection`, `TallyPairingCode`, `hash_secret`, `secrets_equal`, `settings.tally_connector_download_url`
- Produces:
  - `create_pairing_code(db, org_id) -> tuple[str, datetime]`  # plaintext code, expires_at
  - `consume_pairing_code(db, code, *, label=None) -> tuple[TallyConnection, str]`  # connection, plaintext device_token
  - `disconnect_org(db, org_id) -> None`
  - `connection_status_for_org(db, org_id, *, live_session) -> dict`  # used fully in Task 3; for now pass `live_session=None`
  - Routes: `POST /tally/pairing`, `GET /tally/status`, `POST /tally/disconnect`

- [ ] **Step 1: Write failing pairing tests**

```python
# apps/api/tests/test_tally_pairing.py
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Organization, TallyConnection, TallyPairingCode
from app.services.tally_pairing import (
    create_pairing_code,
    consume_pairing_code,
    disconnect_org,
    connection_status_for_org,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


def test_create_and_consume_pairing(db, monkeypatch):
    monkeypatch.setenv("TALLY_TOKEN_PEPPER", "test-pepper")
    from app.config import Settings
    import app.services.tally_crypto as crypto
    import app.services.tally_pairing as pairing
    crypto.settings = Settings(_env_file=None)
    pairing.settings = Settings(_env_file=None)

    org = Organization(name="Firm")
    db.add(org)
    db.flush()
    code, expires = create_pairing_code(db, org.id)
    db.commit()
    assert len(code) >= 6
    assert expires > datetime.now(timezone.utc)

    conn, token = consume_pairing_code(db, code, label="desk-pc")
    db.commit()
    assert conn.organization_id == org.id
    assert conn.status == "paired"
    assert token
    assert connection_status_for_org(db, org.id, live_session=None)["status"] == "offline"

    disconnect_org(db, org.id)
    db.commit()
    assert connection_status_for_org(db, org.id, live_session=None)["status"] == "not_connected"


def test_expired_code_rejected(db, monkeypatch):
    monkeypatch.setenv("TALLY_TOKEN_PEPPER", "test-pepper")
    from app.config import Settings
    import app.services.tally_crypto as crypto
    import app.services.tally_pairing as pairing
    crypto.settings = Settings(_env_file=None)
    pairing.settings = Settings(_env_file=None)

    org = Organization(name="Firm")
    db.add(org)
    db.flush()
    code, _ = create_pairing_code(db, org.id)
    row = db.query(TallyPairingCode).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    with pytest.raises(ValueError, match="expired|invalid"):
        consume_pairing_code(db, code)
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `cd apps/api && uv run pytest tests/test_tally_pairing.py -v`  
Expected: FAIL (import / missing functions)

- [ ] **Step 3: Implement pairing service**

```python
# apps/api/app/services/tally_pairing.py
from __future__ import annotations
import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models import TallyConnection, TallyPairingCode
from app.services.tally_crypto import hash_secret, secrets_equal

PAIRING_TTL = timedelta(minutes=15)
CODE_ALPHABET = string.ascii_uppercase + string.digits


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_code(n: int = 8) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(n))


def create_pairing_code(db: Session, organization_id: UUID) -> tuple[str, datetime]:
    for _ in range(8):
        code = _generate_code()
        digest = hash_secret(code)
        if db.query(TallyPairingCode).filter(TallyPairingCode.code_hash == digest).first():
            continue
        expires = _now() + PAIRING_TTL
        db.add(
            TallyPairingCode(
                organization_id=organization_id,
                code_hash=digest,
                expires_at=expires,
            )
        )
        db.flush()
        return code, expires
    raise RuntimeError("could not allocate pairing code")


def consume_pairing_code(
    db: Session, code: str, *, label: str | None = None
) -> tuple[TallyConnection, str]:
    raw = (code or "").strip().upper()
    if not raw:
        raise ValueError("invalid pairing code")
    digest = hash_secret(raw)
    row = (
        db.query(TallyPairingCode)
        .filter(TallyPairingCode.code_hash == digest)
        .one_or_none()
    )
    if row is None or row.consumed_at is not None:
        raise ValueError("invalid pairing code")
    if row.expires_at < _now():
        raise ValueError("pairing code expired")
    row.consumed_at = _now()
    # Revoke any existing paired connection for org (replace device)
    existing = (
        db.query(TallyConnection)
        .filter(
            TallyConnection.organization_id == row.organization_id,
            TallyConnection.status == "paired",
        )
        .all()
    )
    for c in existing:
        c.status = "revoked"
        c.revoked_at = _now()
    device_token = secrets.token_urlsafe(32)
    conn = TallyConnection(
        organization_id=row.organization_id,
        token_hash=hash_secret(device_token),
        label=label,
        status="paired",
    )
    db.add(conn)
    db.flush()
    return conn, device_token


def disconnect_org(db: Session, organization_id: UUID) -> None:
    rows = (
        db.query(TallyConnection)
        .filter(
            TallyConnection.organization_id == organization_id,
            TallyConnection.status == "paired",
        )
        .all()
    )
    for c in rows:
        c.status = "revoked"
        c.revoked_at = _now()
    db.flush()


def connection_status_for_org(
    db: Session, organization_id: UUID, *, live_session
) -> dict:
    conn = (
        db.query(TallyConnection)
        .filter(
            TallyConnection.organization_id == organization_id,
            TallyConnection.status == "paired",
        )
        .order_by(TallyConnection.created_at.desc())
        .first()
    )
    if conn is None:
        return {"status": "not_connected"}
    base = {
        "device_label": conn.label,
        "last_seen_at": conn.last_seen_at.isoformat() if conn.last_seen_at else None,
        "last_tally_ok_at": conn.last_tally_ok_at.isoformat()
        if conn.last_tally_ok_at
        else None,
    }
    if live_session is None:
        return {"status": "offline", **base}
    if not getattr(live_session, "tally_ok", False):
        return {"status": "tally_unreachable", **base}
    return {"status": "online", **base}


def find_connection_by_device_token(db: Session, token: str) -> TallyConnection | None:
    raw = (token or "").strip()
    if not raw:
        return None
    rows = (
        db.query(TallyConnection)
        .filter(TallyConnection.status == "paired")
        .all()
    )
    for row in rows:
        if secrets_equal(raw, row.token_hash):
            return row
    return None
```

Note: `find_connection_by_device_token` scanning all paired rows is fine for MVP firm count; optimize later with token prefix index if needed.

- [ ] **Step 4: Schemas + CA routes**

```python
# apps/api/app/schemas/tally.py
from pydantic import BaseModel

class PairingOut(BaseModel):
    code: str
    expires_at: str
    download_url: str | None = None

class TallyStatusOut(BaseModel):
    status: str
    device_label: str | None = None
    last_seen_at: str | None = None
    last_tally_ok_at: str | None = None

class ConnectorPairIn(BaseModel):
    code: str
    label: str | None = None

class ConnectorPairOut(BaseModel):
    device_id: str
    device_token: str
    ws_url: str
```

```python
# apps/api/app/api/tally.py
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
from app.services.tally_sessions import get_live_session  # stub in Task 3 if needed

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
    # Task 3 will also drop live session
    return {"ok": True}
```

For Task 2 only, if `tally_sessions` does not exist yet, add a tiny stub:

```python
# apps/api/app/services/tally_sessions.py
from uuid import UUID

def get_live_session(organization_id: UUID):
    return None

def drop_live_session(organization_id: UUID) -> None:
    return None
```

Wire in `main.py`: `from app.api.tally import router as tally_router` and `app.include_router(tally_router)`.

- [ ] **Step 5: Run pairing tests**

Run: `cd apps/api && uv run pytest tests/test_tally_pairing.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/services/tally_pairing.py apps/api/app/services/tally_sessions.py \
  apps/api/app/schemas/tally.py apps/api/app/api/tally.py apps/api/app/main.py \
  apps/api/tests/test_tally_pairing.py
git commit -m "feat(tally): pairing, status, and disconnect API"
```

---

### Task 3: Live session registry + connector pair + WebSocket relay

**Files:**
- Modify: `apps/api/app/services/tally_sessions.py`
- Modify: `apps/api/app/api/tally.py` (add pair + WS)
- Modify: `apps/api/app/services/tally_pairing.py` (optional: call `drop_live_session` from disconnect route)
- Test: `apps/api/tests/test_tally_sessions.py`

**Interfaces:**
- Produces:
  - `class LiveSession` with `organization_id`, `tally_ok: bool`, `async def rpc(op: str, args: dict) -> dict`
  - `register_live_session(org_id, session)`, `get_live_session(org_id)`, `drop_live_session(org_id)`
  - `POST /tally/connector/pair` → `ConnectorPairOut`
  - `WS /tally/connector/ws` with `Authorization: Bearer <device_token>`

- [ ] **Step 1: Write session registry tests**

```python
# apps/api/tests/test_tally_sessions.py
import asyncio
from uuid import uuid4
from app.services.tally_sessions import (
    LiveSession,
    register_live_session,
    get_live_session,
    drop_live_session,
)


def test_register_and_get():
    org = uuid4()
    drop_live_session(org)
    assert get_live_session(org) is None
    sess = LiveSession(organization_id=org)
    sess.tally_ok = True
    register_live_session(org, sess)
    assert get_live_session(org) is sess
    drop_live_session(org)
    assert get_live_session(org) is None


def test_rpc_resolves_response():
    org = uuid4()
    sess = LiveSession(organization_id=org)
    register_live_session(org, sess)

    async def _run():
        async def responder():
            await asyncio.sleep(0.01)
            # pick pending id
            req_id = next(iter(sess._pending.keys()))
            sess.resolve_response(req_id, {"ok": True, "data": {"balance": "100"}})

        task = asyncio.create_task(responder())
        result = await sess.rpc("ledger_balance", {"ledger": "Cash"}, timeout=2.0)
        await task
        return result

    out = asyncio.get_event_loop().run_until_complete(_run())
    assert out["balance"] == "100"
    drop_live_session(org)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd apps/api && uv run pytest tests/test_tally_sessions.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement session registry**

```python
# apps/api/app/services/tally_sessions.py
from __future__ import annotations
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from uuid import UUID

_sessions: dict[UUID, "LiveSession"] = {}


@dataclass
class LiveSession:
    organization_id: UUID
    tally_ok: bool = False
    send_json: Callable[[dict], Awaitable[None]] | None = None
    _pending: dict[str, asyncio.Future] = field(default_factory=dict)

    async def rpc(self, op: str, args: dict, timeout: float = 25.0) -> dict[str, Any]:
        if self.send_json is None:
            raise RuntimeError("connector not connected")
        req_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[req_id] = fut
        try:
            await self.send_json(
                {"type": "request", "id": req_id, "op": op, "args": args or {}}
            )
            raw = await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending.pop(req_id, None)
        if not raw.get("ok", False):
            raise RuntimeError(raw.get("error") or "tally request failed")
        return raw.get("data") or {}

    def resolve_response(self, req_id: str, payload: dict) -> None:
        fut = self._pending.get(req_id)
        if fut and not fut.done():
            fut.set_result(payload)


def register_live_session(organization_id: UUID, session: LiveSession) -> None:
    _sessions[organization_id] = session


def get_live_session(organization_id: UUID) -> LiveSession | None:
    return _sessions.get(organization_id)


def drop_live_session(organization_id: UUID) -> None:
    _sessions.pop(organization_id, None)
```

- [ ] **Step 4: Connector pair + WebSocket endpoints**

Add to `apps/api/app/api/tally.py`:

```python
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect, Header
from app.schemas.tally import ConnectorPairIn, ConnectorPairOut
from app.services.tally_pairing import consume_pairing_code, find_connection_by_device_token
from app.services.tally_sessions import LiveSession, register_live_session, drop_live_session
from app.services.tally_gateway import assert_op_allowed  # Task 4 — stub whitelist for now
import json

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
```

Also call `drop_live_session(user.organization_id)` inside `tally_disconnect`.

For `assert_op_allowed`: until Task 4, either omit from WS (ops validated when sending RPC from tools) or add:

```python
# temporary in tally_gateway.py
ALLOWED_OPS = {"list_companies", "ledger_balance", "day_book", "trial_balance", "probe"}

def assert_op_allowed(op: str) -> None:
    if op not in ALLOWED_OPS:
        raise ValueError(f"op not allowed: {op}")
```

- [ ] **Step 5: Fix asyncio test if needed**

Prefer `asyncio.run(_run())` instead of `get_event_loop().run_until_complete` on Python 3.12+.

- [ ] **Step 6: Run tests**

Run: `cd apps/api && uv run pytest tests/test_tally_sessions.py tests/test_tally_pairing.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/services/tally_sessions.py apps/api/app/api/tally.py \
  apps/api/app/services/tally_gateway.py apps/api/tests/test_tally_sessions.py
git commit -m "feat(tally): connector pairing and WebSocket relay"
```

---

### Task 4: Read-only Tally gateway (whitelist + XML)

**Files:**
- Modify: `apps/api/app/services/tally_gateway.py`
- Test: `apps/api/tests/test_tally_gateway.py`

**Interfaces:**
- Produces:
  - `ALLOWED_OPS: set[str]`
  - `assert_op_allowed(op: str) -> None`
  - `build_tally_xml(op: str, args: dict) -> str`  # XML body for connector to POST
  - `parse_tally_xml(op: str, xml_text: str) -> dict`  # best-effort parse; connector may also return pre-parsed JSON

Design choice for v1: **cloud builds XML; connector POSTs it to Tally and returns raw XML; cloud parses**. That keeps Tally XML knowledge server-side.

- [ ] **Step 1: Failing tests**

```python
# apps/api/tests/test_tally_gateway.py
import pytest
from app.services.tally_gateway import assert_op_allowed, build_tally_xml, parse_tally_xml


def test_rejects_write_ops():
    with pytest.raises(ValueError):
        assert_op_allowed("import_voucher")
    with pytest.raises(ValueError):
        build_tally_xml("alter_ledger", {})


def test_build_ledger_balance_contains_ledger_name():
    xml = build_tally_xml("ledger_balance", {"ledger": "Cash", "from": "20260401", "to": "20260430"})
    assert "Cash" in xml
    assert "IMPORT" not in xml.upper() or "IMPORT DATA" not in xml.upper()
```

(Adjust the IMPORT assertion to whatever write markers you use — goal is read export requests only.)

- [ ] **Step 2: Run — expect FAIL / incomplete**

- [ ] **Step 3: Implement whitelist + minimal XML templates**

Implement at least:

| op | args | Tally request intent |
| --- | --- | --- |
| `probe` | `{}` | lightweight company info / empty export |
| `list_companies` | `{}` | list companies |
| `ledger_balance` | `ledger`, optional `from`,`to` | ledger VCH / balance report |
| `day_book` | `from`, `to` | day book |
| `trial_balance` | `from`, `to` | trial balance |

Use standard Tally XML `<ENVELOPE>…` export requests. Keep parsers lenient: if parse is hard, return `{"raw_xml_truncated": xml_text[:4000]}` so Advisor still has something — improve parsers iteratively. Prefer extracting obvious fields when possible.

- [ ] **Step 4: Run tests PASS**

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/services/tally_gateway.py apps/api/tests/test_tally_gateway.py
git commit -m "feat(tally): read-only XML gateway whitelist"
```

---

### Task 5: `TallyTools` + Advisor wiring; remove firm MCP

**Files:**
- Create: `apps/api/app/ai/tally_tools.py`
- Modify: `apps/api/app/ai/agents.py` (instructions)
- Modify: `apps/api/app/main.py` (register tools; remove `build_tally_mcp_tools`)
- Delete: `apps/api/app/ai/tally_mcp.py`, `apps/api/tests/test_tally_mcp.py`
- Modify: `.env.example`, `README.md`
- Test: `apps/api/tests/test_tally_tools.py`

**Interfaces:**
- Consumes: `get_request_org_id`, `SessionLocal`, `get_live_session`, `connection_status_for_org`, `assert_op_allowed`, `settings.tally_rpc_timeout_seconds`
- Produces: `class TallyTools(Toolkit)` with tools:
  - `tally_connection_status`
  - `tally_list_companies`
  - `tally_ledger_balance`
  - `tally_day_book`
  - `tally_trial_balance`

- [ ] **Step 1: Failing tool tests**

```python
# apps/api/tests/test_tally_tools.py
import json
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Organization, TallyConnection
from app.ai.tally_tools import TallyTools
from app.services.tally_crypto import hash_secret
from app.services.tally_sessions import LiveSession, register_live_session, drop_live_session


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


def test_status_not_connected(db, monkeypatch):
    monkeypatch.setenv("TALLY_TOKEN_PEPPER", "test-pepper")
    from app.config import Settings
    import app.services.tally_crypto as crypto
    crypto.settings = Settings(_env_file=None)
    org = Organization(name="F")
    db.add(org)
    db.flush()
    tools = TallyTools(db=db, organization_id=org.id)
    out = json.loads(tools.tally_connection_status())
    assert out["status"] == "not_connected"


def test_ledger_balance_via_fake_session(db, monkeypatch):
    monkeypatch.setenv("TALLY_TOKEN_PEPPER", "test-pepper")
    from app.config import Settings
    import app.services.tally_crypto as crypto
    crypto.settings = Settings(_env_file=None)
    org = Organization(name="F")
    db.add(org)
    db.flush()
    db.add(
        TallyConnection(
            organization_id=org.id,
            token_hash=hash_secret("tok"),
            status="paired",
            label="pc",
        )
    )
    db.flush()
    sess = LiveSession(organization_id=org.id, tally_ok=True)

    async def fake_rpc(op, args, timeout=25.0):
        assert op == "ledger_balance"
        return {"ledger": args["ledger"], "balance": "1234.00"}

    sess.rpc = fake_rpc  # type: ignore
    register_live_session(org.id, sess)
    tools = TallyTools(db=db, organization_id=org.id)
    out = json.loads(tools.tally_ledger_balance(ledger="Cash"))
    assert out["balance"] == "1234.00"
    drop_live_session(org.id)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `TallyTools`**

Mirror `WorkbenchTools` session/org pattern. For async `rpc`, use a small helper:

```python
import asyncio

def _run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # If already in a loop (AgentOS), create a task and wait via nest — prefer:
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
```

Return JSON strings with actionable errors:

- not connected / offline / tally_unreachable messages matching the spec
- never include UUIDs, device tokens, or connection ids

- [ ] **Step 4: Wire Advisor**

In `main.py`:

```python
from app.ai.tally_tools import TallyTools
# remove tally_mcp imports
advisor_tools: list = [
    WorkbenchTools(),
    WebSearchTools(enable_news=False, fixed_max_results=5),
    TallyTools(),
]
```

Update `CA_ADVISOR_INSTRUCTIONS` — replace MCP paragraph with:

```text
When the user asks about live Tally books (ledgers, day book, trial balance), call the tally_* tools.
If tally_connection_status is not online, tell the CA to open Settings → Tally and start the Accountings Connector on the firm PC — never invent book figures.
Never show device tokens, connection ids, or internal UUIDs.
```

Remove `/health` `tally_mcp` block; optionally report nothing or a simple `"tally_connector": "enabled"`.

Delete `tally_mcp.py` and `test_tally_mcp.py`. Update `.env.example` / `README.md` for connector flow.

- [ ] **Step 5: Run tests**

Run: `cd apps/api && uv run pytest tests/test_tally_tools.py tests/test_tally_pairing.py tests/test_chat.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/ai/tally_tools.py apps/api/app/ai/agents.py apps/api/app/main.py \
  apps/api/tests/test_tally_tools.py apps/api/app/config.py .env.example README.md
git rm -f apps/api/app/ai/tally_mcp.py apps/api/tests/test_tally_mcp.py
git commit -m "feat(tally): Advisor TallyTools and remove firm MCP wiring"
```

---

### Task 6: Settings → Tally UI

**Files:**
- Create: `apps/web/src/app/(app)/settings/tally/page.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/(app)/layout.tsx` (add Settings nav + crumbs)

**Interfaces:**
- Consumes: `POST /tally/pairing`, `GET /tally/status`, `POST /tally/disconnect`
- Produces: page showing status, Connect (shows code + download), Disconnect; poll status every 5s while code visible

- [ ] **Step 1: Add API helpers**

```typescript
// in apps/web/src/lib/api.ts
export type TallyStatus = {
  status: "not_connected" | "offline" | "online" | "tally_unreachable" | string;
  device_label?: string | null;
  last_seen_at?: string | null;
  last_tally_ok_at?: string | null;
};

export async function getTallyStatus(): Promise<TallyStatus> {
  return api("/tally/status");
}

export async function createTallyPairing(): Promise<{
  code: string;
  expires_at: string;
  download_url?: string | null;
}> {
  return api("/tally/pairing", { method: "POST" });
}

export async function disconnectTally(): Promise<void> {
  await api("/tally/disconnect", { method: "POST" });
}
```

- [ ] **Step 2: Build page**

Create `apps/web/src/app/(app)/settings/tally/page.tsx` as a client page:

- Load status on mount
- Primary actions: **Connect Tally** → show large pairing code + copy button + download link (or “Download link coming soon” if null)
- **Disconnect** when paired/online/offline
- Status badge copy:
  - `not_connected` → Not connected
  - `offline` → Connector offline — open Accountings Connector on the firm PC
  - `online` → Online
  - `tally_unreachable` → Connector online, but TallyPrime XML port not reachable
- Match Tripundra void Operate styles (`bg-void`, `border-line`, existing button classes)
- One job: connect Tally — no cards clutter beyond status + actions

- [ ] **Step 3: Nav**

Add `{ href: "/settings/tally", label: "Settings" }` to `NAV` (or nest under Settings if you prefer a settings index later — v1 can link directly to Tally).

Update `crumbs()` for `/settings`.

- [ ] **Step 4: Manual smoke**

With API running: open Settings → Connect → see code; call pair via curl with that code; confirm status flips after connecting a fake WS (or wait for Task 7).

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/\(app\)/settings/tally/page.tsx apps/web/src/lib/api.ts \
  apps/web/src/app/\(app\)/layout.tsx
git commit -m "feat(web): Settings → Tally connect UI"
```

---

### Task 7: Windows connector app

**Files:**
- Create: `apps/tally-connector/README.md`
- Create: `apps/tally-connector/pyproject.toml`
- Create: `apps/tally-connector/connector/main.py`
- Create: `apps/tally-connector/connector/tally_client.py`

**Interfaces:**
- Consumes: `POST {API}/tally/connector/pair`, `WS {API}/tally/connector/ws`, local Tally HTTP
- Produces: CLI that stores device token in a local file, heartbeats, handles `request` frames by POSTing XML from cloud…  

**Simplified connector protocol for v1 (recommended):**

Cloud `rpc` sends `{type,id,op,args}`. Connector:

1. Calls cloud helper **or** builds XML locally using the same op names via duplicated minimal templates — **prefer:** include `xml` in the request frame from the gateway when sending RPC.

Update Task 3/5 `LiveSession.rpc` path: before send, `xml = build_tally_xml(op, args)` and send `{"type":"request","id","op","args","xml"}`. Connector POSTs `xml` to `http://{host}:{port}` and returns `{type:"response","id","ok", "data": {"raw_xml": ...}}` or parsed. Cloud `TallyTools` then `parse_tally_xml(op, raw)`.

- [ ] **Step 1: Implement local Tally client**

```python
# apps/tally-connector/connector/tally_client.py
import httpx

def probe(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        r = httpx.get(f"http://{host}:{port}", timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False

def post_xml(host: str, port: int, xml: str, timeout: float = 20.0) -> str:
    r = httpx.post(
        f"http://{host}:{port}",
        content=xml.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.text
```

- [ ] **Step 2: Implement connector main loop**

CLI args / env:

- `ACCOUNTINGS_API_URL` (e.g. `http://127.0.0.1:8000`)
- Pairing: prompt for code on first run; save `~/.accountings/tally-connector.json` with `device_token`, `api_url`, `tally_host`, `tally_port`
- Connect WS with `Authorization: Bearer {device_token}`
- Every 10s send `{"type":"heartbeat","tally_ok": probe(...)}`
- On `request`: `post_xml` → `response` with `ok` + `data: {raw_xml: text}` (truncate if > 500_000 chars)
- On auth failure: print “Re-pair from Settings → Tally”

- [ ] **Step 3: README for non-technical install**

Steps: install Python 3.11+, `pip install -e .`, enable TallyPrime XML/ODBC port 9000, run `accountings-tally-connector`, paste code from Settings.

- [ ] **Step 4: Optionally set `TALLY_CONNECTOR_DOWNLOAD_URL` later** — for now UI shows README instructions if download_url empty.

- [ ] **Step 5: Commit**

```bash
git add apps/tally-connector
git commit -m "feat(tally): Windows dial-out connector CLI"
```

Also patch API send path to include `xml` if not done in Task 3:

```python
from app.services.tally_gateway import assert_op_allowed, build_tally_xml
# in LiveSession.rpc or TallyTools before rpc:
assert_op_allowed(op)
xml = build_tally_xml(op, args)
await self.send_json({"type": "request", "id": req_id, "op": op, "args": args, "xml": xml})
```

Commit that API tweak with the connector if needed.

---

### Task 8: End-to-end hardening + docs

**Files:**
- Modify: `README.md`, `.env.example`
- Modify: health/docs as needed
- Test: full pytest subset

- [ ] **Step 1: Update root README** with Settings → Tally + connector section; remove firm MCP instructions.

- [ ] **Step 2: `.env.example`**

```env
TALLY_TOKEN_PEPPER=dev-tally-pepper-change-me
TALLY_CONNECTOR_DOWNLOAD_URL=
TALLY_HEARTBEAT_STALE_SECONDS=60
TALLY_RPC_TIMEOUT_SECONDS=25
```

- [ ] **Step 3: Run full relevant tests**

Run: `cd apps/api && uv run pytest tests/test_tally_crypto.py tests/test_tally_pairing.py tests/test_tally_sessions.py tests/test_tally_gateway.py tests/test_tally_tools.py tests/test_chat.py -v`  
Expected: all PASS

- [ ] **Step 4: Manual checklist**

1. Migrate DB  
2. Start API + web  
3. Settings → Connect → copy code  
4. Run connector with code  
5. Open TallyPrime company, XML on  
6. Advisor: “What is my Tally connection status?” then a ledger question  

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example
git commit -m "docs: TallyPrime hosted connector setup"
```

---

## Spec coverage checklist

| Spec item | Task |
| --- | --- |
| Hosted gateway + dial-out connector | 3, 4, 7 |
| Pairing code + download UX | 2, 6 |
| Status Online/Offline/Not connected/unreachable | 2, 3, 6 |
| Disconnect revokes | 2, 3 |
| DB tables | 1 |
| Whitelist read-only ops | 4 |
| `TallyTools` on Advisor | 5 |
| Remove firm `TALLY_MCP_*` | 1, 5 |
| Windows connector | 7 |
| Org isolation | 2–5 |
| Tests unit + fake session | 1–5 |
| Docs | 7, 8 |

## Plan self-review notes

- Path prefix: plan uses `/tally/*` to match existing FastAPI routers (`/auth`, `/clients`); equivalent to spec’s `/api/tally/*` conceptually.
- Connector receives `xml` on each request so XML templates stay server-side.
- In-memory `_sessions` is single-process only (acceptable for MVP; document in README).
- No write ops, no per-client company map, no macOS connector — deferred per spec.
