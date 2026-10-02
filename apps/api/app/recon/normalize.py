from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def normalize_invoice_number(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _to_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {value!r}")


@dataclass(frozen=True)
class Invoice:
    invoice_number: str
    invoice_date: date
    supplier_gstin: str
    recipient_gstin: str | None
    taxable_value: Decimal
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    cess: Decimal
    total: Decimal
    source_id: str | None = None

    @property
    def normalized_number(self) -> str:
        return normalize_invoice_number(self.invoice_number)


def to_invoice(row: dict[str, Any], *, source_id: str | None = None) -> Invoice:
    return Invoice(
        invoice_number=str(row["invoice_number"]).strip(),
        invoice_date=_to_date(row["invoice_date"]),
        supplier_gstin=str(row["supplier_gstin"]).strip().upper(),
        recipient_gstin=(
            str(row["recipient_gstin"]).strip().upper()
            if row.get("recipient_gstin")
            else None
        ),
        taxable_value=_to_decimal(row.get("taxable_value")),
        igst=_to_decimal(row.get("igst")),
        cgst=_to_decimal(row.get("cgst")),
        sgst=_to_decimal(row.get("sgst")),
        cess=_to_decimal(row.get("cess")),
        total=_to_decimal(row.get("total")),
        source_id=source_id,
    )
