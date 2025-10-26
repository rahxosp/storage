"""SQLite DB for metrics storage and retrieval."""
import sqlite3
import os
import threading
from typing import List, Tuple, Optional
from datetime import datetime, timedelta

_DB_PATH = os.path.join(os.path.dirname(__file__), 'metrics.db')
_lock = threading.Lock()


def _get_conn():
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              server TEXT NOT NULL,
              ts INTEGER NOT NULL,
              cpu REAL,
              ram_used_mb REAL,
              ram_total_mb REAL,
              gpu_util REAL,
              gpu_mem_used_mb REAL,
              gpu_mem_total_mb REAL
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_server_ts ON metrics(server, ts);")
        conn.commit()


def insert_metric(server: str, ts: int, cpu: Optional[float], ram_used_mb: Optional[float], ram_total_mb: Optional[float],
                  gpu_util: Optional[float], gpu_mem_used_mb: Optional[float], gpu_mem_total_mb: Optional[float]):
    with _lock:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO metrics(server, ts, cpu, ram_used_mb, ram_total_mb, gpu_util, gpu_mem_used_mb, gpu_mem_total_mb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (server, ts, cpu, ram_used_mb, ram_total_mb, gpu_util, gpu_mem_used_mb, gpu_mem_total_mb)
            )
            conn.commit()


def fetch_series(server: str, field: str, seconds: int = 300) -> List[Tuple[int, float]]:
    assert field in {"cpu", "gpu_util", "ram_used_mb", "gpu_mem_used_mb"}
    since_ts = int(datetime.utcnow().timestamp()) - seconds
    with _lock:
        with _get_conn() as conn:
            cur = conn.execute(
                f"SELECT ts, {field} FROM metrics WHERE server=? AND ts>=? AND {field} IS NOT NULL ORDER BY ts ASC",
                (server, since_ts)
            )
            rows = cur.fetchall()
            return [(int(ts), float(val)) for ts, val in rows]
