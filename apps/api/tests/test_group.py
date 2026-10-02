from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.recon.group import group_exceptions
from app.recon.match import MatchResult
from app.recon.normalize import Invoice


def _inv(number: str, gstin: str = "29ABCDE1234F1Z5") -> Invoice:
    return Invoice(
        invoice_number=number,
        invoice_date=date(2026, 3, 1),
        supplier_gstin=gstin,
        recipient_gstin=None,
        taxable_value=Decimal("1000"),
        igst=Decimal("0"),
        cgst=Decimal("90"),
        sgst=Decimal("90"),
        cess=Decimal("0"),
        total=Decimal("1180"),
    )


def test_groups_gstin_mismatches_by_supplier():
    results = [
        MatchResult(
            purchase=_inv(f"A{i}"),
            gstr=_inv(f"A{i}", gstin="29ABCDE1234F1Z6"),
            match_status="gstin_mismatch",
            match_score=Decimal("0.5"),
            difference_type="gstin",
        )
        for i in range(3)
    ]
    groups = group_exceptions(results)
    assert len(groups) == 1
    assert groups[0].invoice_count == 3
    assert groups[0].category == "gstin_mismatch"
    assert groups[0].potential_itc == Decimal("540")
