from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from server import db
from server.config import HOST, PORT
from server.sync import parse_match_time, scrape_since

ROOT = Path(__file__).resolve().parents[1]
app = Flask(__name__)


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.get("/player.html")
def player_page():
    return send_from_directory(ROOT, "player.html")


@app.get("/js/<path:filename>")
def js_files(filename: str):
    return send_from_directory(ROOT / "js", filename)


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


def main() -> None:
    db.init_schema()
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
