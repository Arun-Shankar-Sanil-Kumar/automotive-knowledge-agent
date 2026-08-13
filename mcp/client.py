"""MCP client for Phase 1.

Provides an MCP client that connects to the configured Fetch MCP server,
discovers its tools, and invokes the appropriate tool so the server performs
the actual web retrieval. This module does not implement any direct HTTP
scraping; the target URL is always passed to the MCP server.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional
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

    def find_fetch_tool(self, tools: Optional[list] = None) -> dict:
        """Identify the Fetch tool from the discovered tool information.

        Uses the actual tool metadata returned by the MCP server instead of
        assuming a fixed tool name. Prefers an exact ``fetch`` match and then
        falls back to any tool whose name contains ``fetch``.
        """
        if tools is None:
            tools = self.list_tools()

        named = []
        for tool in tools:
            if isinstance(tool, dict) and tool.get("name"):
                named.append(tool)

        for tool in named:
            if tool["name"] == "fetch":
                return tool
        for tool in named:
            if "fetch" in tool["name"].lower():
                return tool
        raise RuntimeError(
            "No Fetch tool found among the tools discovered on the MCP server"
        )

    def get_tool_arguments(self, tool: dict, url: str) -> dict:
        """Build the invocation arguments for a tool from its input schema.

        The argument key is derived from the tool's declared input schema
        (preferring a ``url`` property) so that the actual schema returned by
        the MCP server is respected.
        """
        schema = tool.get("inputSchema")
        if not isinstance(schema, dict):
            schema = tool.get("parameters") if isinstance(tool.get("parameters"), dict) else {}

        properties = schema.get("properties")
        required = schema.get("required") if isinstance(schema.get("required"), list) else []

        if isinstance(properties, dict):
            if "url" in properties:
                return {"url": url}
            if required:
                return {required[0]: url}
            if properties:
                return {next(iter(properties)): url}

        return {"url": url}

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Invoke an MCP tool on the server and return the raw result.

        The tool invocation is sent to the MCP server; the server (not this
        client) performs any external work such as fetching the web page.
        """
        if not getattr(self, "connected", False):
            try:
                self.connect()
            except Exception as exc:
                raise ConnectionError(f"Cannot invoke tool because MCP connection failed: {exc}") from exc

        if not self.endpoint:
            raise ValueError("MCP server endpoint is not configured. Set MCP_SERVER_ENDPOINT")

        url = self.endpoint.rstrip("/") + "/tools/call"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"name": tool_name, "arguments": arguments}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return self._parse_call_response(resp)
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to invoke tool '{tool_name}': {exc}") from exc

    @staticmethod
    def _parse_call_response(resp: requests.Response) -> Any:
        """Parse a tool call response, returning the raw result structure."""
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type.lower():
            try:
                return resp.json()
            except ValueError:
                pass
        try:
            return resp.json()
        except ValueError:
            return {"content": resp.text}


def extract_content(result: Any) -> str:
    """Extract readable text from a tool call result.

    Handles plain text, JSON objects, and MCP-style result payloads such as
    ``{"content": [...]}``, ``{"result": ...}``, or content items of the form
    ``{"type": "text", "text": "..."}``.
    """
    if isinstance(result, str):
        return result
    if result is None:
        return ""
    if isinstance(result, list):
        parts = []
        for item in result:
            text = extract_content(item)
            if text:
                parts.append(text)
        return "\n".join(parts)
    if isinstance(result, dict):
        for key in ("content", "result", "text", "output", "body", "data", "response"):
            if key in result:
                text = extract_content(result[key])
                if text:
                    return text
        return json.dumps(result, indent=2)
    return str(result)
