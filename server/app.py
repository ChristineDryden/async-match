from __future__ import annotations

from pathlib import Path

from flask import Flask, abort, jsonify, send_from_directory

from server import db
from server.config import HOST, PORT
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
