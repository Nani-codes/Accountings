from __future__ import annotations

REQUIRED_FIELDS = [
    "invoice_number",
    "invoice_date",
    "supplier_gstin",
    "taxable_value",
    "total",
]

OPTIONAL_TAX_FIELDS = ["cgst", "sgst", "igst", "cess", "recipient_gstin"]

TEMPLATES: dict[str, dict[str, str]] = {
    "generic_purchase": {
        "invoice_number": "invoice_number",
        "invoice_date": "invoice_date",
        "supplier_gstin": "supplier_gstin",
        "recipient_gstin": "recipient_gstin",
        "taxable_value": "taxable_value",
        "cgst": "cgst",
        "sgst": "sgst",
        "igst": "igst",
        "cess": "cess",
        "total": "total",
    },
    "generic_gstr2b": {
        "invoice_number": "invoice_number",
        "invoice_date": "invoice_date",
        "supplier_gstin": "supplier_gstin",
        "recipient_gstin": "recipient_gstin",
        "taxable_value": "taxable_value",
        "cgst": "cgst",
        "sgst": "sgst",
        "igst": "igst",
        "cess": "cess",
        "total": "total",
    },
    "tally_purchase": {
        "invoice_number": "Voucher Number",
        "invoice_date": "Date",
        "supplier_gstin": "Party GSTIN",
        "taxable_value": "Taxable Amount",
        "cgst": "CGST",
        "sgst": "SGST",
        "igst": "IGST",
        "total": "Grand Total",
    },
}
