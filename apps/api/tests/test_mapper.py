import pandas as pd
import pytest

from app.recon.mapper import apply_mapping


def test_apply_mapping_renames_columns():
    df = pd.DataFrame(
        {
            "Inv No": ["A-1"],
            "GSTIN": ["29ABCDE1234F1Z5"],
            "Taxable": [1000],
            "Date": ["2026-03-01"],
            "Total": [1180],
        }
    )
    mapping = {
        "invoice_number": "Inv No",
        "supplier_gstin": "GSTIN",
        "taxable_value": "Taxable",
        "invoice_date": "Date",
        "total": "Total",
    }
    rows = apply_mapping(df, mapping)
    assert rows[0]["invoice_number"] == "A-1"
    assert rows[0]["supplier_gstin"] == "29ABCDE1234F1Z5"
    assert rows[0]["cgst"] == 0


def test_apply_mapping_rejects_missing_required():
    df = pd.DataFrame({"Inv No": ["A-1"]})
    with pytest.raises(ValueError) as exc:
        apply_mapping(df, {"invoice_number": "Inv No"})
    assert "supplier_gstin" in str(exc.value)
