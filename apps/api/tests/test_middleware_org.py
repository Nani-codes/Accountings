"""Unit tests for OrgContextMiddleware JWT -> org_id resolution (bug fix)."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from starlette.requests import Request

from app.api import middleware_org
from app.api.middleware_org import OrgContextMiddleware
from app.services.auth import create_access_token


def _request_with_auth(header_value: str | None) -> Request:
    headers = []
    if header_value is not None:
        headers.append((b"authorization", header_value.encode()))
    scope = {"type": "http", "headers": headers}
    return Request(scope)


def test_resolve_org_id_returns_none_without_bearer():
    assert OrgContextMiddleware._resolve_org_id(_request_with_auth(None)) is None
    assert (
        OrgContextMiddleware._resolve_org_id(_request_with_auth("Token abc")) is None
    )


def test_resolve_org_id_returns_none_for_invalid_token():
    req = _request_with_auth("Bearer not-a-real-jwt")
    assert OrgContextMiddleware._resolve_org_id(req) is None


def test_resolve_org_id_looks_up_user_org(monkeypatch):
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    token = create_access_token(user_id=user_id)

    class _Query:
        def filter(self, *_a, **_k):
            return self

        def first(self):
            return SimpleNamespace(organization_id=org_id)

    class _Session:
        def query(self, *_a, **_k):
            return _Query()

        def close(self):
            pass

    monkeypatch.setattr(middleware_org, "SessionLocal", lambda: _Session())

    req = _request_with_auth(f"Bearer {token}")
    assert OrgContextMiddleware._resolve_org_id(req) == org_id


def test_resolve_org_id_returns_none_when_user_missing(monkeypatch):
    token = create_access_token(user_id=uuid.uuid4())

    class _Query:
        def filter(self, *_a, **_k):
            return self

        def first(self):
            return None

    class _Session:
        def query(self, *_a, **_k):
            return _Query()

        def close(self):
            pass

    monkeypatch.setattr(middleware_org, "SessionLocal", lambda: _Session())

    req = _request_with_auth(f"Bearer {token}")
    assert OrgContextMiddleware._resolve_org_id(req) is None
