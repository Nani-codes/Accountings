from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.recon.normalize import Invoice, normalize_invoice_number


@dataclass
class MatchResult:
    purchase: Invoice
    gstr: Invoice | None
    match_status: str
    match_score: Decimal
    difference_amount: Decimal | None = None
    difference_type: str | None = None


@dataclass
class ReconcileOutput:
    results: list[MatchResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _tax_total(inv: Invoice) -> Decimal:
    return inv.cgst + inv.sgst + inv.igst + inv.cess


def _amount_close(a: Decimal, b: Decimal, tol: Decimal) -> bool:
    return abs(a - b) <= tol


def _date_close(a: date, b: date, days: int) -> bool:
    return abs((a - b).days) <= days


def reconcile(
    purchase: list[Invoice],
    gstr2b: list[Invoice],
    *,
    date_tolerance_days: int = 3,
    amount_tolerance: Decimal = Decimal("1.00"),
) -> ReconcileOutput:
    # Detect duplicates in purchase by normalized number + gstin
    seen_keys: dict[tuple[str, str], int] = {}
    for p in purchase:
        key = (p.supplier_gstin, p.normalized_number)
        seen_keys[key] = seen_keys.get(key, 0) + 1

    used_gstr: set[int] = set()
    results: list[MatchResult] = []

    for p in purchase:
        key = (p.supplier_gstin, p.normalized_number)
        if seen_keys.get(key, 0) > 1:
            results.append(
                MatchResult(
                    purchase=p,
                    gstr=None,
                    match_status="duplicate",
                    match_score=Decimal("0"),
                    difference_type="duplicate",
                )
            )
            continue

        # Tier 1: GSTIN + exact invoice number
        candidates = [
            (i, g)
            for i, g in enumerate(gstr2b)
            if i not in used_gstr
            and g.supplier_gstin == p.supplier_gstin
            and g.invoice_number == p.invoice_number
        ]
        # Tier 2: GSTIN + normalized number
        if not candidates:
            candidates = [
                (i, g)
                for i, g in enumerate(gstr2b)
                if i not in used_gstr
                and g.supplier_gstin == p.supplier_gstin
                and g.normalized_number == p.normalized_number
            ]
        # Tier 3: GSTIN + amount + date
        if not candidates:
            candidates = [
                (i, g)
                for i, g in enumerate(gstr2b)
                if i not in used_gstr
                and g.supplier_gstin == p.supplier_gstin
                and _amount_close(g.taxable_value, p.taxable_value, amount_tolerance)
                and _date_close(g.invoice_date, p.invoice_date, date_tolerance_days)
            ]
        # Tier 4: GSTIN + approximate amount
        if not candidates:
            candidates = [
                (i, g)
                for i, g in enumerate(gstr2b)
                if i not in used_gstr
                and g.supplier_gstin == p.supplier_gstin
                and _amount_close(g.taxable_value, p.taxable_value, amount_tolerance * 5)
            ]
        # Tier 5: fuzzy — same normalized number any GSTIN (gstin mismatch path)
        fuzzy = [
            (i, g)
            for i, g in enumerate(gstr2b)
            if i not in used_gstr and g.normalized_number == p.normalized_number
        ]

        if not candidates and fuzzy:
            i, g = fuzzy[0]
            used_gstr.add(i)
            results.append(
                MatchResult(
                    purchase=p,
                    gstr=g,
                    match_status="gstin_mismatch",
                    match_score=Decimal("0.5"),
                    difference_amount=Decimal("0"),
                    difference_type="gstin",
                )
            )
            continue

        if not candidates:
            results.append(
                MatchResult(
                    purchase=p,
                    gstr=None,
                    match_status="missing_in_2b",
                    match_score=Decimal("0"),
                    difference_amount=p.taxable_value,
                    difference_type="missing",
                )
            )
            continue

        i, g = candidates[0]
        used_gstr.add(i)

        if p.invoice_date != g.invoice_date and not _date_close(
            p.invoice_date, g.invoice_date, date_tolerance_days
        ):
            results.append(
                MatchResult(
                    purchase=p,
                    gstr=g,
                    match_status="date_mismatch",
                    match_score=Decimal("0.7"),
                    difference_type="date",
                )
            )
            continue

        if not _amount_close(p.taxable_value, g.taxable_value, amount_tolerance):
            results.append(
                MatchResult(
                    purchase=p,
                    gstr=g,
                    match_status="amount_mismatch",
                    match_score=Decimal("0.8"),
                    difference_amount=p.taxable_value - g.taxable_value,
                    difference_type="amount",
                )
            )
            continue

        if not _amount_close(_tax_total(p), _tax_total(g), amount_tolerance):
            results.append(
                MatchResult(
                    purchase=p,
                    gstr=g,
                    match_status="tax_mismatch",
                    match_score=Decimal("0.85"),
                    difference_amount=_tax_total(p) - _tax_total(g),
                    difference_type="tax",
                )
            )
            continue

        # Simple credit note flag: numbers containing CN/DN with opposing signs not modeled — skip
        is_cn = "CN" in normalize_invoice_number(p.invoice_number) or str(
            p.invoice_number
        ).upper().startswith("CN")
        g_is_cn = "CN" in g.normalized_number
        if is_cn != g_is_cn and (is_cn or g_is_cn):
            results.append(
                MatchResult(
                    purchase=p,
                    gstr=g,
                    match_status="credit_debit_note_mismatch",
                    match_score=Decimal("0.6"),
                    difference_type="credit_note",
                )
            )
            continue

        results.append(
            MatchResult(
                purchase=p,
                gstr=g,
                match_status="exact_match",
                match_score=Decimal("1.0"),
                difference_amount=Decimal("0"),
                difference_type="none",
            )
        )

    summary = {
        "purchase_count": len(purchase),
        "gstr2b_count": len(gstr2b),
        "matched": sum(1 for r in results if r.match_status == "exact_match"),
        "exceptions": sum(1 for r in results if r.match_status != "exact_match"),
        "by_status": {},
    }
    for r in results:
        summary["by_status"][r.match_status] = (
            summary["by_status"].get(r.match_status, 0) + 1
        )

    return ReconcileOutput(results=results, summary=summary)
