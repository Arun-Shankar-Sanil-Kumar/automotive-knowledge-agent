"""Phase 1 URL ingestion runner.

Accepts a URL from the user and retrieves the webpage content through the
Fetch MCP server using the existing MCP client. The application does not
perform any direct HTTP scraping; the Fetch MCP server performs the web
retrieval.
"""
from __future__ import annotations

import logging
import sys

from mcp import MCPClient
from mcp.client import (
    MCPConfigurationError,
    MCPConnectionError,
    MCPDiscoveryError,
    MCPInvocationError,
    MCPResponseError,
    MCPToolNotFoundError,
    extract_content,
)

logger = logging.getLogger(__name__)

MAX_URL_LENGTH = 2048
SUPPORTED_SCHEMES = ("http://", "https://")


class InvalidURLError(ValueError):
    """The supplied URL is not acceptable for ingestion."""


def validate_url(value: str) -> str:
    """Validate the input URL and return it normalized, or raise InvalidURLError."""
    if not isinstance(value, str):
        raise InvalidURLError("Invalid URL.")
    value = value.strip()
    if not value:
        raise InvalidURLError("Invalid URL.")
    if len(value) > MAX_URL_LENGTH:
        raise InvalidURLError("Invalid URL.")
    if " " in value or "\t" in value or "\n" in value:
        raise InvalidURLError("Invalid URL.")
    lower = value.lower()
    if not lower.startswith(SUPPORTED_SCHEMES):
        raise InvalidURLError(
            "Unsupported URL scheme. Only http:// and https:// are supported."
        )
    if not value.split("://", 1)[1]:
        raise InvalidURLError("Invalid URL.")
    return value


def ingest_url(url: str) -> dict:
    """Retrieve a webpage through the Fetch MCP server.

    Connects to the MCP server, discovers its tools, identifies the Fetch
    tool from the discovered tool information, invokes it with the supplied
    URL, and extracts the returned content. Preserves the source URL.

    Raises InvalidURLError for unusable URLs and MCP* exceptions on failure;
    never marks a failed operation as SUCCESS.
    """
    url = validate_url(url)
    client = MCPClient()
    client.connect()
    tools = client.list_tools()
    fetch_tool = client.find_fetch_tool(tools)
    arguments = client.get_tool_arguments(fetch_tool, url)
    result = client.call_tool(fetch_tool["name"], arguments)
    content = extract_content(result)

    if not content.strip():
        return {
            "source": url,
            "tool": fetch_tool["name"],
            "status": "NO_CONTENT",
            "content": "",
        }

    return {
        "source": url,
        "tool": fetch_tool["name"],
        "status": "SUCCESS",
        "content": content,
    }


def report_error(exc: Exception) -> None:
    """Print a concise user-facing error and log the technical detail."""
    if isinstance(exc, InvalidURLError):
        print(exc)
    elif isinstance(exc, MCPConfigurationError):
        print(f"MCP configuration error: {exc}")
    elif isinstance(exc, MCPConnectionError):
        print(f"Unable to connect to Fetch MCP Server: {exc}")
    elif isinstance(exc, MCPDiscoveryError):
        print(f"Unable to discover Fetch MCP tools: {exc}")
    elif isinstance(exc, MCPToolNotFoundError):
        print(f"Unable to locate the Fetch tool: {exc}")
    elif isinstance(exc, MCPInvocationError):
        print(f"Unable to retrieve webpage: {exc}")
    elif isinstance(exc, MCPResponseError):
        print(f"Invalid response from Fetch MCP server: {exc}")
    else:
        logger.exception("Unexpected error during URL ingestion")
        print(f"Unexpected error during URL ingestion: {exc}")


def main() -> None:
    print("========================================")
    print("Automotive Knowledge Ingestion")
    print("========================================")
    print()
    try:
        raw = input("Enter URL: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        print("No URL entered. Exiting.")
        return

    try:
        url = validate_url(raw)
    except InvalidURLError:
        print("Invalid URL.")
        return

    print()
    print("Fetching URL through Fetch MCP...")
    try:
        outcome = ingest_url(url)
    except Exception as exc:
        report_error(exc)
        return

    print()
    print("Source:")
    print(outcome["source"])
    print()
    print("Status:")
    print(outcome["status"])
    print()
    print("Content:")
    print("----------------------------------------")
    print(outcome["content"] or "Webpage retrieved, but no usable content was returned.")
    print("----------------------------------------")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()