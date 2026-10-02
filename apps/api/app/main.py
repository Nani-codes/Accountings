from __future__ import annotations

import warnings

from agno.db.postgres import PostgresDb
from agno.os import AgentOS
from agno.tools.websearch import WebSearchTools
from fastapi import FastAPI

# agno's components router registers two operations that resolve to the same
# OpenAPI operationId (get_config / get_config_version), which emits a noisy
# UserWarning at schema-build time. It is cosmetic; silence just this one.
warnings.filterwarnings(
    "ignore",
    message="Duplicate Operation ID get_config.*",
    category=UserWarning,
)

from app.ai.agents import (
    build_ca_advisor_agent,
    build_client_request_agent,
    build_explain_agent,
    build_working_paper_agent,
)
from app.ai.chat_tools import WorkbenchTools
from app.ai.tally_tools import TallyTools
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


def _register_health(app: FastAPI) -> None:
    """Attach the product health route. Re-applied to the final app so it wins
    over AgentOS's own /health (which would otherwise override ours)."""

    @app.get("/health")
    def health():
        from app.services.storage import storage_info

        return {
            "status": "ok",
            "storage": storage_info(),
            "tally_connector": "enabled",
        }


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

    _register_health(app)

    return app


def build_agent_os(base_app: FastAPI | None = None) -> AgentOS:
    from app.db import engine

    db = PostgresDb(id=AGENT_OS_DB_ID, db_engine=engine)
    # Workbench tools + Tally tools + web search as function tools. Do not use Gemini
    # search=True — it disables all external tools.
    advisor_tools: list = [
        WorkbenchTools(),
        WebSearchTools(enable_news=False, fixed_max_results=5),
        TallyTools(),
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
        # Keep our product routes (notably /health reporting storage + tally)
        # instead of letting AgentOS override them.
        on_route_conflict="preserve_base_app",
    )


base_app = create_base_app()

# Mount AgentOS when Vertex credentials/project are configured.
from app.ai.agents import vertex_configured

if vertex_configured():
    agent_os = build_agent_os(base_app)
    app = agent_os.get_app()
else:
    app = base_app
