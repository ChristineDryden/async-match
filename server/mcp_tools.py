from __future__ import annotations

import json
from typing import Any, Callable

from server import db
from server import standings as S

TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "get_league_summary",
        "description": "Valhalla League 篮球库总览：场次、时间范围、当前选手榜前几名。回答领先者或整体形势时先调用。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "只看最近 N 小时，不传表示全部",
                },
                "top_n": {
                    "type": "integer",
                    "description": "返回前几名，默认 5",
                    "default": 5,
                },
            },
        },
    },
    {
        "name": "get_player_standings",
        "description": "选手积分榜：P、W-L、PCT、胜率、GB、L5、STRK。可按最近小时或 ISO 时间区间过滤。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer", "description": "最近 N 小时"},
                "from_iso": {"type": "string", "description": "起始时间 ISO8601"},
                "to_iso": {"type": "string", "description": "结束时间 ISO8601"},
                "top_n": {"type": "integer", "description": "返回前几名，默认 15", "default": 15},
            },
        },
    },
    {
        "name": "get_team_standings",
        "description": "球队积分榜，字段与选手榜相同。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer"},
                "from_iso": {"type": "string"},
                "to_iso": {"type": "string"},
                "top_n": {"type": "integer", "default": 15},
            },
        },
    },
    {
        "name": "get_player_record",
        "description": "某选手的战绩、主要对手和最近比赛。选手名支持模糊匹配。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "player": {"type": "string", "description": "选手名，如 Melo"},
                "hours": {"type": "integer", "description": "只看最近 N 小时"},
                "recent_n": {"type": "integer", "description": "最近比赛条数，默认 8", "default": 8},
            },
            "required": ["player"],
        },
    },
    {
        "name": "get_head_to_head",
        "description": "两名选手的历史交锋胜负和比分。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "player_a": {"type": "string"},
                "player_b": {"type": "string"},
            },
            "required": ["player_a", "player_b"],
        },
    },
    {
        "name": "get_recent_matches",
        "description": "最近篮球赛果列表，可按选手过滤。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "player": {"type": "string"},
                "limit": {"type": "integer", "description": "默认 10，最大 24", "default": 10},
                "hours": {"type": "integer"},
            },
        },
    },
    {
        "name": "search_players",
        "description": "按名字搜索库里的选手，不确定拼写时使用。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    },
]


def grok_function_tools() -> list[dict[str, Any]]:
    tools = []
    for item in TOOL_DEFS:
        tools.append(
            {
                "type": "function",
                "name": item["name"],
                "description": item["description"],
                "parameters": item["inputSchema"],
            }
        )
    return tools


def mcp_tool_list() -> list[dict[str, Any]]:
    return [
        {
            "name": item["name"],
            "description": item["description"],
            "inputSchema": item["inputSchema"],
        }
        for item in TOOL_DEFS
    ]


def _load_matches() -> list[dict]:
    db.init_schema()
    return db.list_matches()


def _window(matches: list[dict], hours: int | None, from_iso: str | None, to_iso: str | None) -> tuple[list[dict], str]:
    if hours:
        return S.filter_matches_by_hours(matches, int(hours)), f"最近 {int(hours)} 小时"
    from_ms = S._parse_ms(from_iso) if from_iso else None
    to_ms = S._parse_ms(to_iso) if to_iso else None
    if from_ms is not None or to_ms is not None:
        return S.filter_matches_by_range(matches, from_ms, to_ms), "自定义区间"
    return matches, "全部数据"


def _clip(n: Any, default: int, lo: int, hi: int) -> int:
    try:
        value = int(n)
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def tool_get_league_summary(hours: int | None = None, top_n: int = 5, **_: Any) -> dict[str, Any]:
    matches = _load_matches()
    filtered, label = _window(matches, hours, None, None)
    rows = S.compute_player_standings(filtered)
    dates = [m.get("date") for m in filtered if m.get("date")]
    return {
        "window": label,
        "match_count": len(filtered),
        "total_in_db": len(matches),
        "from": dates[-1] if dates else None,
        "to": dates[0] if dates else None,
        "player_count": len(rows),
        "leaders": [S._compact_row(r) for r in rows[: _clip(top_n, 5, 1, 20)]],
    }


def tool_get_player_standings(
    hours: int | None = None,
    from_iso: str | None = None,
    to_iso: str | None = None,
    top_n: int = 15,
    **_: Any,
) -> dict[str, Any]:
    matches, label = _window(_load_matches(), hours, from_iso, to_iso)
    rows = S.compute_player_standings(matches)
    n = _clip(top_n, 15, 1, 40)
    return {
        "window": label,
        "match_count": len(matches),
        "shown": min(n, len(rows)),
        "total_players": len(rows),
        "standings": [S._compact_row(r) for r in rows[:n]],
    }


def tool_get_team_standings(
    hours: int | None = None,
    from_iso: str | None = None,
    to_iso: str | None = None,
    top_n: int = 15,
    **_: Any,
) -> dict[str, Any]:
    matches, label = _window(_load_matches(), hours, from_iso, to_iso)
    rows = S.compute_team_standings(matches)
    n = _clip(top_n, 15, 1, 40)
    return {
        "window": label,
        "match_count": len(matches),
        "shown": min(n, len(rows)),
        "total_teams": len(rows),
        "standings": [S._compact_row(r) for r in rows[:n]],
    }


def tool_get_player_record(
    player: str,
    hours: int | None = None,
    recent_n: int = 8,
    **_: Any,
) -> dict[str, Any]:
    matches, label = _window(_load_matches(), hours, None, None)
    resolved = S.resolve_player(matches, player)
    if not resolved["match"]:
        return {
            "error": "未找到唯一选手",
            "query": player,
            "candidates": resolved["candidates"],
        }
    name = resolved["match"]
    rows = S.compute_player_standings(matches)
    self = next((S._compact_row(r) for r in rows if r["player"] == name), None)
    log = S.player_match_log(matches, name)
    n = _clip(recent_n, 8, 1, 20)
    return {
        "window": label,
        "player": name,
        "standing": self,
        "rivals": S.opponent_records(log)[:8],
        "recent": log[:n],
        "game_count": len(log),
    }


def tool_get_head_to_head(player_a: str, player_b: str, **_: Any) -> dict[str, Any]:
    matches = _load_matches()
    a = S.resolve_player(matches, player_a)
    b = S.resolve_player(matches, player_b)
    if not a["match"] or not b["match"]:
        return {
            "error": "选手无法唯一匹配",
            "player_a": a,
            "player_b": b,
        }
    name_a, name_b = a["match"], b["match"]
    log = [
        g
        for g in S.player_match_log(matches, name_a)
        if g["opponent"] == name_b
    ]
    wins = sum(1 for g in log if g["won"])
    losses = len(log) - wins
    return {
        "player_a": name_a,
        "player_b": name_b,
        "games": len(log),
        "record": f"{wins}-{losses}",
        "a_wins": wins,
        "b_wins": losses,
        "recent": log[:12],
    }


def tool_get_recent_matches(
    player: str | None = None,
    limit: int = 10,
    hours: int | None = None,
    **_: Any,
) -> dict[str, Any]:
    matches, label = _window(_load_matches(), hours, None, None)
    name = None
    if player:
        resolved = S.resolve_player(matches, player)
        if not resolved["match"]:
            return {"error": "未找到唯一选手", "candidates": resolved["candidates"]}
        name = resolved["match"]
        games = S.player_match_log(matches, name)
        compact = games[: _clip(limit, 10, 1, 24)]
        return {"window": label, "player": name, "matches": compact}
    ordered = sorted(matches, key=lambda m: S._parse_ms(m.get("date")) or 0, reverse=True)
    n = _clip(limit, 10, 1, 24)
    slim = [
        {
            "id": m.get("id"),
            "date": m.get("date"),
            "home_player": m.get("home_player"),
            "away_player": m.get("away_player"),
            "home_team": m.get("home_team"),
            "away_team": m.get("away_team"),
            "home_score": m.get("home_score"),
            "away_score": m.get("away_score"),
        }
        for m in ordered[:n]
    ]
    return {"window": label, "matches": slim}


def tool_search_players(query: str, **_: Any) -> dict[str, Any]:
    matches = _load_matches()
    resolved = S.resolve_player(matches, query)
    return {
        "query": query,
        "match": resolved["match"],
        "candidates": resolved["candidates"],
    }


HANDLERS: dict[str, Callable[..., Any]] = {
    "get_league_summary": tool_get_league_summary,
    "get_player_standings": tool_get_player_standings,
    "get_team_standings": tool_get_team_standings,
    "get_player_record": tool_get_player_record,
    "get_head_to_head": tool_get_head_to_head,
    "get_recent_matches": tool_get_recent_matches,
    "search_players": tool_search_players,
}


def call_tool(name: str, arguments: dict[str, Any] | None) -> str:
    handler = HANDLERS.get(name)
    if handler is None:
        payload = {"error": f"未知工具: {name}"}
    else:
        try:
            payload = handler(**(arguments or {}))
        except TypeError as exc:
            payload = {"error": f"参数错误: {exc}"}
        except Exception as exc:  # noqa: BLE001
            payload = {"error": str(exc)}
    return json.dumps(payload, ensure_ascii=False)
