"""
Windows dial-out connector for TallyPrime hosted connector.

Connects to cloud API via WebSocket, pairs with a code, stores device token,
sends heartbeats, and proxies XML requests to local Tally.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import httpx
import websockets
from pydantic import BaseModel, ValidationError

from connector.tally_client import post_xml, probe


# ============================================================================
# Configuration
# ============================================================================


class ConnectorConfig(BaseModel):
    """Stored connector configuration."""
    device_token: str
    api_url: str
    tally_host: str
    tally_port: int


def _app_version() -> str:
    """Best-effort connector version for --version / smoke tests."""
    try:
        from connector import __version__

        return __version__
    except Exception:
        return "0.0.0"


def get_config_path() -> Path:
    """Get the path to the connector config file."""
    home = Path.home()
    config_dir = home / ".accountings"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "tally-connector.json"


def load_config() -> Optional[ConnectorConfig]:
    """Load connector config from disk."""
    config_path = get_config_path()
    if not config_path.exists():
        return None
    try:
        with open(config_path) as f:
            data = json.load(f)
        return ConnectorConfig(**data)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return None


def save_config(config: ConnectorConfig) -> None:
    """Save connector config to disk."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config.model_dump(), f, indent=2)
    # Restrict permissions to owner only
    config_path.chmod(0o600)


# ============================================================================
# Pairing
# ============================================================================


async def pair_connector(api_url: str) -> ConnectorConfig:
    """
    Pair the connector with a code from the cloud API.
    
    Prompts user for:
    - Pairing code (from Settings → Tally)
    - Tally host (default: localhost)
    - Tally port (default: 9000)
    
    Args:
        api_url: Cloud API URL (e.g., http://127.0.0.1:8000)
        
    Returns:
        ConnectorConfig with device_token and settings
        
    Raises:
        ValueError: If pairing fails
    """
    print("\n=== TallyPrime Connector Pairing ===\n")
    
    # Get pairing code
    code = input("Enter pairing code from Settings → Tally: ").strip()
    if not code:
        raise ValueError("Pairing code is required")
    
    # Get Tally host
    tally_host = input("Tally host (default: localhost): ").strip() or "localhost"
    
    # Get Tally port
    tally_port_str = input("Tally port (default: 9000): ").strip() or "9000"
    try:
        tally_port = int(tally_port_str)
    except ValueError:
        raise ValueError(f"Invalid port: {tally_port_str}")
    
    # Verify Tally is reachable
    print(f"\nProbing Tally at {tally_host}:{tally_port}...")
    if not probe(tally_host, tally_port):
        print(
            f"Warning: Could not reach Tally at {tally_host}:{tally_port}. "
            "Make sure TallyPrime is running with XML/ODBC port enabled.",
            file=sys.stderr,
        )
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != "y":
            raise ValueError("Pairing cancelled")
    else:
        print("✓ Tally is reachable")
    
    # Call pairing endpoint
    print(f"\nPairing with {api_url}...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{api_url}/tally/connector/pair",
                json={"code": code, "label": "Windows Connector"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise ValueError(f"Pairing failed: {e}")
    
    device_token = data.get("device_token")
    if not device_token:
        raise ValueError("No device_token in pairing response")
    
    config = ConnectorConfig(
        device_token=device_token,
        api_url=api_url,
        tally_host=tally_host,
        tally_port=tally_port,
    )
    
    save_config(config)
    print(f"✓ Paired successfully. Device token saved to {get_config_path()}")
    return config


# ============================================================================
# WebSocket Connection
# ============================================================================


async def run_connector(config: ConnectorConfig) -> None:
    """
    Run the connector main loop.
    
    Connects to cloud API via WebSocket, sends heartbeats every 10s,
    and handles request/response frames.
    
    Args:
        config: ConnectorConfig with device_token and settings
    """
    api_url = config.api_url
    ws_url = api_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/tally/connector/ws"
    
    print(f"\nConnecting to {ws_url}...")
    
    try:
        async with websockets.connect(
            ws_url,
            subprotocols=[],
            extra_headers={"Authorization": f"Bearer {config.device_token}"},
        ) as websocket:
            print("✓ Connected to cloud API")
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(
                _heartbeat_loop(websocket, config)
            )
            
            # Start message handler task
            handler_task = asyncio.create_task(
                _message_handler(websocket, config)
            )
            
            # Wait for either task to fail
            done, pending = await asyncio.wait(
                [heartbeat_task, handler_task],
                return_when=asyncio.FIRST_EXCEPTION,
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
            
            # Check for exceptions
            for task in done:
                exc = task.exception()
                if exc:
                    raise exc
    
    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket error: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Connection error: {e}", file=sys.stderr)
        raise


async def _heartbeat_loop(websocket: Any, config: ConnectorConfig) -> None:
    """
    Send heartbeat every 10 seconds.
    
    Args:
        websocket: WebSocket connection
        config: ConnectorConfig with Tally settings
    """
    while True:
        try:
            await asyncio.sleep(10)
            tally_ok = probe(config.tally_host, config.tally_port)
            msg = {"type": "heartbeat", "tally_ok": tally_ok}
            await websocket.send(json.dumps(msg))
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Heartbeat error: {e}", file=sys.stderr)
            raise


async def _message_handler(websocket: Any, config: ConnectorConfig) -> None:
    """
    Handle incoming messages from cloud API.
    
    Processes:
    - request: POST XML to Tally, send response
    - auth failure: Print re-pair message
    
    Args:
        websocket: WebSocket connection
        config: ConnectorConfig with Tally settings
    """
    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
            except json.JSONDecodeError:
                print(f"Invalid JSON: {message}", file=sys.stderr)
                continue
            
            msg_type = msg.get("type")
            
            if msg_type == "request":
                await _handle_request(websocket, msg, config)
            elif msg_type == "error":
                error_msg = msg.get("message", "Unknown error")
                if "auth" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    print(
                        "Authentication failed. Re-pair from Settings → Tally",
                        file=sys.stderr,
                    )
                    raise RuntimeError(f"Auth error: {error_msg}")
                else:
                    print(f"Error from cloud: {error_msg}", file=sys.stderr)
    except asyncio.CancelledError:
        pass


async def _handle_request(
    websocket: Any, msg: dict, config: ConnectorConfig
) -> None:
    """
    Handle a request frame from cloud API.
    
    POSTs XML to local Tally and sends response back.
    
    Args:
        websocket: WebSocket connection
        msg: Request message with id, op, args, xml
        config: ConnectorConfig with Tally settings
    """
    req_id = msg.get("id")
    xml = msg.get("xml")
    
    if not req_id or not xml:
        print(f"Invalid request: missing id or xml", file=sys.stderr)
        return
    
    try:
        # POST XML to Tally
        raw_xml = await asyncio.to_thread(
            post_xml,
            config.tally_host,
            config.tally_port,
            xml,
            timeout=20.0,
        )
        
        # Truncate if too large
        if len(raw_xml) > 500_000:
            raw_xml = raw_xml[:500_000]
        
        # Send response
        response = {
            "type": "response",
            "id": req_id,
            "ok": True,
            "data": {"raw_xml": raw_xml},
        }
        await websocket.send(json.dumps(response))
    
    except Exception as e:
        print(f"Request error: {e}", file=sys.stderr)
        response = {
            "type": "response",
            "id": req_id,
            "ok": False,
            "error": str(e),
        }
        await websocket.send(json.dumps(response))


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Main entry point for the connector CLI."""
    # Lightweight arg handling (keep stdlib-only; argparse is fine for one flag).
    if any(a in ("--version", "-V") for a in sys.argv[1:]):
        print(f"AccountingsConnector {_app_version()}")
        sys.exit(0)
    if any(a in ("--help", "-h") for a in sys.argv[1:]):
        print(
            "Accountings Tally Connector\n\n"
            "Usage: AccountingsConnector [--version] [--help]\n\n"
            "On first run you'll be prompted for the pairing code from\n"
            "Accountings → Settings → Tally. Set ACCOUNTINGS_API_URL to point\n"
            "at your cloud API (default: http://127.0.0.1:8000)."
        )
        sys.exit(0)

    # Get API URL from environment or use default
    api_url = os.environ.get("ACCOUNTINGS_API_URL", "http://127.0.0.1:8000")
    
    # Load existing config or pair
    config = load_config()
    if config is None:
        print("No existing configuration found. Starting pairing...")
        try:
            config = asyncio.run(pair_connector(api_url))
        except (ValueError, KeyboardInterrupt) as e:
            print(f"Pairing failed: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Run connector
    print(f"\nStarting connector (API: {config.api_url}, Tally: {config.tally_host}:{config.tally_port})")
    try:
        asyncio.run(run_connector(config))
    except KeyboardInterrupt:
        print("\nConnector stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Connector error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
