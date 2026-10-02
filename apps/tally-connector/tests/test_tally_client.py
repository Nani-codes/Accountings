"""
Tests for the tally_client module.
"""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from connector.tally_client import probe, post_xml


class TestProbe:
    """Tests for probe function."""
    
    def test_probe_success(self):
        """Test successful probe when Tally is running."""
        with patch("connector.tally_client.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = probe("localhost", 9000)
            
            assert result is True
            mock_get.assert_called_once_with(
                "http://localhost:9000",
                timeout=3.0
            )
    
    def test_probe_server_error(self):
        """Test probe with server error (status >= 500)."""
        with patch("connector.tally_client.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            result = probe("localhost", 9000)
            
            assert result is False
    
    def test_probe_client_error(self):
        """Test probe with client error (status < 500)."""
        with patch("connector.tally_client.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = probe("localhost", 9000)
            
            assert result is True
    
    def test_probe_connection_error(self):
        """Test probe when connection fails."""
        with patch("connector.tally_client.httpx.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")
            
            result = probe("localhost", 9000)
            
            assert result is False
    
    def test_probe_timeout(self):
        """Test probe with timeout."""
        with patch("connector.tally_client.httpx.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")
            
            result = probe("localhost", 9000)
            
            assert result is False
    
    def test_probe_custom_timeout(self):
        """Test probe with custom timeout."""
        with patch("connector.tally_client.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = probe("localhost", 9000, timeout=5.0)
            
            assert result is True
            mock_get.assert_called_once_with(
                "http://localhost:9000",
                timeout=5.0
            )
    
    def test_probe_custom_host_port(self):
        """Test probe with custom host and port."""
        with patch("connector.tally_client.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = probe("192.168.1.100", 8080)
            
            assert result is True
            mock_get.assert_called_once_with(
                "http://192.168.1.100:8080",
                timeout=3.0
            )


class TestPostXml:
    """Tests for post_xml function."""
    
    def test_post_xml_success(self):
        """Test successful XML POST."""
        xml_request = '<?xml version="1.0"?><ENVELOPE></ENVELOPE>'
        xml_response = '<?xml version="1.0"?><RESPONSE></RESPONSE>'
        
        with patch("connector.tally_client.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.text = xml_response
            mock_post.return_value = mock_response
            
            result = post_xml("localhost", 9000, xml_request)
            
            assert result == xml_response
            mock_post.assert_called_once_with(
                "http://localhost:9000",
                content=xml_request.encode("utf-8"),
                headers={"Content-Type": "application/xml"},
                timeout=20.0,
            )
    
    def test_post_xml_http_error(self):
        """Test POST with HTTP error."""
        xml_request = '<?xml version="1.0"?><ENVELOPE></ENVELOPE>'
        
        with patch("connector.tally_client.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock()
            )
            mock_post.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                post_xml("localhost", 9000, xml_request)
    
    def test_post_xml_custom_timeout(self):
        """Test POST with custom timeout."""
        xml_request = '<?xml version="1.0"?><ENVELOPE></ENVELOPE>'
        xml_response = '<?xml version="1.0"?><RESPONSE></RESPONSE>'
        
        with patch("connector.tally_client.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.text = xml_response
            mock_post.return_value = mock_response
            
            result = post_xml("localhost", 9000, xml_request, timeout=30.0)
            
            assert result == xml_response
            mock_post.assert_called_once_with(
                "http://localhost:9000",
                content=xml_request.encode("utf-8"),
                headers={"Content-Type": "application/xml"},
                timeout=30.0,
            )
    
    def test_post_xml_custom_host_port(self):
        """Test POST with custom host and port."""
        xml_request = '<?xml version="1.0"?><ENVELOPE></ENVELOPE>'
        xml_response = '<?xml version="1.0"?><RESPONSE></RESPONSE>'
        
        with patch("connector.tally_client.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.text = xml_response
            mock_post.return_value = mock_response
            
            result = post_xml("192.168.1.100", 8080, xml_request)
            
            assert result == xml_response
            mock_post.assert_called_once_with(
                "http://192.168.1.100:8080",
                content=xml_request.encode("utf-8"),
                headers={"Content-Type": "application/xml"},
                timeout=20.0,
            )
    
    def test_post_xml_encoding(self):
        """Test POST with non-ASCII characters."""
        xml_request = '<?xml version="1.0" encoding="utf-8"?><ENVELOPE>नमस्ते</ENVELOPE>'
        xml_response = '<?xml version="1.0"?><RESPONSE></RESPONSE>'
        
        with patch("connector.tally_client.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.text = xml_response
            mock_post.return_value = mock_response
            
            result = post_xml("localhost", 9000, xml_request)
            
            assert result == xml_response
            # Verify encoding was applied
            call_args = mock_post.call_args
            assert call_args[1]["content"] == xml_request.encode("utf-8")
