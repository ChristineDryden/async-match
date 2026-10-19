from __future__ import annotations

import json
from typing import Any

from server.config import XAI_API_KEY, XAI_BASE_URL, XAI_MODEL
from server.mcp_tools import call_tool, grok_function_tools

INSTRUCTIONS = """你是 Valhalla League 篮球积分榜应用里的比赛分析助手。
只用工具查到的真实数据回答，不要编造场次、比分或排名。
先调用合适的工具再下结论。选手名不确定时先 search_players。
预测对战胜负或获胜概率时，必须调用 predict_matchup，不要说没有概率模型。
说明这是基于历史赛果的 Elo，不是博彩赔率；confidence 为 low 时明确说场次少、把握低。
用简体中文回答，除非用户用了别的语言。
回答要短：点出排名、胜负、胜率、近况和交锋，必要时点出具体场次。
时间窗口要说清楚是全部数据还是最近几小时。
"""

MAX_TOOL_ROUNDS = 6
MAX_HISTORY = 20


def _client():
    from openai import OpenAI

    api_key = (XAI_API_KEY or "").strip()
    if not api_key:
        raise RuntimeError("未配置 XAI_API_KEY，无法调用 Grok。")
    return OpenAI(
        api_key=api_key,
        base_url=XAI_BASE_URL,
    )


def _model() -> str:
    return XAI_MODEL or "grok-4.6"


def _text_from(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text
    chunks: list[str] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) in ("output_text", "text"):
                chunks.append(getattr(part, "text", "") or "")
    return "".join(chunks).strip()


def _function_calls(response: Any) -> list[Any]:
    return [
        item
        for item in (getattr(response, "output", None) or [])
        if getattr(item, "type", None) == "function_call"
    ]


def _item_to_input(item: Any) -> dict[str, Any] | None:
    kind = getattr(item, "type", None)
    if kind == "function_call":
        return {
            "type": "function_call",
            "call_id": item.call_id,
            "name": item.name,
            "arguments": item.arguments or "{}",
        }
    if kind == "message":
        text = ""
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) in ("output_text", "text"):
                text += getattr(part, "text", "") or ""
        text = text.strip()
        if text:
            return {"role": "assistant", "content": text}
    return None


def _history_from_messages(
    message: str | None,
    messages: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for item in messages or []:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
    if not history:
        text = (message or "").strip()
        if text:
            history.append({"role": "user", "content": text})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    return history


def run_chat(
    message: str | None = None,
    previous_response_id: str | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    del previous_response_id  # 当前账号不支持 Responses 服务端会话
    history: list[dict[str, Any]] = _history_from_messages(message, messages)
    if not history:
        raise ValueError("消息不能为空")

    client = _client()
    tools = grok_function_tools()
    model = _model()
    used: list[str] = []
    create_kwargs: dict[str, Any] = {
        "model": model,
        "instructions": INSTRUCTIONS,
        "tools": tools,
        "reasoning": {"effort": "low"},
        "store": False,
    }

    response = client.responses.create(input=history, **create_kwargs)
    rounds = 0
    while _function_calls(response) and rounds < MAX_TOOL_ROUNDS:
        rounds += 1
        for item in response.output:
            converted = _item_to_input(item)
            if converted:
                history.append(converted)
        for item in _function_calls(response):
            try:
                args = json.loads(item.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            used.append(item.name)
            history.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": call_tool(item.name, args if isinstance(args, dict) else {}),
                }
            )
        response = client.responses.create(input=history, **create_kwargs)

    reply = _text_from(response)
    if not reply and _function_calls(response):
        reply = "分析还没结束，请再问一次，或把问题说得更具体一点。"
    return {
        "reply": reply or "没有生成回答。",
        "response_id": getattr(response, "id", None),
        "model": model,
        "tools_used": used,
    }
