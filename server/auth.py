from __future__ import annotations

import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import jsonify, request

from server.config import AUTH_PASSWORD, AUTH_USERNAME, SESSION_HOURS

_COOKIE = "async_match_session"
_sessions: dict[str, datetime] = {}


def _purge() -> None:
    now = datetime.now(timezone.utc)
    expired = [token for token, until in _sessions.items() if until <= now]
    for token in expired:
        _sessions.pop(token, None)


def issue_session(username: str) -> str:
    _purge()
    token = secrets.token_urlsafe(32)
    _sessions[token] = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    return token


def drop_session(token: str | None) -> None:
    if token:
        _sessions.pop(token, None)


def session_user(token: str | None) -> str | None:
    if not token:
        return None
    _purge()
    until = _sessions.get(token)
    if until is None or until <= datetime.now(timezone.utc):
        _sessions.pop(token, None)
        return None
    return AUTH_USERNAME


def credentials_match(username: str, password: str) -> bool:
    user_ok = hmac.compare_digest(username, AUTH_USERNAME)
    pass_ok = hmac.compare_digest(password, AUTH_PASSWORD)
    return user_ok and pass_ok


def current_user() -> str | None:
    return session_user(request.cookies.get(_COOKIE))


def require_login():
    if current_user():
        return None
    return jsonify({"error": "未登录"}), 401


def attach_session(response, token: str):
    response.set_cookie(
        _COOKIE,
        token,
        httponly=True,
        samesite="Lax",
        secure=os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
        max_age=SESSION_HOURS * 3600,
        path="/",
    )
    return response


def clear_session(response):
    response.delete_cookie(_COOKIE, path="/")
    return response
