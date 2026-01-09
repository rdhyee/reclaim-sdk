"""
Tests for Hours (Time Schemes) resource.
"""

import pytest

from reclaim_sdk.resources.hours import Hours


class TestHoursIntegration:
    """Integration tests for Hours."""

    @pytest.mark.integration
    def test_hours_list(self, client):
        """Can list time schemes."""
        hours = Hours.list(client)
        assert isinstance(hours, list)
        assert len(hours) > 0

    @pytest.mark.integration
    def test_hours_has_expected_fields(self, client):
        """Hours have expected fields."""
        hours = Hours.list(client)
        if hours:
            h = hours[0]
            assert hasattr(h, "id")
            assert hasattr(h, "title")
            assert hasattr(h, "description")
            assert hasattr(h, "status")

    @pytest.mark.integration
    def test_hours_standard_schemes_exist(self, client):
        """Standard time schemes exist."""
        hours = Hours.list(client)
        titles = [h.title for h in hours]

        # Reclaim has these standard time schemes
        expected = ["Working Hours", "Personal Hours", "Meeting Hours"]
        for expected_title in expected:
            assert expected_title in titles, f"Expected '{expected_title}' in {titles}"
