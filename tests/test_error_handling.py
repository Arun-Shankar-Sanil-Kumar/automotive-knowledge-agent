"""Offline tests for TASK-05 error handling.

These tests exercise the MCP client and backend error paths using a local
mock MCP server (stdlib http.server) plus direct unit checks. They do NOT
contact a real Fetch MCP server and do NOT fetch real web pages.
"""
from __future__ import annotations

import json
import os
import threading
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler, HTTPServer

from mcp.client import (
    MCPClient,
    MCPConfigurationError,
    MCPConnectionError,
    MCPDiscoveryError,
    MCPInvocationError,
    MCPResponseError,
    MCPToolNotFoundError,
    extract_content,
)
from backend.app import InvalidURLError, ingest_url, validate_url


class MockMCPHandler(BaseHTTPRequestHandler):
    """Serves configurable MCP endpoints for offline testing."""

    mode = "ok"  # ok | no_fetch | list_500 | call_500 | malformed | empty

    FETCH_TOOLS = [
        {
            "name": "fetch",
            "description": "Fetch a URL and return the web page content.",
            "inputSchema": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        }
    ]

    OTHER_TOOLS = [{"name": "other", "description": "Not a fetch tool."}]

    def _send_json(self, code: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_malformed(self) -> None:
        body = b"{not valid json"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/"):
            self._send_json(200, {"status": "ok"})
        elif self.path.rstrip("/") == "/tools/list":
            if self.mode == "list_500":
                self._send_json(500, {"error": "list failed"})
            elif self.mode == "malformed":
                self._send_malformed()
            elif self.mode == "no_fetch":
                self._send_json(200, {"tools": self.OTHER_TOOLS})
            else:
                self._send_json(200, {"tools": self.FETCH_TOOLS})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/tools/call":
            self._send_json(404, {"error": "not found"})
            return
        if self.mode == "call_500":
            self._send_json(500, {"error": "call failed"})
        elif self.mode == "malformed":
            self._send_malformed()
        elif self.mode == "empty":
            self._send_json(200, {"content": []})
        else:
            self._send_json(200, {"content": [{"type": "text", "text": "mock page content"}]})

    def log_message(self, *args):
        pass


class MockMCPServer:
    """Runs the mock MCP server in a background thread."""

    def __init__(self):
        self.server = HTTPServer(("127.0.0.1", 0), MockMCPHandler)
        self.port = self.server.server_address[1]
        self.endpoint = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def setUpModule():
    pass


def tearDownModule():
    pass


class URLValidationTests(unittest.TestCase):
    def test_valid_http_url(self):
        self.assertEqual(validate_url("https://example.com"), "https://example.com")

    def test_valid_http_url_scheme(self):
        self.assertEqual(validate_url("http://example.com/page"), "http://example.com/page")

    def test_invalid_url_rejected(self):
        for bad in ("not-a-url", "", "   ", "http://"):
            with self.assertRaises(InvalidURLError):
                validate_url(bad)

    def test_unsupported_scheme_rejected(self):
        with self.assertRaises(InvalidURLError) as ctx:
            validate_url("ftp://example.com")
        self.assertIn("scheme", str(ctx.exception).lower())

    def test_whitespace_rejected(self):
        with self.assertRaises(InvalidURLError):
            validate_url("https://exa mple.com")


class ExtractContentTests(unittest.TestCase):
    def test_plain_text(self):
        self.assertEqual(extract_content("hello"), "hello")

    def test_mcp_style_text_items(self):
        result = {"content": [{"type": "text", "text": "abc"}]}
        self.assertEqual(extract_content(result), "abc")

    def test_empty_content(self):
        self.assertEqual(extract_content({"content": []}), "")
        self.assertEqual(extract_content(None), "")


class ClientErrorTests(unittest.TestCase):
    def test_missing_configuration(self):
        client = MCPClient(endpoint="")
        with self.assertRaises(MCPConfigurationError):
            client.connect()

    def test_list_tools_missing_configuration(self):
        client = MCPClient(endpoint="")
        with self.assertRaises(MCPConfigurationError):
            client.list_tools()

    def test_connection_failure(self):
        client = MCPClient(endpoint="http://127.0.0.1:1")
        with self.assertRaises(MCPConnectionError):
            client.connect()

    def test_fetch_tool_not_found(self):
        client = MCPClient()
        with self.assertRaises(MCPToolNotFoundError):
            client.find_fetch_tool([{"name": "other"}, {"raw": "text"}])


class MockServerErrorTests(unittest.TestCase):
    server = None

    @classmethod
    def setUpClass(cls):
        cls.server = MockMCPServer()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_successful_ingest(self):
        MockMCPHandler.mode = "ok"
        with unittest.mock.patch.dict(os.environ, {"MCP_SERVER_ENDPOINT": self.server.endpoint}):
            outcome = ingest_url("https://example.com")
        self.assertEqual(outcome["status"], "SUCCESS")
        self.assertEqual(outcome["source"], "https://example.com")
        self.assertIn("mock page content", outcome["content"])

    def test_tools_list_failure(self):
        MockMCPHandler.mode = "list_500"
        with unittest.mock.patch.dict(os.environ, {"MCP_SERVER_ENDPOINT": self.server.endpoint}):
            with self.assertRaises(MCPDiscoveryError):
                ingest_url("https://example.com")

    def test_no_fetch_tool(self):
        MockMCPHandler.mode = "no_fetch"
        with unittest.mock.patch.dict(os.environ, {"MCP_SERVER_ENDPOINT": self.server.endpoint}):
            with self.assertRaises(MCPToolNotFoundError):
                ingest_url("https://example.com")

    def test_tools_call_failure(self):
        MockMCPHandler.mode = "call_500"
        with unittest.mock.patch.dict(os.environ, {"MCP_SERVER_ENDPOINT": self.server.endpoint}):
            with self.assertRaises(MCPInvocationError):
                ingest_url("https://example.com")

    def test_malformed_response(self):
        MockMCPHandler.mode = "malformed"
        with unittest.mock.patch.dict(os.environ, {"MCP_SERVER_ENDPOINT": self.server.endpoint}):
            with self.assertRaises(MCPResponseError):
                ingest_url("https://example.com")

    def test_empty_content_status(self):
        MockMCPHandler.mode = "empty"
        with unittest.mock.patch.dict(os.environ, {"MCP_SERVER_ENDPOINT": self.server.endpoint}):
            outcome = ingest_url("https://example.com")
        self.assertEqual(outcome["status"], "NO_CONTENT")
        self.assertEqual(outcome["content"], "")


class BackendAppTests(unittest.TestCase):
    def test_ingest_url_invalid_url_raises(self):
        with self.assertRaises(InvalidURLError):
            ingest_url("not-a-url")

    def test_ingest_url_missing_config_raises(self):
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(MCPConfigurationError):
                ingest_url("https://example.com")


if __name__ == "__main__":
    unittest.main(verbosity=2)
