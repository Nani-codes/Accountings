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


def _model(*, search: bool = False) -> Gemini:
    kwargs: dict = {
        "id": settings.vertex_model_id,
        "vertexai": True,
        "project_id": settings.google_cloud_project or None,
        "location": settings.google_cloud_location,
    }
    credentials = _vertex_credentials()
    if credentials is not None:
        kwargs["credentials"] = credentials
    if search:
        kwargs["search"] = True
    return Gemini(**kwargs)


CA_ADVISOR_INSTRUCTIONS = (
    "You are an Indian Chartered Accountant assistant for a GST reconciliation workbench. "
    "For legal or process questions: call the web_search tool, prefer official government "
    "sources (gst.gov.in, cbic.gov.in, incometax.gov.in, and similar) first; use open-web "
    "sources only as a fallback. "
    "Cite inline: after each claim grounded in search, place a bare marker like [1] or [2] "
    "matching the 1-based index of the web_search result you used. Do not dump a separate "
    "sources bullet list at the end. Use multiple markers when several sources support a claim. "
    "When the user mentions clients, runs, findings, invoices, or firm data, call the workbench "
    "tools before answering — never invent GSTINs, invoice numbers, amounts, or statuses. "
    "Present clients as name + GSTIN only. Never show Client ID, run id, finding id, UUID, "
    "or other internal identifiers in your replies — even if a tool payload contains them. "
    "If tools return not_found or unauthorized, say so clearly. "
    "When the user attaches documents (PDF, Excel, CSV, images, etc.), ground your answer in "
    "their content; do not invent figures, invoice numbers, or amounts that are not present. "
    "When the user asks about live Tally books (ledgers, day book, trial balance), call the tally_* tools. "
    "If tally_connection_status is not online, tell the CA to open Settings → Tally and start the Accountings Connector on the firm PC — never invent book figures. "
    "Never show device tokens, connection ids, or internal UUIDs. "
    "Format answers in clear markdown (headings, lists, bold sparingly). "
    "Answers are educational only; the CA must verify against official sources before filing. "
    "Do not perform write actions on the Accountings workbench (accept/dismiss findings, "
    "send email, or mutate workbench data)."
)


def build_ca_advisor_agent(*, tools: list | None = None, db=None) -> Agent:
    """Firm-wide CA advisor with web search + optional org tools.

    Note: Gemini ``search=True`` (built-in grounding) disables external function
    tools, so we use WebSearchTools instead of model-level search.
    """
    kwargs: dict = {
        "id": "ca-advisor",
        "name": "CAAdvisor",
        "model": _model(search=False),
        "tools": tools if tools is not None else [],
        "instructions": CA_ADVISOR_INSTRUCTIONS,
        "markdown": True,
        "add_history_to_context": True,
        "num_history_runs": 5,
        "add_datetime_to_context": True,
    }
    if db is not None:
        kwargs["db"] = db
    return Agent(**kwargs)


def build_explain_agent(*, db=None) -> Agent:
    kwargs: dict = {
        "id": "explain-finding",
        "name": "ExplainFinding",
        "model": _model(),
        "output_schema": ExplainFindingOut,
        "instructions": (
            "You explain GST reconciliation exception groups for Indian CAs. "
            "Use only the provided JSON evidence. Do not invent invoices or amounts."
        ),
    }
    if db is not None:
        kwargs["db"] = db
    return Agent(**kwargs)


def build_client_request_agent(*, db=None) -> Agent:
    kwargs: dict = {
        "id": "draft-client-request",
        "name": "DraftClientRequest",
        "model": _model(),
        "output_schema": ClientRequestOut,
        "instructions": (
            "Draft a short professional email from a CA firm to a client about GST "
            "reconciliation exceptions. Use only the provided findings. No WhatsApp slang."
        ),
    }
    if db is not None:
        kwargs["db"] = db
    return Agent(**kwargs)


def build_working_paper_agent(*, db=None) -> Agent:
    kwargs: dict = {
        "id": "generate-working-paper",
        "name": "GenerateWorkingPaper",
        "model": _model(),
        "output_schema": WorkingPaperOut,
        "instructions": (
            "Write a concise GST reconciliation working-paper narrative from the run "
            "summary and accepted findings. Do not invent numbers."
        ),
    }
    if db is not None:
        kwargs["db"] = db
    return Agent(**kwargs)
