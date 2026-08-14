"""
Hound MCP client for anti-bot site acquisition.

Wraps the JSON-RPC / SSE protocol to call Hound's mcp_smart_fetch,
mcp_smart_search, and mcp_screenshot tools over HTTP.
Replaces raw urllib for sources blocked by Cloudflare / Turnstile / DataDome.
"""

import json
import logging
import time
import urllib.request
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

HOUND_URL = "http://127.0.0.1:8765/mcp"
DEFAULT_TIMEOUT = 90


class HoundMCPClient:
    """Lightweight MCP client for Hound server.

    Protocol:
      1. POST initialize → receive mcp-session-id header
      2. POST tools/call with session ID → SSE-stream result
    """

    def __init__(self, endpoint: str = HOUND_URL, timeout: int = DEFAULT_TIMEOUT):
        self.endpoint = endpoint
        self.timeout = timeout
        self._session_id: Optional[str] = None

    # ── public fetch API ──────────────────────────────────────────────

    def smart_fetch(
        self, url: str
    ) -> Tuple[Optional[str], Optional[str], dict]:
        """Fetch a URL via Hound's browser engine.

        Returns (markdown_content, url, metadata_dict).
        On failure returns (None, url, error_meta).
        """
        sid = self._ensure_session()
        payload = {
            "jsonrpc": "2.0",
            "id": id(url),
            "method": "tools/call",
            "params": {
                "name": "mcp_smart_fetch",
                "arguments": {"url": url},
            },
        }
        raw, meta = self._post(payload, sid)
        return self._unpack_fetch(raw, url, meta)

    # ── internal MCP protocol ─────────────────────────────────────────

    def _ensure_session(self) -> str:
        """Return existing session ID or create a new one."""
        if self._session_id:
            return self._session_id
        payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "hound-fetcher", "version": "1.0"},
            },
        }
        raw, meta = self._post(payload, session_id=None)
        # metadata carries the session ID header
        self._session_id = meta.get("session_id")
        if not self._session_id:
            logger.error("Hound initialize returned no session ID")
        return self._session_id

    def _post(
        self, payload: dict, session_id: Optional[str] = None
    ) -> Tuple[str, dict]:
        """POST a JSON-RPC payload to Hound's MCP endpoint.

        Returns (response_body_text, metadata_dict).
        """
        body = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        req = urllib.request.Request(
            self.endpoint, data=body, headers=headers, method="POST"
        )
        meta = {"session_id": session_id}

        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
            meta["session_id"] = resp.headers.get("mcp-session-id", session_id)
            raw = resp.read().decode("utf-8", errors="replace")
            return raw, meta
        except Exception as exc:
            meta["error"] = str(exc)
            logger.warning(f"Hound POST failed: {exc}")
            return "", meta

    @staticmethod
    def _unpack_fetch(
        raw: str, url: str, meta: dict
    ) -> Tuple[Optional[str], str, dict]:
        """Parse SSE stream, extract smart_fetch result text."""
        if not raw:
            return None, url, {**meta, "status": "empty_response"}

        for line in raw.split("\n"):
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
            except json.JSONDecodeError:
                continue

            result = data.get("result", {})
            content = result.get("content", [])
            for c in content:
                text = c.get("text", "")
                if not text:
                    continue
                # Hound wraps JSON inside text for fetch results
                try:
                    inner = json.loads(text)
                except json.JSONDecodeError:
                    return text, url, {**meta, "status": "raw_text"}

                status = inner.get("status", 0)
                if status != 200:
                    error_msg = inner.get("content", [str(inner)])[0] if inner.get("content") else str(inner)
                    return None, url, {**meta, "status": "fetch_error", "error": error_msg}

                content_list = inner.get("content", [])
                if content_list:
                    markdown_text = content_list[0]
                    return markdown_text, inner.get("url", url), {**meta, "status": "ok"}

        return None, url, {**meta, "status": "no_content"}

    @staticmethod
    def _unpack_tools(raw: str) -> list:
        """Parse SSE stream and extract tools/list result."""
        for line in raw.split("\n"):
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            result = data.get("result", {})
            return result.get("tools", [])
        return []
