from __future__ import annotations

from uuid import UUID

from fastapi import Request
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.ai.org_context import set_request_org_id
from app.config import settings
from app.db import SessionLocal
from app.models import User


class OrgContextMiddleware(BaseHTTPMiddleware):
    """Resolve org_id from the JWT and expose it to Agno tools.

    The JWT only carries ``sub`` (user id), so we look up the user's
    ``organization_id`` from the database and set it in a context var that
    ``WorkbenchTools`` / ``TallyTools`` read via ``get_request_org_id()``.
    Unauthenticated or invalid requests fall through with ``org_id=None``.
    """

    async def dispatch(self, request: Request, call_next):
        org_id = self._resolve_org_id(request)
        set_request_org_id(org_id)
        try:
            return await call_next(request)
        finally:
            # Avoid context bleeding across requests on reused worker tasks.
            set_request_org_id(None)

    @staticmethod
    def _resolve_org_id(request: Request) -> UUID | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except Exception:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == UUID(str(user_id))).first()
            return user.organization_id if user else None
        except Exception:
            return None
        finally:
            db.close()
