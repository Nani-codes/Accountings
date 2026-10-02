from datetime import date
from decimal import Decimal

from app.recon.match import reconcile
from app.recon.normalize import Invoice, normalize_invoice_number, to_invoice


def inv(
    *,
    number: str,
    gstin: str,
    taxable: float,
    total: float | None = None,
    cgst: float = 0,
    sgst: float = 0,
    igst: float = 0,
    day: int = 1,
) -> Invoice:
    t = Decimal(str(taxable))
    return Invoice(
        invoice_number=number,
        invoice_date=date(2026, 3, day),
        supplier_gstin=gstin,
        recipient_gstin="29AAAAA0000A1Z5",
        taxable_value=t,
        igst=Decimal(str(igst)),
        cgst=Decimal(str(cgst)),
        sgst=Decimal(str(sgst)),
        cess=Decimal("0"),
        total=Decimal(str(total if total is not None else taxable + cgst + sgst + igst)),
    )


def test_normalize_strips_separators_and_case():
    assert normalize_invoice_number(" INV/001-A ") == "INV001A"
    assert normalize_invoice_number("inv001a") == "INV001A"


def test_to_invoice_from_row():
    invoice = to_invoice(
        {
            "invoice_number": "A-1",
            "invoice_date": "2026-03-01",
            "supplier_gstin": "29abcde1234f1z5",
            "taxable_value": "1000",
            "cgst": "90",
            "sgst": "90",
            "total": "1180",
        }
    )
    assert invoice.supplier_gstin == "29ABCDE1234F1Z5"
    assert invoice.taxable_value == Decimal("1000")


def test_exact_match_gstin_and_number():
    p = [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, cgst=90, sgst=90, total=1180)]
    b = [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, cgst=90, sgst=90, total=1180)]
    out = reconcile(p, b)
    assert out.summary["matched"] == 1
    assert out.results[0].match_status == "exact_match"


def test_missing_in_2b():
    out = reconcile(
        [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, total=1180)], []
    )
    assert out.results[0].match_status == "missing_in_2b"


def test_gstin_mismatch_same_normalized_number():
    out = reconcile(
        [inv(number="INV-1", gstin="29ABCDE1234F1Z5", taxable=1000, total=1180)],
        [inv(number="INV1", gstin="29ABCDE1234F1Z6", taxable=1000, total=1180)],
    )
    assert out.results[0].match_status == "gstin_mismatch"


def test_amount_mismatch():
    out = reconcile(
        [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=120000, total=120000)],
        [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=118000, total=118000)],
    )
    assert out.results[0].match_status == "amount_mismatch"


def test_tax_mismatch():
    out = reconcile(
        [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, cgst=108, sgst=108, total=1216)],
        [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, cgst=98, sgst=98, total=1196)],
    )
    assert out.results[0].match_status == "tax_mismatch"


def test_duplicate_purchase_rows():
    p = [
        inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, total=1180),
        inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, total=1180),
    ]
    b = [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, total=1180)]
    out = reconcile(p, b)
    assert all(r.match_status == "duplicate" for r in out.results)


def test_date_mismatch_beyond_tolerance():
    p = [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, total=1180, day=1)]
    b = [inv(number="A1", gstin="29ABCDE1234F1Z5", taxable=1000, total=1180, day=20)]
    out = reconcile(p, b, date_tolerance_days=3)
    assert out.results[0].match_status == "date_mismatch"


def test_fuzzy_number_match_after_normalization_tier():
    out = reconcile(
        [inv(number="INV-1", gstin="29ABCDE1234F1Z5", taxable=1000, cgst=90, sgst=90, total=1180)],
        [inv(number="INV1", gstin="29ABCDE1234F1Z5", taxable=1000, cgst=90, sgst=90, total=1180)],
    )
    assert out.results[0].match_status == "exact_match"
