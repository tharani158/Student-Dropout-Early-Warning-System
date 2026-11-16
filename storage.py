"""Metadata persistence: local JSON by default, PostgreSQL when configured."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def read_state(path: Path) -> dict[str, Any]:
    url = os.getenv("DATABASE_URL")
    if url:
        import psycopg
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS eduguard_state (id integer PRIMARY KEY, payload jsonb NOT NULL)")
                cur.execute("SELECT payload FROM eduguard_state WHERE id = 1")
                row = cur.fetchone()
                return row[0] if row else {"datasets": [], "activities": []}
    if not path.exists():
        return {"datasets": [], "activities": []}
    state = json.loads(path.read_text(encoding="utf-8"))
    state.setdefault("activities", [])
    return state


def write_state(path: Path, payload: dict[str, Any]) -> None:
    url = os.getenv("DATABASE_URL")
    if url:
        import psycopg
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS eduguard_state (id integer PRIMARY KEY, payload jsonb NOT NULL)")
                cur.execute("INSERT INTO eduguard_state (id, payload) VALUES (1, %s::jsonb) "
                            "ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload",
                            (json.dumps(payload, default=str),))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
