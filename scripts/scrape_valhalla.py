#!/usr/bin/env python3
"""Scrape Valhalla League results from drafted.gg and keep basketball only."""

from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://drafted.gg/en/valhalla-league/results"

NBA_TEAMS = {
    "Atlanta Hawks",
    "Boston Celtics",
    "Brooklyn Nets",
    "Charlotte Hornets",
    "Chicago Bulls",
    "Cleveland Cavaliers",
    "Dallas Mavericks",
    "Denver Nuggets",
    "Detroit Pistons",
    "Golden State Warriors",
    "Houston Rockets",
    "Indiana Pacers",
    "LA Clippers",
    "Los Angeles Clippers",
    "Los Angeles Lakers",
    "Memphis Grizzlies",
    "Miami Heat",
    "Milwaukee Bucks",
    "Minnesota Timberwolves",
    "New Orleans Pelicans",
    "New York Knicks",
    "Oklahoma City Thunder",
    "Orlando Magic",
    "Philadelphia 76ers",
    "Phoenix Suns",
    "Portland Trail Blazers",
    "Sacramento Kings",
    "San Antonio Spurs",
    "Toronto Raptors",
    "Utah Jazz",
    "Washington Wizards",
}


def fetch_rsc(url: str) -> str:
    last = ""
    for attempt in range(3):
        result = subprocess.run(
            [
                "curl",
                "-sL",
                "-H",
                "RSC: 1",
                "-H",
                "Accept: text/x-component",
                "-H",
                "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "--globoff",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        last = result.stdout or ""
        if result.returncode == 0 and len(last) > 2000:
            return last
        time.sleep(1 + attempt)
    return last


def parse_page(text: str) -> tuple[list[dict], dict | None]:
    matches: list[dict] = []
    seen: set[str] = set()
    for m in re.finditer(r'"children":"Match (\d+)"', text):
        mid = m.group(1)
        if mid in seen:
            continue
        seen.add(mid)
        pre = text[max(0, m.start() - 3500) : m.start()]
        window = text[m.start() : m.start() + 4500]
        date_m = re.search(r'"date":"\$D([^"]+)"', window)
        score_m = re.search(r'"children":"(\d+) - (\d+)"', window)
        periods_m = re.search(r'"periods":\{"type":"([^"]+)"', window)
        ha = re.search(
            r'"home":\{"name":"([^"]+)".*?"away":\{"name":"([^"]+)"',
            window,
        )
        home_team_m = re.findall(
            r'"className":"font-nunito text-right[^"]*","children":"([^"]+)"',
            pre,
        )
        away_team_m = re.findall(
            r'"className":"font-nunito text-left[^"]*","children":"([^"]+)"',
            window,
        )
        matches.append(
            {
                "id": mid,
                "date": date_m.group(1) if date_m else None,
                "home_score": int(score_m.group(1)) if score_m else None,
                "away_score": int(score_m.group(2)) if score_m else None,
                "period_type": periods_m.group(1) if periods_m else None,
                "home_team": home_team_m[-1] if home_team_m else None,
                "away_team": away_team_m[0] if away_team_m else None,
                "home_player": ha.group(1) if ha else None,
                "away_player": ha.group(2) if ha else None,
            }
        )

    pag = re.search(
        r'"hasNextPage":(true|false),"hasPreviousPage":(true|false),'
        r'"startCursor":"([^"]+)","endCursor":"([^"]+)"',
        text,
    )
    pageinfo = None
    if pag:
        pageinfo = {
            "hasNextPage": pag.group(1) == "true",
            "endCursor": pag.group(4),
        }
    return matches, pageinfo


def is_basketball(match: dict) -> bool:
    return match.get("home_team") in NBA_TEAMS or match.get("away_team") in NBA_TEAMS


def scrape(max_pages: int = 40) -> list[dict]:
    all_matches: list[dict] = []
    seen_ids: set[str] = set()
    cursor = None
    empty_streak = 0

    for page in range(1, max_pages + 1):
        url = BASE if not cursor else f"{BASE}?r={urllib.parse.quote(cursor, safe='')}"
        try:
            text = fetch_rsc(url)
        except subprocess.CalledProcessError:
            empty_streak += 1
            if empty_streak >= 3:
                break
            time.sleep(1)
            continue

        matches, pageinfo = parse_page(text)
        new = 0
        for rec in matches:
            if rec["id"] in seen_ids:
                continue
            seen_ids.add(rec["id"])
            all_matches.append(rec)
            new += 1

        last = matches[-1]["date"] if matches else None
        print(f"page {page} new={new} total={len(all_matches)} last={last}", flush=True)

        if new == 0:
            empty_streak += 1
            if empty_streak >= 2:
                break
            time.sleep(1)
            continue

        empty_streak = 0
        if not pageinfo or not pageinfo.get("hasNextPage"):
            break
        cursor = pageinfo["endCursor"]
        time.sleep(0.2)

    return all_matches


def finish_rows(buckets: dict) -> list[dict]:
    rows = []
    for name, stats in buckets.items():
        gp = stats["gp"]
        pct = stats["w"] / gp if gp else 0
        last5 = stats["results"][-5:]
        streak_kind = stats["results"][-1] if stats["results"] else "-"
        streak_n = 0
        for result in reversed(stats["results"]):
            if result == streak_kind:
                streak_n += 1
            else:
                break
        rows.append(
            {
                "key": name,
                "label": stats["label"],
                "p": gp,
                "w": stats["w"],
                "l": stats["l"],
                "pct": pct,
                "pf": stats["pf"],
                "pa": stats["pa"],
                "l5": f"{last5.count('W')}-{last5.count('L')}",
                "strk": f"{streak_kind} {streak_n}" if streak_n else "-",
            }
        )
    rows.sort(key=lambda row: (-row["pct"], -row["w"], row["l"], -(row["pf"] - row["pa"])))
    if rows:
        leader = rows[0]
        for row in rows:
            gb = ((leader["w"] - row["w"]) + (row["l"] - leader["l"])) / 2.0
            row["gb"] = "-" if abs(gb) < 1e-9 else gb
            row["pctDisplay"] = f"{row['pct']:.3f}"
            row["wl"] = f"{row['w']}-{row['l']}"
            row["gbDisplay"] = row["gb"] if row["gb"] == "-" else f"{row['gb']:.1f}"
    return rows


def build_standings(games: list[dict]) -> dict:
    valid = [
        m
        for m in games
        if m.get("home_score") is not None
        and m.get("away_score") is not None
        and m.get("home_team")
        and m.get("away_team")
        and m.get("home_player")
        and m.get("away_player")
    ]
    chronological = sorted(valid, key=lambda m: m["date"] or "")

    teams = defaultdict(
        lambda: {
            "gp": 0,
            "w": 0,
            "l": 0,
            "pf": 0,
            "pa": 0,
            "results": [],
            "players": Counter(),
        }
    )
    players = defaultdict(
        lambda: {
            "gp": 0,
            "w": 0,
            "l": 0,
            "pf": 0,
            "pa": 0,
            "results": [],
            "teams": Counter(),
        }
    )

    for match in chronological:
        home_win = match["home_score"] > match["away_score"]
        for side, won in (("home", home_win), ("away", not home_win)):
            team = match[f"{side}_team"]
            player = match[f"{side}_player"]
            scored = match[f"{side}_score"]
            allowed = match["away_score"] if side == "home" else match["home_score"]

            t = teams[team]
            t["gp"] += 1
            t["w"] += int(won)
            t["l"] += int(not won)
            t["pf"] += scored
            t["pa"] += allowed
            t["results"].append("W" if won else "L")
            t["players"][player] += 1

            p = players[player]
            p["gp"] += 1
            p["w"] += int(won)
            p["l"] += int(not won)
            p["pf"] += scored
            p["pa"] += allowed
            p["results"].append("W" if won else "L")
            p["teams"][team] += 1

    for stats in teams.values():
        stats["label"] = stats["players"].most_common(1)[0][0]
    for stats in players.values():
        stats["label"] = stats["teams"].most_common(1)[0][0]

    team_rows = finish_rows(teams)
    player_rows = finish_rows(players)

    def pack(rows, team_first: bool):
        packed = []
        for i, row in enumerate(rows, 1):
            team = row["key"] if team_first else row["label"]
            player = row["label"] if team_first else row["key"]
            packed.append(
                {
                    "rank": i,
                    "team": team,
                    "player": player,
                    "display": f"{team} ({player})",
                    "p": row["p"],
                    "w": row["w"],
                    "l": row["l"],
                    "wl": row["wl"],
                    "pct": row["pct"],
                    "pctDisplay": row["pctDisplay"],
                    "gb": row["gb"],
                    "gbDisplay": row["gbDisplay"],
                    "l5": row["l5"],
                    "strk": row["strk"],
                    "pf": row["pf"],
                    "pa": row["pa"],
                }
            )
        return packed

    newest_first = sorted(chronological, key=lambda m: m["date"] or "", reverse=True)
    return {
        "source": "https://drafted.gg/valhalla-league/results",
        "scrapedAt": datetime.now(timezone.utc).isoformat(),
        "window": {
            "from": chronological[0]["date"] if chronological else None,
            "to": chronological[-1]["date"] if chronological else None,
        },
        "gameCount": len(chronological),
        "teamStandings": pack(team_rows, True),
        "playerStandings": pack(player_rows, False),
        "matches": [
            {**match, "homeWin": match["home_score"] > match["away_score"]}
            for match in newest_first
        ],
    }


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    mixed = scrape(max_pages=40)
    basketball = [m for m in mixed if is_basketball(m)]
    print(f"mixed={len(mixed)} basketball={len(basketball)}")
    payload = build_standings(basketball)
    (DATA / "matches.json").write_text(json.dumps(basketball, indent=2), encoding="utf-8")
    (DATA / "standings.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {DATA / 'standings.json'}")


if __name__ == "__main__":
    main()
