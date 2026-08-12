"""MCP client foundation for Phase 1.

This module provides a minimal MCP client class used as a foundation
for later integration with an external Fetch MCP server. It intentionally
does not implement network calls yet — those will be added in TASK-02.
"""
from __future__ import annotations

import os
from typing import Optional


class MCPClient:
    """Minimal MCP client foundation.

    Reads basic configuration from environment variables and exposes
    stubs for connect and tool discovery.
    """

    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self.endpoint = endpoint or os.getenv("MCP_SERVER_ENDPOINT")
        self.api_key = api_key or os.getenv("MCP_API_KEY")

    def connect(self) -> None:
        """Establish connection to MCP server.

        Not implemented in TASK-01; this is a placeholder to be implemented
        in the next task that actually integrates with a Fetch MCP server.
        """
        raise NotImplementedError("MCP server connection not implemented yet")

    def list_tools(self) -> list:
        """Discover available tools exposed by the MCP server.

        Returns a list-like structure describing available tools. Not implemented
        in TASK-01; present as a defined API for future work.
        """
        raise NotImplementedError("Tool discovery not implemented yet")
