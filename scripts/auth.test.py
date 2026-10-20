from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server.auth as auth
from server.app import app


def test_login_gates_pages_and_data():
    client = app.test_client()

    home = client.get("/")
    assert home.status_code == 302
    assert home.headers["Location"].startswith("/login")

    player = client.get("/player?name=Melo")
    assert player.status_code == 302
    assert "/login" in player.headers["Location"]
    assert "redirect=" in player.headers["Location"]

    denied = client.get("/api/matches")
    assert denied.status_code == 401

    bad = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert bad.status_code == 401

    ok = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert ok.status_code == 200
    assert ok.json["user"] == "admin"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json["user"] == "admin"

    again = client.get("/")
    assert again.status_code != 302

    client.post("/api/auth/logout")
    public_asset = client.get("/favicon.svg")
    assert public_asset.status_code != 302
    assert client.get("/api/matches").status_code == 401


def test_session_expires(monkeypatch):
    token = auth.issue_session("admin")
    assert auth.session_user(token) == "admin"
    auth.drop_session(token)
    assert auth.session_user(token) is None
