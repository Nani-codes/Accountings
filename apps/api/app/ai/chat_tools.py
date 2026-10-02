from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator, Optional
from uuid import UUID

from agno.tools import Toolkit
from sqlalchemy.orm import Session

from app.ai.org_context import get_request_org_id
from app.db import SessionLocal
from app.models import (
    AiFinding,
    Client,
    ClientDocument,
    Invoice,
    ReconciliationRun,
)


def _json(obj: Any) -> str:
    return json.dumps(obj, default=str)


class WorkbenchTools(Toolkit):
    """Read-only workbench tools scoped to a single organization.

    Responses are CA-facing: names, GSTINs, periods, statuses — never UUIDs.
    Lookups accept client name or GSTIN (and period for runs).

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
            name="workbench_tools",
            tools=[
                self.list_clients,
                self.get_client,
                self.list_runs,
                self.get_run,
                self.list_findings,
                self.get_finding,
                self.search_invoices,
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
                    "Sign in to Accountings (JWT in Authorization) so firm "
                    "data tools can resolve your organization."
                ),
            }
        )

    def _find_client(self, db: Session, org_id: UUID, client: str) -> Client | None:
        """Resolve by exact GSTIN (case-insensitive) or case-insensitive name."""
        q = (client or "").strip()
        if not q:
            return None
        gstin = q.upper()
        by_gstin = (
            db.query(Client)
            .filter(Client.organization_id == org_id, Client.gstin == gstin)
            .one_or_none()
        )
        if by_gstin:
            return by_gstin
        by_name = (
            db.query(Client)
            .filter(Client.organization_id == org_id, Client.name.ilike(q))
            .one_or_none()
        )
        if by_name:
            return by_name
        return (
            db.query(Client)
            .filter(Client.organization_id == org_id, Client.name.ilike(f"%{q}%"))
            .first()
        )

    def _find_run(
        self, db: Session, org_id: UUID, client: Client | None, period: str
    ) -> ReconciliationRun | None:
        if not client or not period:
            return None
        return (
            db.query(ReconciliationRun)
            .filter(
                ReconciliationRun.client_id == client.id,
                ReconciliationRun.organization_id == org_id,
                ReconciliationRun.period == period,
            )
            .one_or_none()
        )

    def list_clients(self) -> str:
        """List all clients for the organization."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            clients = db.query(Client).filter(Client.organization_id == org_id).all()
            return _json([{"name": c.name, "gstin": c.gstin} for c in clients])

    def get_client(self, client: str) -> str:
        """Get a client by name or GSTIN."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            row = self._find_client(db, org_id, client)
            if not row:
                return _json({"error": "not_found", "detail": f"Client '{client}' not found"})
            return _json({"name": row.name, "gstin": row.gstin})

    def list_runs(self, client: str | None = None) -> str:
        """List reconciliation runs for a client or all clients."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            q = db.query(ReconciliationRun).filter(ReconciliationRun.organization_id == org_id)
            if client:
                row = self._find_client(db, org_id, client)
                if not row:
                    return _json({"error": "not_found", "detail": f"Client '{client}' not found"})
                q = q.filter(ReconciliationRun.client_id == row.id)
            runs = q.all()
            return _json(
                [
                    {
                        "period": r.period,
                        "status": r.status,
                        "client_name": r.client.name if r.client else None,
                    }
                    for r in runs
                ]
            )

    def get_run(self, client: str, period: str) -> str:
        """Get a reconciliation run by client and period."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            row = self._find_client(db, org_id, client)
            if not row:
                return _json({"error": "not_found", "detail": f"Client '{client}' not found"})
            run = self._find_run(db, org_id, row, period)
            if not run:
                return _json({"error": "not_found", "detail": f"Run for {period} not found"})
            return _json(
                {
                    "period": run.period,
                    "status": run.status,
                    "client_name": row.name,
                    "summary": run.summary,
                }
            )

    def list_findings(self, client: str, period: str) -> str:
        """List findings for a client's reconciliation run."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            row = self._find_client(db, org_id, client)
            if not row:
                return _json({"error": "not_found", "detail": f"Client '{client}' not found"})
            run = self._find_run(db, org_id, row, period)
            if not run:
                return _json({"error": "not_found", "detail": f"Run for {period} not found"})
            findings = db.query(AiFinding).filter(AiFinding.run_id == run.id).all()
            return _json(
                [
                    {
                        "category": f.category,
                        "severity": f.severity,
                        "title": f.title,
                        "status": f.status,
                    }
                    for f in findings
                ]
            )

    def get_finding(self, client: str, period: str, title: str) -> str:
        """Get a specific finding by title."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            row = self._find_client(db, org_id, client)
            if not row:
                return _json({"error": "not_found", "detail": f"Client '{client}' not found"})
            run = self._find_run(db, org_id, row, period)
            if not run:
                return _json({"error": "not_found", "detail": f"Run for {period} not found"})
            finding = (
                db.query(AiFinding)
                .filter(AiFinding.run_id == run.id, AiFinding.title.ilike(title))
                .first()
            )
            if not finding:
                return _json({"error": "not_found", "detail": f"Finding '{title}' not found"})
            return _json(
                {
                    "category": finding.category,
                    "severity": finding.severity,
                    "title": finding.title,
                    "description": finding.description,
                    "evidence": finding.evidence,
                    "status": finding.status,
                }
            )

    def search_invoices(self, client: str, query: str) -> str:
        """Search invoices for a client by number or amount."""
        with self._session() as (db, org_id):
            if db is None or org_id is None:
                return self._needs_auth()
            row = self._find_client(db, org_id, client)
            if not row:
                return _json({"error": "not_found", "detail": f"Client '{client}' not found"})
            invoices = (
                db.query(Invoice)
                .filter(
                    Invoice.client_id == row.id,
                    (Invoice.invoice_number.ilike(f"%{query}%"))
                    | (Invoice.amount.astext.ilike(f"%{query}%")),
                )
                .limit(10)
                .all()
            )
            return _json(
                [
                    {
                        "invoice_number": inv.invoice_number,
                        "amount": str(inv.amount),
                        "date": inv.date.isoformat() if inv.date else None,
                    }
                    for inv in invoices
                ]
            )
