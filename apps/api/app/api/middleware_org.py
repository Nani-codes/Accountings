from __future__ import annotations

from uuid import UUID

from fastapi import Request
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.ai.org_context import set_request_org_id
from app.config import settings


class OrgContextMiddleware(BaseHTTPMiddleware):
    """Extract org_id from JWT and set it in request context for tools."""

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")
        org_id = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
                user_id = payload.get("sub")
                if user_id:
                    # In a real app, look up user → org_id from DB
                    # For now, we'll rely on tools to fetch it
                    pass
            except Exception:
                pass
        set_request_org_id(org_id)
        response = await call_next(request)
        return response
