"""
Tests for the main connector module.
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, call
from tempfile import TemporaryDirectory

from connector.main import (
    ConnectorConfig,
    get_config_path,
    load_config,
    save_config,
    pair_connector,
    _handle_request,
)


class TestConnectorConfig:
    """Tests for ConnectorConfig model."""
    
    def test_config_creation(self):
        """Test creating a ConnectorConfig."""
        config = ConnectorConfig(
            device_token="test-token",
            api_url="http://localhost:8000",
            tally_host="localhost",
            tally_port=9000,
        )
        
        assert config.device_token == "test-token"
        assert config.api_url == "http://localhost:8000"
        assert config.tally_host == "localhost"
        assert config.tally_port == 9000
    
    def test_config_model_dump(self):
        """Test serializing ConnectorConfig."""
        config = ConnectorConfig(
            device_token="test-token",
            api_url="http://localhost:8000",
            tally_host="localhost",
            tally_port=9000,
        )
        
        data = config.model_dump()
        assert data == {
            "device_token": "test-token",
            "api_url": "http://localhost:8000",
            "tally_host": "localhost",
            "tally_port": 9000,
        }


class TestConfigPersistence:
    """Tests for config file persistence."""
    
    def test_save_and_load_config(self):
        """Test saving and loading config."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "tally-connector.json"
            
            with patch("connector.main.get_config_path", return_value=config_path):
                # Save config
                config = ConnectorConfig(
                    device_token="test-token",
                    api_url="http://localhost:8000",
                    tally_host="localhost",
                    tally_port=9000,
                )
                save_config(config)
                
                # Verify file exists
                assert config_path.exists()
                
                # Load config
                loaded = load_config()
                assert loaded is not None
                assert loaded.device_token == "test-token"
                assert loaded.api_url == "http://localhost:8000"
                assert loaded.tally_host == "localhost"
                assert loaded.tally_port == 9000
    
    def test_load_config_not_found(self):
        """Test loading config when file doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.json"
            
            with patch("connector.main.get_config_path", return_value=config_path):
                result = load_config()
                assert result is None
    
    def test_load_config_invalid_json(self):
        """Test loading config with invalid JSON."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "tally-connector.json"
            config_path.write_text("invalid json {")
            
            with patch("connector.main.get_config_path", return_value=config_path):
                result = load_config()
                assert result is None
    
    def test_save_config_permissions(self):
        """Test that saved config has restricted permissions."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "tally-connector.json"
            
            with patch("connector.main.get_config_path", return_value=config_path):
                config = ConnectorConfig(
                    device_token="test-token",
                    api_url="http://localhost:8000",
                    tally_host="localhost",
                    tally_port=9000,
                )
                save_config(config)
                
                # Check permissions (0o600 = rw-------)
                mode = config_path.stat().st_mode & 0o777
                assert mode == 0o600


class TestPairing:
    """Tests for pairing functionality."""
    
    @pytest.mark.asyncio
    async def test_pair_connector_success(self):
        """Test successful pairing."""
        with patch("builtins.input") as mock_input, \
             patch("connector.main.probe", return_value=True), \
             patch("connector.main.save_config") as mock_save, \
             patch("connector.main.httpx.AsyncClient") as mock_client_class:
            
            # Setup inputs
            mock_input.side_effect = [
                "ABC123",  # pairing code
                "localhost",  # tally host
                "9000",  # tally port
            ]
            
            # Setup HTTP response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "device_token": "device-token-123",
                "device_id": "device-id-123",
                "ws_url": "/tally/connector/ws",
            }
            
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Run pairing
            config = await pair_connector("http://localhost:8000")
            
            # Verify
            assert config.device_token == "device-token-123"
            assert config.api_url == "http://localhost:8000"
            assert config.tally_host == "localhost"
            assert config.tally_port == 9000
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pair_connector_invalid_port(self):
        """Test pairing with invalid port."""
        with patch("builtins.input") as mock_input:
            mock_input.side_effect = [
                "ABC123",  # pairing code
                "localhost",  # tally host
                "invalid",  # invalid port
            ]
            
            with pytest.raises(ValueError, match="Invalid port"):
                await pair_connector("http://localhost:8000")
    
    @pytest.mark.asyncio
    async def test_pair_connector_empty_code(self):
        """Test pairing with empty code."""
        with patch("builtins.input") as mock_input:
            mock_input.return_value = ""
            
            with pytest.raises(ValueError, match="Pairing code is required"):
                await pair_connector("http://localhost:8000")
    
    @pytest.mark.asyncio
    async def test_pair_connector_tally_unreachable(self):
        """Test pairing when Tally is unreachable."""
        with patch("builtins.input") as mock_input, \
             patch("connector.main.probe", return_value=False):
            
            mock_input.side_effect = [
                "ABC123",  # pairing code
                "localhost",  # tally host
                "9000",  # tally port
                "n",  # don't continue
            ]
            
            with pytest.raises(ValueError, match="Pairing cancelled"):
                await pair_connector("http://localhost:8000")


class TestHandleRequest:
    """Tests for request handling."""
    
    @pytest.mark.asyncio
    async def test_handle_request_success(self):
        """Test successful request handling."""
        mock_websocket = AsyncMock()
        config = ConnectorConfig(
            device_token="token",
            api_url="http://localhost:8000",
            tally_host="localhost",
            tally_port=9000,
        )
        
        msg = {
            "id": "req-123",
            "xml": '<?xml version="1.0"?><ENVELOPE></ENVELOPE>',
        }
        
        with patch("connector.main.post_xml", return_value="<RESPONSE></RESPONSE>"):
            await _handle_request(mock_websocket, msg, config)
        
        # Verify response was sent
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["type"] == "response"
        assert sent_data["id"] == "req-123"
        assert sent_data["ok"] is True
        assert sent_data["data"]["raw_xml"] == "<RESPONSE></RESPONSE>"
    
    @pytest.mark.asyncio
    async def test_handle_request_missing_id(self):
        """Test request handling with missing id."""
        mock_websocket = AsyncMock()
        config = ConnectorConfig(
            device_token="token",
            api_url="http://localhost:8000",
            tally_host="localhost",
            tally_port=9000,
        )
        
        msg = {
            "xml": '<?xml version="1.0"?><ENVELOPE></ENVELOPE>',
        }
        
        await _handle_request(mock_websocket, msg, config)
        
        # Should not send response
        mock_websocket.send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_request_missing_xml(self):
        """Test request handling with missing xml."""
        mock_websocket = AsyncMock()
        config = ConnectorConfig(
            device_token="token",
            api_url="http://localhost:8000",
            tally_host="localhost",
            tally_port=9000,
        )
        
        msg = {
            "id": "req-123",
        }
        
        await _handle_request(mock_websocket, msg, config)
        
        # Should not send response
        mock_websocket.send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_request_xml_truncation(self):
        """Test that large XML responses are truncated."""
        mock_websocket = AsyncMock()
        config = ConnectorConfig(
            device_token="token",
            api_url="http://localhost:8000",
            tally_host="localhost",
            tally_port=9000,
        )
        
        msg = {
            "id": "req-123",
            "xml": '<?xml version="1.0"?><ENVELOPE></ENVELOPE>',
        }
        
        # Create a large response
        large_response = "x" * 600_000
        
        with patch("connector.main.post_xml", return_value=large_response):
            await _handle_request(mock_websocket, msg, config)
        
        # Verify response was truncated
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert len(sent_data["data"]["raw_xml"]) == 500_000
    
    @pytest.mark.asyncio
    async def test_handle_request_error(self):
        """Test request handling with error."""
        mock_websocket = AsyncMock()
        config = ConnectorConfig(
            device_token="token",
            api_url="http://localhost:8000",
            tally_host="localhost",
            tally_port=9000,
        )
        
        msg = {
            "id": "req-123",
            "xml": '<?xml version="1.0"?><ENVELOPE></ENVELOPE>',
        }
        
        with patch("connector.main.post_xml", side_effect=Exception("Connection failed")):
            await _handle_request(mock_websocket, msg, config)
        
        # Verify error response was sent
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["type"] == "response"
        assert sent_data["id"] == "req-123"
        assert sent_data["ok"] is False
        assert "Connection failed" in sent_data["error"]
