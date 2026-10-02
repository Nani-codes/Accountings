from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.agents import build_explain_agent
from app.ai.schemas import ExplainFindingOut
from app.models import AiFinding, ReconciliationRun
from app.recon.group import ExceptionGroup


def enrich_findings_from_groups(
    db: Session,
    run: ReconciliationRun,
    groups: list[ExceptionGroup],
    *,
    explain_fn=None,
) -> None:
    """Replace stub findings with Agno explanations when available.

    explain_fn(group_dict) -> ExplainFindingOut for tests / offline mode.
    """
    agent = None if explain_fn else build_explain_agent()

    # Clear prior pending findings for this run (idempotent re-enrich)
    db.query(AiFinding).filter(AiFinding.run_id == run.id).delete()
    for group in groups:
        payload = {
            "category": group.category,
            "supplier_gstin": group.supplier_gstin,
            "invoice_count": group.invoice_count,
            "potential_itc": str(group.potential_itc),
            "evidence": group.evidence,
        }
        if explain_fn:
            out: ExplainFindingOut = explain_fn(payload)
        else:
            try:
                result = agent.run(str(payload))
                out = result.content if isinstance(result.content, ExplainFindingOut) else ExplainFindingOut.model_validate(result.content)
            except Exception:
                out = ExplainFindingOut(
                    title=f"{group.category.replace('_', ' ').title()} — {group.supplier_key}",
                    description=f"{group.invoice_count} invoices affected.",
                    likely_reason="See evidence; LLM enrichment unavailable.",
                    recommended_action="Review supporting documents with the client.",
                    severity="medium",
                )
        db.add(
            AiFinding(
                client_id=run.client_id,
                run_id=run.id,
                category=group.category,
                severity=out.severity,
                title=out.title,
                description=f"{out.description}\n\nLikely reason: {out.likely_reason}",
                evidence=group.evidence,
                recommended_action=out.recommended_action,
                status="pending",
            )
        )


def draft_client_message(findings: list[AiFinding]) -> str:
    lines = [f"• {f.title}" for f in findings]
    return (
        "During our GST reconciliation we found items that need your confirmation:\n\n"
        + "\n".join(lines)
        + "\n\nPlease review and share corrected details/documents."
    )
