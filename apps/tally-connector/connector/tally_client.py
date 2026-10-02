"""
Local Tally HTTP client for XML requests.

Provides:
- probe(host, port, timeout): Check if Tally is running
- post_xml(host, port, xml, timeout): POST XML to Tally and get response
"""

import httpx


def probe(host: str, port: int, timeout: float = 3.0) -> bool:
    """
    Probe if Tally is running on the given host:port.
    
    Args:
        host: Tally host (usually "localhost")
        port: Tally port (usually 9000)
        timeout: Probe timeout in seconds
        
    Returns:
        True if Tally responds with status < 500, False otherwise
    """
    try:
        r = httpx.get(f"http://{host}:{port}", timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False


def post_xml(host: str, port: int, xml: str, timeout: float = 20.0) -> str:
    """
    POST XML to Tally and return the response.
    
    Args:
        host: Tally host (usually "localhost")
        port: Tally port (usually 9000)
        xml: XML request string
        timeout: Request timeout in seconds
        
    Returns:
        Response text from Tally
        
    Raises:
        httpx.HTTPError: If the request fails
    """
    r = httpx.post(
        f"http://{host}:{port}",
        content=xml.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.text
