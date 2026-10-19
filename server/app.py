from __future__ import annotations

from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

from server import db
from server.chat import run_chat
from server.config import HOST, PORT
from server.mcp_http import mcp_response
from server.sync import parse_match_time, scrape_since

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = ROOT / "frontend" / "dist"
app = Flask(__name__)


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/api/<path:_rest>", methods=["OPTIONS"])
def api_preflight(_rest: str):
    return ("", 204)


@app.get("/api/health")
def api_health():
    return jsonify({"ok": True})


@app.get("/api/matches")
def api_matches():
    db.init_schema()
    matches = db.list_matches()
    latest = db.latest_played_at()
    return jsonify(
        {
            "matches": matches,
            "count": len(matches),
            "latest": latest.isoformat().replace("+00:00", "Z") if latest else None,
        }
    )


@app.post("/api/chat")
def api_chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message")
    messages = data.get("messages")
    try:
        result = run_chat(
            message=str(message or "") if message else None,
            messages=messages if isinstance(messages, list) else None,
        )
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Grok 调用失败：{exc}"}), 502


@app.route("/mcp", methods=["GET", "POST", "OPTIONS"])
def mcp_endpoint():
    if request.method == "OPTIONS":
        return ("", 204)
    return mcp_response()


@app.post("/api/sync")
def api_sync():
    db.init_schema()
    watermark = db.latest_played_at()
    scraped = scrape_since(watermark, max_pages=80)
    inserted, skipped = db.insert_matches(scraped, parse_match_time)
    latest = db.latest_played_at()
    return jsonify(
        {
            "watermark": watermark.isoformat().replace("+00:00", "Z") if watermark else None,
            "scanned": len(scraped),
            "inserted": inserted,
            "skipped": skipped,
            "latest": latest.isoformat().replace("+00:00", "Z") if latest else None,
            "total": db.match_count(),
        }
    )


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def spa(path: str):
    if path.startswith("api/"):
        abort(404)
    if not FRONTEND_DIST.exists():
        return (
            jsonify(
                {
                    "error": "frontend not built",
                    "hint": "cd frontend && npm install && npm run build",
                }
            ),
            503,
        )
    target = FRONTEND_DIST / path
    if path and target.is_file():
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


def main() -> None:
    db.init_schema()
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
