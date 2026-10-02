from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from app.recon.match import MatchResult
from app.recon.normalize import Invoice


@dataclass
class ExceptionGroup:
    category: str
    supplier_gstin: str | None
    supplier_key: str
    invoice_count: int
    potential_itc: Decimal
    evidence: dict


def group_exceptions(
    results: list[MatchResult],
    invoices_by_id: dict[str, Invoice] | None = None,
) -> list[ExceptionGroup]:
    buckets: dict[tuple[str, str], list[MatchResult]] = defaultdict(list)
    for result in results:
        if result.match_status == "exact_match":
            continue
        gstin = result.purchase.supplier_gstin or "unknown"
        buckets[(result.match_status, gstin)].append(result)

    groups: list[ExceptionGroup] = []
    for (category, gstin), items in buckets.items():
        itc = sum((i.purchase.cgst + i.purchase.sgst + i.purchase.igst for i in items), Decimal("0"))
        groups.append(
            ExceptionGroup(
                category=category,
                supplier_gstin=None if gstin == "unknown" else gstin,
                supplier_key=gstin,
                invoice_count=len(items),
                potential_itc=itc,
                evidence={
                    "invoice_numbers": [i.purchase.invoice_number for i in items],
                    "sample_diffs": [
                        {
                            "purchase_gstin": i.purchase.supplier_gstin,
                            "gstr_gstin": i.gstr.supplier_gstin if i.gstr else None,
                            "difference_amount": str(i.difference_amount)
                            if i.difference_amount is not None
                            else None,
                            "difference_type": i.difference_type,
                        }
                        for i in items[:5]
                    ],
                },
            )
        )
    return groups
