from __future__ import annotations

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.ai.schemas import ClientRequestOut, ExplainFindingOut, WorkingPaperOut
from app.config import settings


def _model() -> OpenAIChat:
    # Single cloud model for v1; key from settings/env
    return OpenAIChat(id="gpt-4o-mini", api_key=settings.openai_api_key or None)


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
