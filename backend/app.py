"""Small runner to initialize the Phase 1 application and MCP client.

This script verifies that the MCP client foundation can be imported
and initialized from environment configuration without performing
any network calls.
"""
from __future__ import annotations

import os
from mcp import MCPClient


def main() -> None:
    print("Initializing Phase 1 application...")
    client = MCPClient()
    print(f"Configured MCP endpoint: {client.endpoint!r}")
    print("MCP client foundation initialized (no network calls were made).")


if __name__ == "__main__":
    main()
