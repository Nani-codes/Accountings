from __future__ import annotations

from contextvars import ContextVar
from uuid import UUID

_org_id_context: ContextVar[UUID | None] = ContextVar("org_id", default=None)


def set_request_org_id(org_id: UUID | None) -> None:
    """Set the organization ID for the current request context."""
    _org_id_context.set(org_id)


def get_request_org_id() -> UUID | None:
    """Get the organization ID from the current request context."""
    return _org_id_context.get()
