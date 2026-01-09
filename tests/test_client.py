"""
Tests for ReclaimClient.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

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
