from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
from uuid import UUID

from app.services.tally_gateway import assert_op_allowed, build_tally_xml

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
        
        # Validate operation and build XML
        assert_op_allowed(op)
        xml = build_tally_xml(op, args)
        
        req_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[req_id] = fut
        try:
            await self.send_json(
                {
                    "type": "request",
                    "id": req_id,
                    "op": op,
                    "args": args or {},
                    "xml": xml,
                }
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

