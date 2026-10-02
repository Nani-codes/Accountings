from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.clients import router as clients_router
from app.api.dashboard import router as dashboard_router
from app.api.findings import router as findings_router
from app.api.uploads import router as uploads_router
from app.config import settings


def create_base_app() -> FastAPI:
    app = FastAPI(title="GST Workbench API")
    origins = [o.strip() for o in settings.api_cors_origins.split(",") if o.strip()]
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

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


base_app = create_base_app()
app = base_app  # AgentOS wraps this in Task 10
