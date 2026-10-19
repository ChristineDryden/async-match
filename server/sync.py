from __future__ import annotations

import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from scrape_valhalla import BASE, fetch_rsc, is_basketball, parse_page  # noqa: E402


def parse_match_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def matches_for_insert(matches: list[dict], watermark: datetime | None) -> list[dict]:
    out = []
    for match in matches:
        played = parse_match_time(match.get("date"))
        if played is None:
            continue
        if watermark is not None and played < watermark:
            continue
        out.append(match)
    return out


def page_reached_before_watermark(page_matches: list[dict], watermark: datetime | None) -> bool:
    if watermark is None or not page_matches:
        return False
    times = [parse_match_time(m.get("date")) for m in page_matches]
    times = [t for t in times if t is not None]
    if not times:
        return False
    return max(times) < watermark


def complete_basketball(match: dict) -> bool:
    return bool(
        is_basketball(match)
        and match.get("id")
        and parse_match_time(match.get("date"))
        and match.get("home_player")
        and match.get("away_player")
        and match.get("home_team")
        and match.get("away_team")
        and match.get("home_score") is not None
        and match.get("away_score") is not None
    )


def scrape_since(watermark: datetime | None, max_pages: int = 80, log=print) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()
    cursor = None
    empty_streak = 0

    for page in range(1, max_pages + 1):
        url = BASE if not cursor else f"{BASE}?r={urllib.parse.quote(cursor, safe='')}"
        try:
            text = fetch_rsc(url)
        except Exception as exc:
            empty_streak += 1
            log(f"page {page} fetch error: {exc}")
            if empty_streak >= 3:
                break
            time.sleep(1)
            continue

        matches, pageinfo = parse_page(text)
        basketball = [m for m in matches if complete_basketball(m) and m["id"] not in seen]
        for rec in basketball:
            seen.add(rec["id"])
        batch = matches_for_insert(basketball, watermark)
        found.extend(batch)
        oldest = matches[-1]["date"] if matches else None
        log(
            f"page {page} mixed={len(matches)} basketball={len(basketball)} "
            f"insertable={len(batch)} last={oldest}"
        )

        if not matches:
            empty_streak += 1
            log(f"page {page} empty payload, retry streak={empty_streak}")
            if empty_streak >= 4:
                break
            time.sleep(1.5)
            continue
        empty_streak = 0

        if page_reached_before_watermark(matches, watermark):
            log("reached matches older than DB watermark, stop")
            break
        if not pageinfo or not pageinfo.get("hasNextPage"):
            break
        cursor = pageinfo["endCursor"]
        time.sleep(0.2)

    return found
