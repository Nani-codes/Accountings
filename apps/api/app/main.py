from __future__ import annotations

from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
from fastapi import FastAPI

from app.ai.agents import (
    build_client_request_agent,
    build_explain_agent,
    build_working_paper_agent,
)
from app.api.auth import router as auth_router
from app.api.clients import router as clients_router
from app.api.dashboard import router as dashboard_router
from app.api.exports import router as exports_router
from app.api.findings import router as findings_router
from app.api.uploads import router as uploads_router
from app.config import settings


def create_base_app() -> FastAPI:
    app = FastAPI(title="GST Workbench API")
    origins = [o.strip() for o in settings.api_cors_origins.split(",") if o.strip()]
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(clients_router)
    app.include_router(dashboard_router)
    app.include_router(uploads_router)
    app.include_router(findings_router)
    app.include_router(exports_router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


def build_agent_os(base_app: FastAPI | None = None) -> AgentOS:
    db = SqliteDb(id="gst-workbench-os-db", db_file="tmp/agent_os.db")
    return AgentOS(
        id="gst-workbench-os",
        description="CA GST reconciliation AgentOS",
        agents=[
            build_explain_agent(),
            build_client_request_agent(),
            build_working_paper_agent(),
        ],
        db=db,
        base_app=base_app or create_base_app(),
    )


base_app = create_base_app()

# Mount AgentOS when OpenAI key present; otherwise keep plain FastAPI for local/tests.
if settings.openai_api_key:
    agent_os = build_agent_os(base_app)
    app = agent_os.get_app()
else:
    app = base_app
