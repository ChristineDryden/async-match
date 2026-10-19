from __future__ import annotations

import json
from typing import Any

from flask import Response, jsonify, request

from server.mcp_tools import call_tool, mcp_tool_list

PROTOCOL = "2025-03-26"
SERVER_INFO = {"name": "async-match", "version": "1.0.0"}


def _ok(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_rpc(body: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
        return _err(body.get("id") if isinstance(body, dict) else None, -32600, "Invalid Request")
    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}
    if method == "initialize":
        return _ok(
            req_id,
            {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            },
        )
    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None
    if method == "ping":
        return _ok(req_id, {})
    if method == "tools/list":
        return _ok(req_id, {"tools": mcp_tool_list()})
    if method == "tools/call":
        name = params.get("name") if isinstance(params, dict) else None
        arguments = params.get("arguments") if isinstance(params, dict) else {}
        if not name:
            return _err(req_id, -32602, "Missing tool name")
        text = call_tool(str(name), arguments if isinstance(arguments, dict) else {})
        is_error = False
        try:
            parsed = json.loads(text)
            is_error = isinstance(parsed, dict) and "error" in parsed
        except json.JSONDecodeError:
            is_error = False
        return _ok(
            req_id,
            {
                "content": [{"type": "text", "text": text}],
                "isError": is_error,
            },
        )
    if req_id is None:
        return None
    return _err(req_id, -32601, f"Method not found: {method}")


def mcp_response():
    if request.method == "GET":
        return jsonify(
            {
                "name": "async-match",
                "transport": "streamable-http",
                "protocolVersion": PROTOCOL,
                "tools": [item["name"] for item in mcp_tool_list()],
            }
        )
    body = request.get_json(silent=True)
    if body is None:
        return jsonify(_err(None, -32700, "Parse error")), 400
    result = handle_rpc(body)
    if result is None:
        return ("", 204)
    accept = request.headers.get("Accept", "")
    if "text/event-stream" in accept:
        payload = f"event: message\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
        return Response(payload, mimetype="text/event-stream")
    return jsonify(result)
