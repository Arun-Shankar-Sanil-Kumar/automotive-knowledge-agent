"""Phase 1 URL ingestion runner.

Accepts a URL from the user and retrieves the webpage content through the
Fetch MCP server using the existing MCP client. The application does not
perform any direct HTTP scraping; the Fetch MCP server performs the web
retrieval.
"""
from __future__ import annotations

from mcp import MCPClient
from mcp.client import extract_content

MAX_URL_LENGTH = 2048


def validate_url(value: str) -> bool:
    """Validate that the input looks like a reasonable HTTP/HTTPS URL."""
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value:
        return False
    if len(value) > MAX_URL_LENGTH:
        return False
    if " " in value or "\t" in value or "\n" in value:
        return False
    lower = value.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        return False
    return bool(value.split("://", 1)[1])


def ingest_url(url: str) -> dict:
    """Retrieve a webpage through the Fetch MCP server.

    Connects to the MCP server, discovers its tools, identifies the Fetch
    tool from the discovered tool information, invokes it with the supplied
    URL, and extracts the returned content. Preserves the source URL.
    """
    client = MCPClient()
    client.connect()
    tools = client.list_tools()
    fetch_tool = client.find_fetch_tool(tools)
    arguments = client.get_tool_arguments(fetch_tool, url)
    result = client.call_tool(fetch_tool["name"], arguments)
    content = extract_content(result)

    return {
        "source": url,
        "tool": fetch_tool["name"],
        "status": "SUCCESS",
        "content": content,
    }


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

    if not validate_url(raw):
        print("Invalid URL.")
        return

    print()
    print("Fetching URL through Fetch MCP...")
    try:
        outcome = ingest_url(raw)
    except ValueError as exc:
        print("MCP configuration error:", exc)
        return
    except ConnectionError as exc:
        print("Unable to connect to Fetch MCP Server:", exc)
        return
    except RuntimeError as exc:
        print("Unable to retrieve webpage:", exc)
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
    content = outcome["content"].strip()
    print(content if content else "Webpage retrieved, but no usable content was returned.")
    print("----------------------------------------")


if __name__ == "__main__":
    main()
