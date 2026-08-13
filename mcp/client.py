"""MCP client foundation for Phase 1.

This module provides a minimal MCP client class used as a foundation
for later integration with an external Fetch MCP server. It intentionally
does not implement network calls yet — those will be added in TASK-02.
"""
from __future__ import annotations

import os
from typing import Optional
import requests


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
        if not self.endpoint:
            raise ValueError("MCP server endpoint is not configured. Set MCP_SERVER_ENDPOINT")

        try:
            resp = requests.get(self.endpoint, timeout=5)
            resp.raise_for_status()
            self.connected = True
            # Store a lightweight server response for diagnostics; do not assume JSON
            self.server_info = resp.text
            return None
        except requests.RequestException as exc:
            self.connected = False
            raise ConnectionError(f"Failed to connect to MCP server at {self.endpoint}: {exc}") from exc

    def list_tools(self) -> list:
        """Discover available tools exposed by the MCP server.

        Returns a list-like structure describing available tools. Not implemented
        in TASK-01; present as a defined API for future work.
        """
        if not getattr(self, "connected", False):
            # Try a lightweight connect if not already connected
            try:
                self.connect()
            except Exception as exc:
                raise ConnectionError(f"Cannot discover tools because MCP connection failed: {exc}") from exc

        if not self.endpoint:
            raise ValueError("MCP server endpoint is not configured. Set MCP_SERVER_ENDPOINT")

        url = self.endpoint.rstrip("/") + "/tools/list"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()

            # Prefer JSON if possible
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type.lower():
                data = resp.json()
            else:
                # Attempt JSON parse as fallback, otherwise treat as plain text
                try:
                    data = resp.json()
                except Exception:
                    text = resp.text.strip()
                    # If response looks like a newline-separated list, convert to dicts
                    if text and "\n" in text:
                        items = [line.strip() for line in text.splitlines() if line.strip()]
                        data = [{"name": it} for it in items]
                    else:
                        # Last resort: wrap raw text
                        data = [{"raw": text}]

            # Normalize to a list of tool descriptions
            if isinstance(data, dict):
                # Some servers return {"tools": [...]}
                if "tools" in data and isinstance(data["tools"], list):
                    tools = data["tools"]
                else:
                    # Wrap the dict in a list
                    tools = [data]
            elif isinstance(data, list):
                tools = data
            else:
                tools = [data]

            return tools
        except requests.RequestException as exc:
            raise ConnectionError(f"Failed to list tools from MCP server at {url}: {exc}") from exc
