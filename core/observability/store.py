"""SQLite-backed pipeline run log. No caching -- must reflect writes immediately.

Mirrors the pattern in core/audit/store.py but for system telemetry (run
timing, row counts, model params) rather than human review decisions.
"""
import json
import sqlite3

import pandas as pd

from core.config import OBSERVABILITY_DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_seconds REAL,
    status TEXT NOT NULL,
    error_message TEXT,
    stage_durations TEXT,
    row_counts TEXT,
    data_quality_issue_rows INTEGER,
    anomaly_model_info TEXT
);
"""


def _connect() -> sqlite3.Connection:
    OBSERVABILITY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(OBSERVABILITY_DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def record_pipeline_run(
    started_at: str,
    finished_at: str,
    duration_seconds: float,
    status: str,
    error_message: str | None,
    stage_durations: dict,
    row_counts: dict,
    data_quality_issue_rows: int | None,
    anomaly_model_info: dict,
) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO pipeline_runs
               (started_at, finished_at, duration_seconds, status, error_message,
                stage_durations, row_counts, data_quality_issue_rows, anomaly_model_info)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                started_at,
                finished_at,
                duration_seconds,
                status,
                error_message,
                json.dumps(stage_durations),
                json.dumps(row_counts),
                data_quality_issue_rows,
                json.dumps(anomaly_model_info),
            ),
        )


def fetch_pipeline_runs(limit: int = 50) -> pd.DataFrame:
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM pipeline_runs ORDER BY run_id DESC LIMIT ?",
            conn,
            params=(limit,),
        )
    for col in ("stage_durations", "row_counts", "anomaly_model_info"):
        df[col] = df[col].apply(lambda v: json.loads(v) if isinstance(v, str) else {})
    return df
