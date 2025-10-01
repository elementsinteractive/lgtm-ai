import importlib

import pytest

only_if_mcp = pytest.mark.skipif(importlib.util.find_spec("fastmcp") is None, reason="lgtm-ai[mcp] is not installed")
"""Run the test only if lgtm-ai[mcp] is installed."""

only_if_not_mcp = pytest.mark.skipif(
    importlib.util.find_spec("fastmcp") is not None, reason="lgtm-ai[mcp] is installed"
)
"""Run the test only if lgtm-ai[mcp] is NOT installed."""
