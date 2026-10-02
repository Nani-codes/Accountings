from __future__ import annotations

from typing import Any

import pandas as pd

from app.recon.templates import OPTIONAL_TAX_FIELDS, REQUIRED_FIELDS


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> list[dict[str, Any]]:
    missing = [f for f in REQUIRED_FIELDS if f not in mapping]
    if missing:
        raise ValueError(f"Missing required mapping fields: {', '.join(missing)}")

    missing_cols = [col for col in mapping.values() if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Columns not found in file: {', '.join(missing_cols)}")

    rows: list[dict[str, Any]] = []
    for _, series in df.iterrows():
        row: dict[str, Any] = {}
        for field, col in mapping.items():
            row[field] = series[col]
        for tax in OPTIONAL_TAX_FIELDS:
            if tax not in row:
                row[tax] = 0 if tax != "recipient_gstin" else None
        rows.append(row)
    return rows
