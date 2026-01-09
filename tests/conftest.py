"""
Pytest configuration and fixtures for reclaim-sdk tests.

Integration tests require RECLAIM_TOKEN environment variable.
Run with: op run --env-file=<(echo 'RECLAIM_TOKEN="op://..."') -- pytest
"""

import os
import pytest
from typing import Generator

from reclaim_sdk.client import ReclaimClient


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires API access)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no API calls)"
    )


@pytest.fixture(scope="session")
def has_api_token() -> bool:
    """Check if API token is available."""
    return bool(os.environ.get("RECLAIM_TOKEN"))


@pytest.fixture(scope="session")
def client(has_api_token) -> Generator[ReclaimClient, None, None]:
    """
    Provide a configured ReclaimClient for integration tests.

    Skips if RECLAIM_TOKEN is not set.
    """
    if not has_api_token:
        pytest.skip("RECLAIM_TOKEN not set - skipping integration test")

    yield ReclaimClient()


@pytest.fixture
def sample_task_data() -> dict:
    """Sample task data for testing."""
    from datetime import datetime, timedelta

    return {
        "title": "Test Task from pytest",
        "notes": "This is a test task created by pytest",
        "due": datetime.now() + timedelta(days=7),
        "priority": "P3",
    }
