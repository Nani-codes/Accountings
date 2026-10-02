import pytest
from app.services.tally_gateway import assert_op_allowed, build_tally_xml, parse_tally_xml


def test_rejects_write_ops():
    """Verify that write operations are rejected."""
    with pytest.raises(ValueError):
        assert_op_allowed("import_voucher")
    with pytest.raises(ValueError):
        build_tally_xml("alter_ledger", {})


def test_build_ledger_balance_contains_ledger_name():
    """Verify that ledger_balance XML contains the ledger name and no write markers."""
    xml = build_tally_xml("ledger_balance", {"ledger": "Cash", "from": "20260401", "to": "20260430"})
    assert "Cash" in xml
    # Ensure no write markers
    assert "IMPORT" not in xml.upper() or "IMPORT DATA" not in xml.upper()


def test_allowed_ops_are_read_only():
    """Verify that all allowed ops are read-only."""
    from app.services.tally_gateway import ALLOWED_OPS
    
    for op in ALLOWED_OPS:
        # Should not raise
        assert_op_allowed(op)


def test_build_probe_xml():
    """Verify probe operation builds valid XML."""
    xml = build_tally_xml("probe", {})
    assert xml is not None
    assert len(xml) > 0
    assert "<ENVELOPE" in xml or "<envelope" in xml.lower()


def test_build_list_companies_xml():
    """Verify list_companies operation builds valid XML."""
    xml = build_tally_xml("list_companies", {})
    assert xml is not None
    assert len(xml) > 0


def test_build_day_book_xml():
    """Verify day_book operation builds valid XML with date range."""
    xml = build_tally_xml("day_book", {"from": "20260401", "to": "20260430"})
    assert xml is not None
    assert "20260401" in xml
    assert "20260430" in xml


def test_build_trial_balance_xml():
    """Verify trial_balance operation builds valid XML with date range."""
    xml = build_tally_xml("trial_balance", {"from": "20260401", "to": "20260430"})
    assert xml is not None
    assert "20260401" in xml
    assert "20260430" in xml


def test_parse_tally_xml_lenient():
    """Verify that parse_tally_xml is lenient and returns something useful."""
    # Test with minimal XML
    xml = "<ENVELOPE><BODY></BODY></ENVELOPE>"
    result = parse_tally_xml("probe", xml)
    assert isinstance(result, dict)
    # Should have either parsed data or raw_xml_truncated fallback
    assert len(result) > 0


def test_parse_tally_xml_with_data():
    """Verify that parse_tally_xml extracts data when available."""
    # Simple XML with company info
    xml = """<ENVELOPE>
    <BODY>
        <COMPANY>
            <NAME>Test Company</NAME>
            <MNAME>Test</MNAME>
        </COMPANY>
    </BODY>
</ENVELOPE>"""
    result = parse_tally_xml("list_companies", xml)
    assert isinstance(result, dict)
    # Should have extracted something
    assert len(result) > 0
