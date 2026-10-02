from pathlib import Path

import pandas as pd

from app.recon.match import reconcile
from app.recon.normalize import to_invoice

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "recon" / "tiny_pair"


def test_tiny_golden_fixture():
    purchase_df = pd.read_csv(FIXTURE / "purchase.csv")
    gstr_df = pd.read_csv(FIXTURE / "gstr2b.csv")
    purchase = [to_invoice(row.to_dict()) for _, row in purchase_df.iterrows()]
    gstr = [to_invoice(row.to_dict()) for _, row in gstr_df.iterrows()]
    out = reconcile(purchase, gstr)
    expected = pd.read_json(FIXTURE / "expected.json", typ="series")
    assert out.summary["matched"] == int(expected["matched"])
    assert out.summary["exceptions"] == int(expected["exceptions"])
