from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.elo import compute_elo, expected_score, predict_matchup, win_probability
from server.standings import (
    compute_player_standings,
    compute_team_standings,
    filter_matches_by_hours,
    player_match_log,
    resolve_player,
)
from server.mcp_http import handle_rpc

NOW = int(datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc).timestamp() * 1000)

MATCHES = [
    {
        "id": "1",
        "date": "2026-10-15T07:30:00.000Z",
        "home_player": "Melo",
        "away_player": "Ray",
        "home_team": "Los Angeles Lakers",
        "away_team": "New York Knicks",
        "home_score": 90,
        "away_score": 70,
    },
    {
        "id": "2",
        "date": "2026-10-15T04:00:00.000Z",
        "home_player": "Melo",
        "away_player": "Jason",
        "home_team": "Denver Nuggets",
        "away_team": "Brooklyn Nets",
        "home_score": 80,
        "away_score": 75,
    },
    {
        "id": "3",
        "date": "2026-10-14T12:00:00.000Z",
        "home_player": "Ray",
        "away_player": "Jason",
        "home_team": "Dallas Mavericks",
        "away_team": "Brooklyn Nets",
        "home_score": 60,
        "away_score": 88,
    },
]


def by_player(rows, name):
    return next((row for row in rows if row["player"] == name), None)


def test_hours_filter():
    assert [m["id"] for m in filter_matches_by_hours(MATCHES, 3, NOW)] == ["1"]


def test_player_standings():
    melo = by_player(compute_player_standings(MATCHES), "Melo")
    assert melo["wl"] == "2-0"
    assert melo["rank"] == 1
    assert melo["display"] == "Los Angeles Lakers (Melo)"


def test_team_standings():
    rows = compute_team_standings(MATCHES)
    lakers = next(row for row in rows if row["team"] == "Los Angeles Lakers")
    assert lakers["wl"] == "1-0"


def test_player_log():
    log = player_match_log(MATCHES, "Melo")
    assert log[0]["opponent"] == "Ray"
    assert log[0]["won"] is True


def test_resolve_player():
    assert resolve_player(MATCHES, "melo")["match"] == "Melo"
    assert "Jason" in resolve_player(MATCHES, "jas")["candidates"] or resolve_player(MATCHES, "jas")["match"] == "Jason"


def test_unknown_mcp_tool():
    res = handle_rpc(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "nope", "arguments": {}},
        }
    )
    assert res["result"]["isError"] is True


def test_elo_equal_ratings():
    assert abs(expected_score(1500, 1500) - 0.5) < 1e-9
    assert abs(win_probability(1600, 1500) - expected_score(1600, 1500)) < 1e-9


def test_elo_melo_above_ray():
    table = compute_elo(MATCHES)
    assert table["Melo"]["elo"] > table["Ray"]["elo"]
    pred = predict_matchup(MATCHES, "Melo", "Ray")
    assert pred["p_a_win"] > 0.5
    assert pred["h2h_a_wins"] == 1
    assert pred["model"] == "elo"


def test_mcp_initialize_and_list():
    init = handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["serverInfo"]["name"] == "async-match"
    listed = handle_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    names = {t["name"] for t in listed["result"]["tools"]}
    assert "get_player_standings" in names
    assert "get_head_to_head" in names
    assert "predict_matchup" in names
    assert "get_elo_ratings" in names


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
