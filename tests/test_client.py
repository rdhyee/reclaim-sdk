"""
Tests for ReclaimClient.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timezone
import httpx

from reclaim_sdk.client import ReclaimClient, ReclaimClientConfig
from reclaim_sdk.exceptions import (
    ReclaimAPIError,
    RecordNotFound,
    InvalidRecord,
    AuthenticationError,
)


class TestReclaimClientConfig:
    """Tests for ReclaimClientConfig."""

    @pytest.mark.unit
    def test_config_with_token(self):
        """Config requires token."""
        config = ReclaimClientConfig(token="test-token")
        assert config.token == "test-token"
        assert config.base_url == "https://api.app.reclaim.ai"

    @pytest.mark.unit
    def test_config_with_custom_base_url(self):
        """Config accepts custom base URL."""
        config = ReclaimClientConfig(
            token="test-token",
            base_url="https://custom.api.com"
        )
        assert config.base_url == "https://custom.api.com"


class TestReclaimClientUnit:
    """Unit tests for ReclaimClient (mocked)."""

    @pytest.mark.unit
    def test_datetime_encoder_utc(self):
        """Datetime encoder converts to UTC ISO format with Z suffix."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = ReclaimClient._datetime_encoder(dt)
        assert result == "2024-01-15T10:30:00Z"

    @pytest.mark.unit
    def test_datetime_encoder_non_datetime_raises(self):
        """Datetime encoder raises TypeError for non-datetime."""
        with pytest.raises(TypeError):
            ReclaimClient._datetime_encoder("not a datetime")

    @pytest.mark.unit
    def test_configure_with_base_url(self):
        """Configure accepts custom base URL."""
        # Reset singleton for test
        ReclaimClient._instance = None
        ReclaimClient._config = None

        client = ReclaimClient.configure(
            token="test-token",
            base_url="https://custom.api.com"
        )
        assert client._config.base_url == "https://custom.api.com"

        # Clean up
        ReclaimClient._instance = None
        ReclaimClient._config = None

    @pytest.mark.unit
    def test_request_handles_empty_200_response(self):
        """Request returns empty dict for empty 200 response."""
        # Reset singleton for test
        ReclaimClient._instance = None
        ReclaimClient._config = None

        client = ReclaimClient.configure(token="test-token")

        # Mock the session.request method
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, 'request', return_value=mock_response):
            result = client.request("POST", "/api/test/enable")
            assert result == {}

        # Clean up
        ReclaimClient._instance = None
        ReclaimClient._config = None

    @pytest.mark.unit
    def test_request_handles_empty_204_response(self):
        """Request returns empty dict for 204 No Content response."""
        # Reset singleton for test
        ReclaimClient._instance = None
        ReclaimClient._config = None

        client = ReclaimClient.configure(token="test-token")

        # Mock the session.request method
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b""
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, 'request', return_value=mock_response):
            result = client.request("DELETE", "/api/test/disable")
            assert result == {}

        # Clean up
        ReclaimClient._instance = None
        ReclaimClient._config = None

    @pytest.mark.unit
    def test_request_parses_json_response(self):
        """Request parses JSON response correctly."""
        # Reset singleton for test
        ReclaimClient._instance = None
        ReclaimClient._config = None

        client = ReclaimClient.configure(token="test-token")

        # Mock the session.request method
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": 123, "title": "Test"}'
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"id": 123, "title": "Test"})

        with patch.object(client.session, 'request', return_value=mock_response):
            result = client.request("GET", "/api/test")
            assert result == {"id": 123, "title": "Test"}

        # Clean up
        ReclaimClient._instance = None
        ReclaimClient._config = None

    @pytest.mark.unit
    def test_request_handles_list_response(self):
        """Request handles list response correctly."""
        # Reset singleton for test
        ReclaimClient._instance = None
        ReclaimClient._config = None

        client = ReclaimClient.configure(token="test-token")

        # Mock the session.request method
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'[{"id": 1}, {"id": 2}]'
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value=[{"id": 1}, {"id": 2}])

        with patch.object(client.session, 'request', return_value=mock_response):
            result = client.request("GET", "/api/test/list")
            assert result == [{"id": 1}, {"id": 2}]
            assert isinstance(result, list)

        # Clean up
        ReclaimClient._instance = None
        ReclaimClient._config = None


class TestReclaimClientIntegration:
    """Integration tests for ReclaimClient."""

    @pytest.mark.integration
    def test_client_singleton(self, client):
        """Client is a singleton."""
        client2 = ReclaimClient()
        assert client is client2

    @pytest.mark.integration
    def test_client_get_user(self, client):
        """Client can fetch current user."""
        user = client.get("/api/users/current")
        assert "id" in user
        assert "email" in user

    @pytest.mark.integration
    def test_client_handles_404(self, client):
        """Client raises RecordNotFound for 404."""
        with pytest.raises(RecordNotFound):
            client.get("/api/tasks/999999999")

    @pytest.mark.integration
    def test_client_handles_forbidden(self, client):
        """Client raises ReclaimAPIError for forbidden endpoints."""
        with pytest.raises(ReclaimAPIError):
            client.get("/api/calendars")
