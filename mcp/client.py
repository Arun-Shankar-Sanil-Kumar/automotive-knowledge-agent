"""MCP client for Phase 1.

Provides an MCP client that connects to the configured Fetch MCP server,
discovers its tools, and invokes the appropriate tool so the server performs
the actual web retrieval. This module does not implement any direct HTTP
scraping; the target URL is always passed to the MCP server.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional
import requests

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base class for failures raised by the MCP client."""


class MCPConfigurationError(MCPError, ValueError):
    """The MCP server endpoint is missing or invalid."""


class MCPConnectionError(MCPError, ConnectionError):
    """Unable to establish a connection to the MCP server."""


class MCPDiscoveryError(MCPError, RuntimeError):
    """Failed to discover tools via tools/list."""


class MCPToolNotFoundError(MCPError, RuntimeError):
    """No suitable Fetch tool was found in the tool discovery result."""


class MCPInvocationError(MCPError, RuntimeError):
    """Failed to invoke an MCP tool via tools/call."""


class MCPResponseError(MCPError, ValueError):
    """The MCP server returned a malformed or empty response."""


class MCPClient:
    """Minimal MCP client foundation.

    Reads basic configuration from environment variables and exposes
    connect, tool discovery, and tool invocation.
    """

    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self.endpoint = endpoint or os.getenv("MCP_SERVER_ENDPOINT")
        self.api_key = api_key or os.getenv("MCP_API_KEY")

    def connect(self) -> None:
        """Establish connection to the MCP server."""
        if not self.endpoint:
            raise MCPConfigurationError(
                "MCP server endpoint is not configured. Set MCP_SERVER_ENDPOINT"
            )

        try:
            resp = requests.get(self.endpoint, timeout=5)
            resp.raise_for_status()
            self.connected = True
            # Store a lightweight server response for diagnostics; do not assume JSON
            self.server_info = resp.text
            return None
        except requests.Timeout as exc:
            self.connected = False
            logger.debug("MCP connect timed out: %s", self.endpoint, exc_info=True)
            raise MCPConnectionError(
                f"Unable to connect to MCP server at {self.endpoint} (timeout)."
            ) from exc
        except requests.RequestException as exc:
            self.connected = False
            logger.debug("MCP connect failed: %s", self.endpoint, exc_info=True)
            raise MCPConnectionError(
                f"Failed to connect to MCP server at {self.endpoint}: {exc}"
            ) from exc

    def list_tools(self) -> list:
        """Discover available tools exposed by the MCP server.

        Returns a list-like structure describing available tools.
        """
        if not getattr(self, "connected", False):
            # Try a lightweight connect if not already connected
            try:
                self.connect()
            except MCPError:
                raise
            except Exception as exc:
                raise MCPConnectionError(f"Cannot discover tools because MCP connection failed: {exc}") from exc

        if not self.endpoint:
            raise MCPConfigurationError(
                "MCP server endpoint is not configured. Set MCP_SERVER_ENDPOINT"
            )

        url = self.endpoint.rstrip("/") + "/tools/list"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except requests.Timeout as exc:
            logger.debug("tools/list timed out: %s", url, exc_info=True)
            raise MCPDiscoveryError(
                f"Unable to retrieve source within the allowed time (tools/list at {url})."
            ) from exc
        except requests.RequestException as exc:
            logger.debug("tools/list failed: %s", url, exc_info=True)
            raise MCPDiscoveryError(f"Failed to list tools from MCP server at {url}: {exc}") from exc

        # Prefer JSON if possible
        content_type = resp.headers.get("Content-Type", "")
        try:
            if "application/json" in content_type.lower():
                data = resp.json()
            else:
                try:
                    data = resp.json()
                except ValueError:
                    text = resp.text.strip()
                    if not text:
                        raise MCPResponseError(
                            f"MCP server returned an empty tools/list response at {url}."
                        ) from None
                    if "\n" in text:
                        items = [line.strip() for line in text.splitlines() if line.strip()]
                        data = [{"name": it} for it in items]
                    else:
                        data = [{"raw": text}]
        except MCPResponseError:
            raise
        except ValueError as exc:
            logger.debug("tools/list returned malformed JSON: %s", url, exc_info=True)
            raise MCPResponseError(
                f"MCP server returned a malformed tools/list response at {url}: {exc}"
            ) from exc

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
        raise MCPToolNotFoundError(
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
            except MCPConnectionError:
                raise
            except Exception as exc:
                raise MCPConnectionError(f"Cannot invoke tool because MCP connection failed: {exc}") from exc

        if not self.endpoint:
            raise MCPConfigurationError(
                "MCP server endpoint is not configured. Set MCP_SERVER_ENDPOINT"
            )

        url = self.endpoint.rstrip("/") + "/tools/call"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"name": tool_name, "arguments": arguments}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.Timeout as exc:
            logger.debug("tools/call timed out: %s", url, exc_info=True)
            raise MCPInvocationError(
                f"Unable to retrieve source within the allowed time (tools/call at {url})."
            ) from exc
        except requests.RequestException as exc:
            logger.debug("tools/call failed: %s", url, exc_info=True)
            raise MCPInvocationError(f"Failed to invoke tool '{tool_name}': {exc}") from exc
        return self._parse_call_response(resp)

    @staticmethod
    def _parse_call_response(resp: requests.Response) -> Any:
        """Parse a tool call response, returning the raw result structure.

        Raises MCPResponseError if the response is malformed or empty.
        """
        content_type = resp.headers.get("Content-Type", "")
        try:
            data = resp.json()
            if isinstance(data, dict) and "error" in data:
                logger.debug("tools/call returned server error: %s", data)
                raise MCPInvocationError(
                    f"Fetch MCP tool reported an error: {data['error']}"
                )
            return data
        except MCPInvocationError:
            raise
        except ValueError as exc:
            if "application/json" in content_type.lower():
                logger.debug("tools/call returned malformed JSON: %s", resp.text[:200])
                raise MCPResponseError(
                    f"MCP server returned a malformed tools/call response: {exc}"
                ) from exc
            text = resp.text
            if not text.strip():
                raise MCPResponseError(
                    "MCP server returned an empty tools/call response."
                )
            return {"content": text}


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
        matched = False
        for key in ("content", "result", "text", "output", "body", "data", "response"):
            if key in result:
                matched = True
                text = extract_content(result[key])
                if text:
                    return text
        return "" if matched else json.dumps(result, indent=2)
    return str(result)
