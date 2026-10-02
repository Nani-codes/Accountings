from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from agno.agent import Agent
from agno.models.google import Gemini
from google.oauth2 import service_account

from app.ai.schemas import ClientRequestOut, ExplainFindingOut, WorkingPaperOut
from app.config import settings


@lru_cache
def _vertex_credentials():
    path = settings.google_application_credentials.strip()
    if not path:
        return None
    cred_path = Path(path).expanduser()
    if not cred_path.is_file():
        return None
    return service_account.Credentials.from_service_account_file(
        str(cred_path),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


def vertex_configured() -> bool:
    if not settings.google_cloud_project:
        return False
    if settings.google_application_credentials and Path(
        settings.google_application_credentials
    ).expanduser().is_file():
        return True
    # ADC / env may still work without an explicit JSON path
    return bool(settings.google_genai_use_vertexai)


def _model() -> Gemini:
    kwargs: dict = {
        "id": settings.vertex_model_id,
        "vertexai": True,
        "project_id": settings.google_cloud_project or None,
        "location": settings.google_cloud_location,
    }
    credentials = _vertex_credentials()
    if credentials is not None:
        kwargs["credentials"] = credentials
    return Gemini(**kwargs)


def build_explain_agent() -> Agent:
    return Agent(
        id="explain-finding",
        name="ExplainFinding",
        model=_model(),
        output_schema=ExplainFindingOut,
        instructions=(
            "You explain GST reconciliation exception groups for Indian CAs. "
            "Use only the provided JSON evidence. Do not invent invoices or amounts."
        ),
    )


def build_client_request_agent() -> Agent:
    return Agent(
        id="draft-client-request",
        name="DraftClientRequest",
        model=_model(),
        output_schema=ClientRequestOut,
        instructions=(
            "Draft a short professional email from a CA firm to a client about GST "
            "reconciliation exceptions. Use only the provided findings. No WhatsApp slang."
        ),
    )


def build_working_paper_agent() -> Agent:
    return Agent(
        id="generate-working-paper",
        name="GenerateWorkingPaper",
        model=_model(),
        output_schema=WorkingPaperOut,
        instructions=(
            "Write a concise GST reconciliation working-paper narrative from the run "
            "summary and accepted findings. Do not invent numbers."
        ),
    )
