from __future__ import annotations

from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
from agno.tools.websearch import WebSearchTools
from fastapi import FastAPI

from app.ai.agents import (
    build_ca_advisor_agent,
    build_client_request_agent,
    build_explain_agent,
    build_working_paper_agent,
)
from app.ai.chat_tools import WorkbenchTools
from app.api.auth import router as auth_router
from app.api.clients import router as clients_router
from app.api.dashboard import router as dashboard_router
from app.api.exports import router as exports_router
from app.api.findings import router as findings_router
from app.api.middleware_org import OrgContextMiddleware
from app.api.tally import router as tally_router
from app.api.uploads import router as uploads_router
from app.config import settings

# AgentOS session/run store id — product Advisor UI uses Agno’s built-in
# /sessions and /agents/{id}/runs (no custom /api/chat wrapper).
AGENT_OS_DB_ID = "gst-workbench-os-db"
CA_ADVISOR_AGENT_ID = "ca-advisor"


def _cors_origins() -> list[str]:
    return [o.strip() for o in settings.api_cors_origins.split(",") if o.strip()]


def create_base_app() -> FastAPI:
    app = FastAPI(title="Accountings API")
    origins = _cors_origins()
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(OrgContextMiddleware)
    app.include_router(auth_router)
    app.include_router(clients_router)
    app.include_router(dashboard_router)
    app.include_router(uploads_router)
    app.include_router(findings_router)
    app.include_router(exports_router)
    app.include_router(tally_router)
    app.include_router(tally_router)

    @app.get("/health")
    def health():
        from app.services.storage import storage_info

        return {
            "status": "ok",
            "storage": storage_info(),
            "tally_connector": "enabled",
        }

    return app


def build_agent_os(base_app: FastAPI | None = None) -> AgentOS:
    db = SqliteDb(id=AGENT_OS_DB_ID, db_file="tmp/agent_os.db")
    # Workbench tools + web search as function tools. Do not use Gemini
    # search=True — it disables all external tools.
    advisor_tools: list = [
        WorkbenchTools(),
        WebSearchTools(enable_news=False, fixed_max_results=5),
    ]
    return AgentOS(
        id="gst-workbench-os",
        description="Accountings AgentOS — CA GST reconciliation",
        agents=[
            build_explain_agent(db=db),
            build_client_request_agent(db=db),
            build_working_paper_agent(db=db),
            build_ca_advisor_agent(tools=advisor_tools, db=db),
        ],
        db=db,
        base_app=base_app or create_base_app(),
        cors_allowed_origins=_cors_origins() or None,
    )


base_app = create_base_app()

# Mount AgentOS when Vertex credentials/project are configured.
from app.ai.agents import vertex_configured

if vertex_configured():
    agent_os = build_agent_os(base_app)
    app = agent_os.get_app()
else:
    app = base_app
