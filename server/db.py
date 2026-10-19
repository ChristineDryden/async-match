from __future__ import annotations

from datetime import datetime, timezone

import pymysql
from pymysql.cursors import DictCursor

from server.config import DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS basketball_matches (
  id VARCHAR(32) NOT NULL,
  played_at DATETIME(3) NOT NULL,
  home_player VARCHAR(128) NOT NULL,
  away_player VARCHAR(128) NOT NULL,
  home_team VARCHAR(128) NOT NULL,
  away_team VARCHAR(128) NOT NULL,
  home_score SMALLINT NOT NULL,
  away_score SMALLINT NOT NULL,
  period_type VARCHAR(32) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_played_at (played_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def connect(with_db: bool = True):
    kwargs = {
        "host": DB["host"],
        "port": DB["port"],
        "user": DB["user"],
        "password": DB["password"],
        "charset": DB["charset"],
        "autocommit": True,
        "cursorclass": DictCursor,
        "connect_timeout": 15,
    }
    if with_db:
        kwargs["database"] = DB["database"]
    return pymysql.connect(**kwargs)


def init_schema() -> None:
    conn = connect(with_db=False)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB['database']}` "
                "DEFAULT CHARACTER SET utf8mb4"
            )
            cur.execute(f"USE `{DB['database']}`")
            cur.execute(SCHEMA)
    finally:
        conn.close()


def _utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def latest_played_at() -> datetime | None:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(played_at) AS latest FROM basketball_matches")
            row = cur.fetchone()
            latest = row["latest"] if row else None
            if latest is None:
                return None
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            return latest.astimezone(timezone.utc)
    finally:
        conn.close()


def insert_matches(matches: list[dict], parse_match_time) -> tuple[int, int]:
    if not matches:
        return 0, 0
    sql = """
        INSERT IGNORE INTO basketball_matches (
          id, played_at, home_player, away_player, home_team, away_team,
          home_score, away_score, period_type
        ) VALUES (
          %(id)s, %(played_at)s, %(home_player)s, %(away_player)s,
          %(home_team)s, %(away_team)s, %(home_score)s, %(away_score)s,
          %(period_type)s
        )
    """
    rows = []
    for match in matches:
        played = parse_match_time(match.get("date"))
        if played is None:
            continue
        rows.append(
            {
                "id": str(match["id"]),
                "played_at": _utc_naive(played),
                "home_player": match["home_player"],
                "away_player": match["away_player"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "home_score": int(match["home_score"]),
                "away_score": int(match["away_score"]),
                "period_type": match.get("period_type"),
            }
        )
    conn = connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(sql, row)
                inserted += cur.rowcount
    finally:
        conn.close()
    skipped = len(rows) - inserted
    return inserted, skipped


def list_matches() -> list[dict]:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, played_at, home_player, away_player, home_team, away_team,
                       home_score, away_score, period_type
                FROM basketball_matches
                ORDER BY played_at DESC, id DESC
                """
            )
            out = []
            for row in cur.fetchall():
                out.append(
                    {
                        "id": row["id"],
                        "date": _iso(row["played_at"]),
                        "home_player": row["home_player"],
                        "away_player": row["away_player"],
                        "home_team": row["home_team"],
                        "away_team": row["away_team"],
                        "home_score": row["home_score"],
                        "away_score": row["away_score"],
                        "period_type": row["period_type"],
                    }
                )
            return out
    finally:
        conn.close()


def match_count() -> int:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM basketball_matches")
            return int(cur.fetchone()["n"])
    finally:
        conn.close()
