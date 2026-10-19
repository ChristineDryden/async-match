from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_ms(iso: str | None) -> int | None:
    if not iso:
        return None
    text = iso.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def filter_matches_by_range(
    matches: list[dict],
    from_ms: int | None,
    to_ms: int | None,
) -> list[dict]:
    out = []
    for match in matches or []:
        ts = _parse_ms(match.get("date"))
        if ts is None:
            continue
        if from_ms is not None and ts < from_ms:
            continue
        if to_ms is not None and ts > to_ms:
            continue
        out.append(match)
    return out


def filter_matches_by_hours(
    matches: list[dict],
    hours: int | None,
    now_ms: int | None = None,
) -> list[dict]:
    if hours is None:
        return list(matches or [])
    now = now_ms if now_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff = now - hours * 60 * 60 * 1000
    return filter_matches_by_range(matches, cutoff, now)


def valid_matches(matches: list[dict] | None) -> list[dict]:
    valid = [
        m
        for m in (matches or [])
        if m
        and m.get("date")
        and m.get("home_player")
        and m.get("away_player")
        and m.get("home_team")
        and m.get("away_team")
        and m.get("home_score") is not None
        and m.get("away_score") is not None
    ]
    valid.sort(key=lambda m: _parse_ms(m.get("date")) or 0)
    return valid


def _record_side(
    bucket: dict[str, dict[str, Any]],
    name: str,
    team: str,
    won: bool,
    scored: int,
    allowed: int,
) -> None:
    row = bucket.get(name)
    if row is None:
        row = bucket[name] = {
            "gp": 0,
            "w": 0,
            "l": 0,
            "pf": 0,
            "pa": 0,
            "results": [],
            "teams": {},
            "last_team": team,
        }
    row["gp"] += 1
    if won:
        row["w"] += 1
    else:
        row["l"] += 1
    row["pf"] += scored
    row["pa"] += allowed
    row["results"].append("W" if won else "L")
    row["teams"][team] = row["teams"].get(team, 0) + 1
    row["last_team"] = team


def _primary_team(stats: dict[str, Any]) -> str:
    best_name = stats["last_team"]
    best_count = -1
    for team, count in stats["teams"].items():
        if count > best_count:
            best_count = count
            best_name = team
    if best_name and stats["teams"].get(best_name) == best_count:
        tied = [team for team, count in stats["teams"].items() if count == best_count]
        if len(tied) > 1:
            return stats["last_team"]
    return best_name


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": row["rank"],
        "player": row["player"],
        "team": row["team"],
        "display": row["display"],
        "p": row["p"],
        "wl": row["wl"],
        "pct": row["pct_display"],
        "win_rate": row["win_rate"],
        "gb": row["gb_display"],
        "l5": row["l5"],
        "strk": row["strk"],
    }


def finish_rows(bucket: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, stats in bucket.items():
        last5 = stats["results"][-5:]
        streak_kind = stats["results"][-1] if stats["results"] else "-"
        streak_n = 0
        for mark in reversed(stats["results"]):
            if mark == streak_kind:
                streak_n += 1
            else:
                break
        team = _primary_team(stats)
        rows.append(
            {
                "player": name,
                "team": team,
                "display": f"{team} ({name})",
                "p": stats["gp"],
                "w": stats["w"],
                "l": stats["l"],
                "pct": (stats["w"] / stats["gp"]) if stats["gp"] else 0.0,
                "pf": stats["pf"],
                "pa": stats["pa"],
                "l5": f"{sum(1 for r in last5 if r == 'W')}-{sum(1 for r in last5 if r == 'L')}",
                "strk": f"{streak_kind} {streak_n}" if streak_n else "-",
            }
        )
    rows.sort(
        key=lambda r: (-r["pct"], -r["w"], r["l"], -(r["pf"] - r["pa"]))
    )
    if rows:
        leader = rows[0]
        for index, row in enumerate(rows):
            gb = (leader["w"] - row["w"] + (row["l"] - leader["l"])) / 2
            row["rank"] = index + 1
            row["wl"] = f"{row['w']}-{row['l']}"
            row["pct_display"] = f"{row['pct']:.3f}"
            row["win_rate"] = f"{row['pct'] * 100:.1f}%"
            row["gb_display"] = "-" if abs(gb) < 1e-9 else f"{gb:.1f}"
    return rows


def compute_player_standings(matches: list[dict] | None) -> list[dict[str, Any]]:
    players: dict[str, dict[str, Any]] = {}
    for match in valid_matches(matches):
        home_win = match["home_score"] > match["away_score"]
        _record_side(
            players,
            match["home_player"],
            match["home_team"],
            home_win,
            int(match["home_score"]),
            int(match["away_score"]),
        )
        _record_side(
            players,
            match["away_player"],
            match["away_team"],
            not home_win,
            int(match["away_score"]),
            int(match["home_score"]),
        )
    return finish_rows(players)


def compute_team_standings(matches: list[dict] | None) -> list[dict[str, Any]]:
    teams: dict[str, dict[str, Any]] = {}
    for match in valid_matches(matches):
        home_win = match["home_score"] > match["away_score"]
        _record_side(
            teams,
            match["home_team"],
            match["home_player"],
            home_win,
            int(match["home_score"]),
            int(match["away_score"]),
        )
        _record_side(
            teams,
            match["away_team"],
            match["away_player"],
            not home_win,
            int(match["away_score"]),
            int(match["home_score"]),
        )
    out = []
    for row in finish_rows(teams):
        team = row["player"]
        player = row["team"]
        copied = dict(row)
        copied["team"] = team
        copied["player"] = player
        copied["display"] = f"{team} ({player})"
        out.append(copied)
    return out


def player_match_log(matches: list[dict] | None, player_name: str) -> list[dict[str, Any]]:
    games = []
    for match in valid_matches(matches):
        if match["home_player"] != player_name and match["away_player"] != player_name:
            continue
        is_home = match["home_player"] == player_name
        player_score = match["home_score"] if is_home else match["away_score"]
        opponent_score = match["away_score"] if is_home else match["home_score"]
        won = player_score > opponent_score
        games.append(
            {
                "id": match["id"],
                "date": match["date"],
                "team": match["home_team"] if is_home else match["away_team"],
                "opponent": match["away_player"] if is_home else match["home_player"],
                "opponent_team": match["away_team"] if is_home else match["home_team"],
                "player_score": player_score,
                "opponent_score": opponent_score,
                "won": won,
                "result": "W" if won else "L",
            }
        )
    games.sort(key=lambda g: _parse_ms(g.get("date")) or 0, reverse=True)
    return games


def opponent_records(log: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    bucket: dict[str, dict[str, Any]] = {}
    for game in log or []:
        name = game["opponent"]
        row = bucket.get(name)
        if row is None:
            row = bucket[name] = {"opponent": name, "p": 0, "w": 0, "l": 0}
        row["p"] += 1
        if game["won"]:
            row["w"] += 1
        else:
            row["l"] += 1
    rows = []
    for row in bucket.values():
        pct = row["w"] / row["p"] if row["p"] else 0.0
        rows.append(
            {
                "opponent": row["opponent"],
                "p": row["p"],
                "wl": f"{row['w']}-{row['l']}",
                "pct": f"{pct:.3f}",
                "win_rate": f"{pct * 100:.1f}%",
            }
        )
    rows.sort(key=lambda r: (-r["p"], -int(r["wl"].split("-")[0]), r["opponent"]))
    return rows


def collect_player_names(matches: list[dict] | None) -> list[str]:
    names: set[str] = set()
    for match in valid_matches(matches):
        names.add(match["home_player"])
        names.add(match["away_player"])
    return sorted(names)


def resolve_player(matches: list[dict] | None, query: str) -> dict[str, Any]:
    q = (query or "").strip()
    names = collect_player_names(matches)
    if not q:
        return {"match": None, "candidates": names[:12]}
    lowered = q.lower()
    exact = [n for n in names if n.lower() == lowered]
    if exact:
        return {"match": exact[0], "candidates": []}
    contains = [n for n in names if lowered in n.lower()]
    if len(contains) == 1:
        return {"match": contains[0], "candidates": []}
    return {"match": None, "candidates": contains[:12] or names[:12]}
