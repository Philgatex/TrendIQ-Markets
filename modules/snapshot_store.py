import json
import os
import sqlite3
import time
from typing import Optional

DEFAULT_DB_PATH = os.environ.get("TRENDIQ_SNAPSHOT_DB", "trendiq_snapshot.db")


def _ensure_db(path: Optional[str] = None):
    path = path or DEFAULT_DB_PATH
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, generated_at INTEGER, payload TEXT)"
    )
    conn.commit()
    return conn


def write_latest_snapshot(df, path: Optional[str] = None):
    path = path or DEFAULT_DB_PATH
    conn = _ensure_db(path)
    try:
        payload = json.dumps({"data": df.to_dict(orient="records")})
        generated_at = int(time.time())
        conn.execute(
            "INSERT OR REPLACE INTO snapshots (id, generated_at, payload) VALUES (1, ?, ?)",
            (generated_at, payload),
        )
        conn.commit()
    finally:
        conn.close()


def load_latest_snapshot(path: Optional[str] = None):
    path = path or DEFAULT_DB_PATH
    if not os.path.exists(path):
        return None
    conn = _ensure_db(path)
    try:
        row = conn.execute("SELECT payload FROM snapshots WHERE id = 1").fetchone()
        if not row:
            return None
        payload = json.loads(row[0])
        records = payload.get("data", [])
        if not records:
            return None
        import pandas as pd

        df = pd.DataFrame(records)
        return df
    except Exception:
        return None
    finally:
        conn.close()
