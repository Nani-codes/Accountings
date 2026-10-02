import asyncio
from uuid import uuid4

import pytest

from app.services.tally_sessions import (
    LiveSession,
    drop_live_session,
    get_live_session,
    register_live_session,
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


@pytest.mark.asyncio
async def test_rpc_resolves_response():
    org = uuid4()
    sess = LiveSession(organization_id=org)
    
    # Mock send_json to allow RPC to proceed
    async def mock_send_json(msg: dict):
        pass
    
    sess.send_json = mock_send_json
    register_live_session(org, sess)

    async def responder():
        await asyncio.sleep(0.01)
        req_id = next(iter(sess._pending.keys()))
        sess.resolve_response(req_id, {"ok": True, "data": {"balance": "100"}})

    task = asyncio.create_task(responder())
    result = await sess.rpc("ledger_balance", {"ledger": "Cash"}, timeout=2.0)
    await task
    assert result["balance"] == "100"
    drop_live_session(org)
