"""
Pytest configuration and global fixtures for Ableton Live 12 MCP Test Suite.
"""

import os
import sys
import pytest

# Ensure tests directory is on pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from harness import Live12TestClient


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "tier1: Tier 1 Feature & Protocol Isolation Tests")
    config.addinivalue_line("markers", "tier2: Tier 2 Boundaries, Corners & Resilience Tests")
    config.addinivalue_line("markers", "tier3: Tier 3 Pairwise Subsystem Interaction Tests")
    config.addinivalue_line("markers", "tier4: Tier 4 End-to-End Production Workflows")
    config.addinivalue_line("markers", "tier5: Tier 5 Adversarial Hardening Tests")
    config.addinivalue_line("markers", "live_only: Tests requiring a running Ableton Live 12 instance")


@pytest.fixture
def client():
    """
    Yields a sandboxed Live12TestClient.
    Guarantees full teardown in finally block regardless of test pass/fail.
    """
    test_client = Live12TestClient()
    try:
        yield test_client
    finally:
        test_client.teardown()


@pytest.fixture
def sandbox_track(client):
    """
    Convenience fixture providing a sandboxed track index.
    """
    t_idx, name = client.create_sandboxed_track("midi", "fixture_track")
    return client, t_idx
