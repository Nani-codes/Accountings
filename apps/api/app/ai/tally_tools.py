from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from typing import Any, Iterator, Optional
from uuid import UUID

from agno.tools import Toolkit
from sqlalchemy.orm import Session

from app.ai.org_context import get_request_org_id
from app.config import settings
from app.db import SessionLocal
from app.services.tally_pairing import connection_status_for_org
from app.services.tally_sessions import get_live_session


def _json(obj: Any) -> str:
    return json.dumps(obj, default=str)


def _run(coro):
    """Run async coroutine from sync context.
    
    If already in an event loop (AgentOS), use ThreadPoolExecutor.
    Otherwise, use asyncio.run().
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # If already in a loop (AgentOS), create a task and wait via executor
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class TallyTools(Toolkit):
    """Tally read-only tools scoped to a single organization.
    
    Responses are CA-facing: ledger names, balances, dates — never UUIDs or device tokens.
    
    Pass ``db`` + ``organization_id`` for direct/in-process calls.
    For AgentOS / product Advisor, omit them — org is resolved from JWT
    middleware via ``org_context``, and each tool opens a short-lived DB session.
    """

    def __init__(
        self,
        db: Session | None = None,
        organization_id: UUID | None = None,
        **kwargs,
    ):
        self._db = db
        self._organization_id = organization_id
        super().__init__(
            name="tally_tools",
            tools=[
                self.tally_connection_status,
                self.tally_list_companies,
                self.tally_ledger_balance,
                self.tally_day_book,
                self.tally_trial_balance,
            ],
            **kwargs,
        )

    def _resolve_org(self) -> UUID | None:
        if self._organization_id is not None:
            return self._organization_id
        return get_request_org_id()

    @contextmanager
    def _session(self) -> Iterator[tuple[Session, UUID] | tuple[None, None]]:
        org_id = self._resolve_org()
        if org_id is None:
            yield None, None  # type: ignore[misc]
            return
        if self._db is not None:
            yield self._db, org_id
            return
        db = SessionLocal()
        try:
            yield db, org_id
        finally:
            db.close()

    def _needs_auth(self) -> str:
        return _json(
            {
                "error": "unauthorized",
                "detail": (
                    "Sign in to Accountings (JWT in Authorization) so Tally "
                    "tools can resolve your organization."
                ),
            }
        )

    def tally_connection_status(self) -> str:
        """Check if Tally connector is online and paired."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            live_session = get_live_session(org_id)
            status = connection_status_for_org(db, org_id, live_session=live_session)
            return _json(status)

    def tally_list_companies(self) -> str:
        """List companies available in the paired Tally instance."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            live_session = get_live_session(org_id)
            if live_session is None:
                return _json({"error": "offline", "detail": "Tally connector is offline"})
            if not getattr(live_session, "tally_ok", False):
                return _json(
                    {
                        "error": "tally_unreachable",
                        "detail": "Tally is not responding on the firm PC",
                    }
                )
            try:
                result = _run(live_session.rpc("list_companies", {}, timeout=settings.tally_rpc_timeout_seconds))
                return _json(result)
            except Exception as e:
                return _json(
                    {
                        "error": "rpc_failed",
                        "detail": str(e),
                    }
                )

    def tally_ledger_balance(
        self,
        ledger: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> str:
        """Get ledger balance for a given ledger name and optional date range."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            live_session = get_live_session(org_id)
            if live_session is None:
                return _json({"error": "offline", "detail": "Tally connector is offline"})
            if not getattr(live_session, "tally_ok", False):
                return _json(
                    {
                        "error": "tally_unreachable",
                        "detail": "Tally is not responding on the firm PC",
                    }
                )
            try:
                args = {"ledger": ledger}
                if from_date:
                    args["from"] = from_date
                if to_date:
                    args["to"] = to_date
                result = _run(live_session.rpc("ledger_balance", args, timeout=settings.tally_rpc_timeout_seconds))
                return _json(result)
            except Exception as e:
                return _json(
                    {
                        "error": "rpc_failed",
                        "detail": str(e),
                    }
                )

    def tally_day_book(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> str:
        """Get day book entries for a date range."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            live_session = get_live_session(org_id)
            if live_session is None:
                return _json({"error": "offline", "detail": "Tally connector is offline"})
            if not getattr(live_session, "tally_ok", False):
                return _json(
                    {
                        "error": "tally_unreachable",
                        "detail": "Tally is not responding on the firm PC",
                    }
                )
            try:
                args = {}
                if from_date:
                    args["from"] = from_date
                if to_date:
                    args["to"] = to_date
                result = _run(live_session.rpc("day_book", args, timeout=settings.tally_rpc_timeout_seconds))
                return _json(result)
            except Exception as e:
                return _json(
                    {
                        "error": "rpc_failed",
                        "detail": str(e),
                    }
                )

    def tally_trial_balance(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> str:
        """Get trial balance for a date range."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            live_session = get_live_session(org_id)
            if live_session is None:
                return _json({"error": "offline", "detail": "Tally connector is offline"})
            if not getattr(live_session, "tally_ok", False):
                return _json(
                    {
                        "error": "tally_unreachable",
                        "detail": "Tally is not responding on the firm PC",
                    }
                )
            try:
                args = {}
                if from_date:
                    args["from"] = from_date
                if to_date:
                    args["to"] = to_date
                result = _run(live_session.rpc("trial_balance", args, timeout=settings.tally_rpc_timeout_seconds))
                return _json(result)
            except Exception as e:
                return _json(
                    {
                        "error": "rpc_failed",
                        "detail": str(e),
                    }
                )
