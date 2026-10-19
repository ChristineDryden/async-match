from __future__ import annotations

import math
from typing import Any

from server.standings import player_match_log, valid_matches

BASE_RATING = 1500.0
K_FACTOR = 32.0
SCALE = 400.0


def expected_score(rating: float, opponent: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((opponent - rating) / SCALE))


def win_probability(rating_a: float, rating_b: float) -> float:
    return expected_score(rating_a, rating_b)


def _mov_multiplier(margin: int) -> float:
    return max(0.5, math.log10(abs(margin) + 1.0))


def compute_elo(matches: list[dict] | None) -> dict[str, dict[str, Any]]:
    ratings: dict[str, float] = {}
    games: dict[str, int] = {}
    for match in valid_matches(matches):
        home = match["home_player"]
        away = match["away_player"]
        home_score = int(match["home_score"])
        away_score = int(match["away_score"])
        ra = ratings.get(home, BASE_RATING)
        rb = ratings.get(away, BASE_RATING)
        ea = expected_score(ra, rb)
        eb = 1.0 - ea
        sa = 1.0 if home_score > away_score else 0.0
        sb = 1.0 - sa
        margin = abs(home_score - away_score)
        k = K_FACTOR * _mov_multiplier(margin)
        ratings[home] = ra + k * (sa - ea)
        ratings[away] = rb + k * (sb - eb)
        games[home] = games.get(home, 0) + 1
        games[away] = games.get(away, 0) + 1
    out = {}
    for name, rating in ratings.items():
        out[name] = {
            "player": name,
            "elo": round(rating, 1),
            "games": games.get(name, 0),
        }
    return out


def elo_table(matches: list[dict] | None, top_n: int = 20) -> list[dict[str, Any]]:
    rows = sorted(
        compute_elo(matches).values(),
        key=lambda r: (-r["elo"], r["player"]),
    )
    for index, row in enumerate(rows):
        row["rank"] = index + 1
    return rows[: max(1, top_n)]


def _confidence(games_a: int, games_b: int) -> str:
    sample = min(games_a, games_b)
    if sample < 5:
        return "low"
    if sample < 12:
        return "medium"
    return "high"


def predict_matchup(matches: list[dict] | None, player_a: str, player_b: str) -> dict[str, Any]:
    table = compute_elo(matches)
    a = table.get(player_a)
    b = table.get(player_b)
    if not a or not b:
        return {
            "error": "选手没有足够的已入库比赛，无法计算 Elo",
            "player_a": player_a,
            "player_b": player_b,
            "known": sorted(table),
        }
    elo_a = float(a["elo"])
    elo_b = float(b["elo"])
    p_a = win_probability(elo_a, elo_b)
    p_b = 1.0 - p_a
    log = [g for g in player_match_log(matches, player_a) if g["opponent"] == player_b]
    a_wins = sum(1 for g in log if g["won"])
    return {
        "model": "elo",
        "k_factor": K_FACTOR,
        "player_a": player_a,
        "player_b": player_b,
        "elo_a": elo_a,
        "elo_b": elo_b,
        "p_a_win": round(p_a, 4),
        "p_b_win": round(p_b, 4),
        "p_a_win_pct": f"{p_a * 100:.1f}%",
        "p_b_win_pct": f"{p_b * 100:.1f}%",
        "games_a": a["games"],
        "games_b": b["games"],
        "confidence": _confidence(int(a["games"]), int(b["games"])),
        "h2h_games": len(log),
        "h2h_record": f"{a_wins}-{len(log) - a_wins}",
        "h2h_a_wins": a_wins,
        "h2h_b_wins": len(log) - a_wins,
        "disclaimer": "基于历史赛果的 Elo，不是博彩赔率。场次少时把握低。",
    }
