import asyncio
from uuid import uuid4

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


def test_rpc_resolves_response():
    org = uuid4()
    sess = LiveSession(organization_id=org)
    sent: list[dict] = []

    async def send_json(payload: dict) -> None:
        sent.append(payload)

    sess.send_json = send_json
    register_live_session(org, sess)

    async def _run():
        async def responder():
            await asyncio.sleep(0.01)
            # the request frame must have registered a pending future
            assert len(sess._pending) == 1
            req_id = next(iter(sess._pending.keys()))
            sess.resolve_response(req_id, {"ok": True, "data": {"balance": "100"}})

        task = asyncio.create_task(responder())
        result = await sess.rpc("ledger_balance", {"ledger": "Cash"}, timeout=2.0)
        await task
        return result

    out = asyncio.run(_run())
    assert len(sent) == 1
    assert sent[0]["type"] == "request"
    assert sent[0]["op"] == "ledger_balance"
    assert sent[0]["args"] == {"ledger": "Cash"}
    assert sent[0]["id"]
    assert out["balance"] == "100"
    assert not sess._pending
    drop_live_session(org)
