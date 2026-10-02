"""
Read-only Tally XML gateway.

Provides:
- ALLOWED_OPS: set of read-only operations
- assert_op_allowed(op): validates operation is in whitelist
- build_tally_xml(op, args): builds Tally XML export request
- parse_tally_xml(op, xml_text): parses Tally XML response (lenient)
"""

from typing import Any, Dict

# Whitelist of allowed read-only operations
ALLOWED_OPS = {"probe", "list_companies", "ledger_balance", "day_book", "trial_balance"}


def assert_op_allowed(op: str) -> None:
    """
    Validate that an operation is in the allowed whitelist.
    
    Args:
        op: Operation name
        
    Raises:
        ValueError: If operation is not allowed
    """
    if op not in ALLOWED_OPS:
        raise ValueError(f"op not allowed: {op}")


def build_tally_xml(op: str, args: Dict[str, Any]) -> str:
    """
    Build a Tally XML export request for a read-only operation.
    
    Args:
        op: Operation name (must be in ALLOWED_OPS)
        args: Operation arguments (ledger, from, to, etc.)
        
    Returns:
        XML string for Tally export request
        
    Raises:
        ValueError: If operation is not allowed
    """
    assert_op_allowed(op)
    
    if op == "probe":
        return _build_probe_xml()
    elif op == "list_companies":
        return _build_list_companies_xml()
    elif op == "ledger_balance":
        return _build_ledger_balance_xml(args)
    elif op == "day_book":
        return _build_day_book_xml(args)
    elif op == "trial_balance":
        return _build_trial_balance_xml(args)
    else:
        raise ValueError(f"Unknown operation: {op}")


def parse_tally_xml(op: str, xml_text: str) -> Dict[str, Any]:
    """
    Parse Tally XML response (lenient).
    
    If parsing is difficult, returns {"raw_xml_truncated": xml_text[:4000]}
    so the Advisor still has something to work with.
    
    Args:
        op: Operation name
        xml_text: Raw XML response from Tally
        
    Returns:
        Dictionary with parsed data or fallback raw XML
    """
    try:
        if op == "probe":
            return _parse_probe_xml(xml_text)
        elif op == "list_companies":
            return _parse_list_companies_xml(xml_text)
        elif op == "ledger_balance":
            return _parse_ledger_balance_xml(xml_text)
        elif op == "day_book":
            return _parse_day_book_xml(xml_text)
        elif op == "trial_balance":
            return _parse_trial_balance_xml(xml_text)
        else:
            # Fallback for unknown ops
            return {"raw_xml_truncated": xml_text[:4000]}
    except Exception:
        # On any parse error, return truncated raw XML
        return {"raw_xml_truncated": xml_text[:4000]}


# ============================================================================
# XML Builders
# ============================================================================


def _build_probe_xml() -> str:
    """Build lightweight probe request (empty export)."""
    return """<?xml version="1.0" encoding="utf-8"?>
<ENVELOPE RequestType="Export">
  <HEADER>
    <TALLYREQUEST>Export</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Company Info</REPORTNAME>
        <STATICVARIABLES>
          <STATICVARIABLE>
            <NAME>CompanyName</NAME>
            <VALUE></VALUE>
          </STATICVARIABLE>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _build_list_companies_xml() -> str:
    """Build list companies request."""
    return """<?xml version="1.0" encoding="utf-8"?>
<ENVELOPE RequestType="Export">
  <HEADER>
    <TALLYREQUEST>Export</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Company List</REPORTNAME>
        <STATICVARIABLES>
          <STATICVARIABLE>
            <NAME>CompanyName</NAME>
            <VALUE></VALUE>
          </STATICVARIABLE>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _build_ledger_balance_xml(args: Dict[str, Any]) -> str:
    """Build ledger balance request."""
    ledger = args.get("ledger", "")
    from_date = args.get("from", "")
    to_date = args.get("to", "")
    
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ENVELOPE RequestType="Export">
  <HEADER>
    <TALLYREQUEST>Export</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Ledger Balance</REPORTNAME>
        <STATICVARIABLES>
          <STATICVARIABLE>
            <NAME>LedgerName</NAME>
            <VALUE>{ledger}</VALUE>
          </STATICVARIABLE>
          <STATICVARIABLE>
            <NAME>FromDate</NAME>
            <VALUE>{from_date}</VALUE>
          </STATICVARIABLE>
          <STATICVARIABLE>
            <NAME>ToDate</NAME>
            <VALUE>{to_date}</VALUE>
          </STATICVARIABLE>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _build_day_book_xml(args: Dict[str, Any]) -> str:
    """Build day book request."""
    from_date = args.get("from", "")
    to_date = args.get("to", "")
    
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ENVELOPE RequestType="Export">
  <HEADER>
    <TALLYREQUEST>Export</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Day Book</REPORTNAME>
        <STATICVARIABLES>
          <STATICVARIABLE>
            <NAME>FromDate</NAME>
            <VALUE>{from_date}</VALUE>
          </STATICVARIABLE>
          <STATICVARIABLE>
            <NAME>ToDate</NAME>
            <VALUE>{to_date}</VALUE>
          </STATICVARIABLE>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _build_trial_balance_xml(args: Dict[str, Any]) -> str:
    """Build trial balance request."""
    from_date = args.get("from", "")
    to_date = args.get("to", "")
    
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ENVELOPE RequestType="Export">
  <HEADER>
    <TALLYREQUEST>Export</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Trial Balance</REPORTNAME>
        <STATICVARIABLES>
          <STATICVARIABLE>
            <NAME>FromDate</NAME>
            <VALUE>{from_date}</VALUE>
          </STATICVARIABLE>
          <STATICVARIABLE>
            <NAME>ToDate</NAME>
            <VALUE>{to_date}</VALUE>
          </STATICVARIABLE>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


# ============================================================================
# XML Parsers (lenient)
# ============================================================================


def _parse_probe_xml(xml_text: str) -> Dict[str, Any]:
    """Parse probe response (lenient)."""
    # For probe, just return basic structure
    return {"status": "ok", "type": "probe"}


def _parse_list_companies_xml(xml_text: str) -> Dict[str, Any]:
    """Parse list companies response (lenient)."""
    companies = []
    
    # Simple string search for COMPANY tags
    import re
    company_pattern = r"<COMPANY[^>]*>(.*?)</COMPANY>"
    matches = re.findall(company_pattern, xml_text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        # Try to extract NAME
        name_pattern = r"<NAME[^>]*>(.*?)</NAME>"
        name_match = re.search(name_pattern, match, re.IGNORECASE)
        if name_match:
            companies.append({"name": name_match.group(1).strip()})
    
    if companies:
        return {"companies": companies}
    
    # Fallback
    return {"raw_xml_truncated": xml_text[:4000]}


def _parse_ledger_balance_xml(xml_text: str) -> Dict[str, Any]:
    """Parse ledger balance response (lenient)."""
    result = {}
    
    # Try to extract ledger name
    import re
    name_pattern = r"<NAME[^>]*>(.*?)</NAME>"
    name_match = re.search(name_pattern, xml_text, re.IGNORECASE)
    if name_match:
        result["ledger_name"] = name_match.group(1).strip()
    
    # Try to extract opening balance
    opening_pattern = r"<OPENINGBALANCE[^>]*>(.*?)</OPENINGBALANCE>"
    opening_match = re.search(opening_pattern, xml_text, re.IGNORECASE)
    if opening_match:
        result["opening_balance"] = opening_match.group(1).strip()
    
    # Try to extract closing balance
    closing_pattern = r"<CLOSINGBALANCE[^>]*>(.*?)</CLOSINGBALANCE>"
    closing_match = re.search(closing_pattern, xml_text, re.IGNORECASE)
    if closing_match:
        result["closing_balance"] = closing_match.group(1).strip()
    
    if result:
        return result
    
    # Fallback
    return {"raw_xml_truncated": xml_text[:4000]}


def _parse_day_book_xml(xml_text: str) -> Dict[str, Any]:
    """Parse day book response (lenient)."""
    entries = []
    
    # Simple string search for VOUCHER tags
    import re
    voucher_pattern = r"<VOUCHER[^>]*>(.*?)</VOUCHER>"
    matches = re.findall(voucher_pattern, xml_text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        entry = {}
        
        # Try to extract date
        date_pattern = r"<DATE[^>]*>(.*?)</DATE>"
        date_match = re.search(date_pattern, match, re.IGNORECASE)
        if date_match:
            entry["date"] = date_match.group(1).strip()
        
        # Try to extract reference
        ref_pattern = r"<REFERENCE[^>]*>(.*?)</REFERENCE>"
        ref_match = re.search(ref_pattern, match, re.IGNORECASE)
        if ref_match:
            entry["reference"] = ref_match.group(1).strip()
        
        if entry:
            entries.append(entry)
    
    if entries:
        return {"entries": entries}
    
    # Fallback
    return {"raw_xml_truncated": xml_text[:4000]}


def _parse_trial_balance_xml(xml_text: str) -> Dict[str, Any]:
    """Parse trial balance response (lenient)."""
    ledgers = []
    
    # Simple string search for LEDGER tags
    import re
    ledger_pattern = r"<LEDGER[^>]*>(.*?)</LEDGER>"
    matches = re.findall(ledger_pattern, xml_text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        ledger = {}
        
        # Try to extract name
        name_pattern = r"<NAME[^>]*>(.*?)</NAME>"
        name_match = re.search(name_pattern, match, re.IGNORECASE)
        if name_match:
            ledger["name"] = name_match.group(1).strip()
        
        # Try to extract debit
        debit_pattern = r"<DEBIT[^>]*>(.*?)</DEBIT>"
        debit_match = re.search(debit_pattern, match, re.IGNORECASE)
        if debit_match:
            ledger["debit"] = debit_match.group(1).strip()
        
        # Try to extract credit
        credit_pattern = r"<CREDIT[^>]*>(.*?)</CREDIT>"
        credit_match = re.search(credit_pattern, match, re.IGNORECASE)
        if credit_match:
            ledger["credit"] = credit_match.group(1).strip()
        
        if ledger:
            ledgers.append(ledger)
    
    if ledgers:
        return {"ledgers": ledgers}
    
    # Fallback
    return {"raw_xml_truncated": xml_text[:4000]}
