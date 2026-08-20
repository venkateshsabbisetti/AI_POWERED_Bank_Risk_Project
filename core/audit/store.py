"""SQLite-backed human-review audit trail. No caching -- must reflect writes immediately."""
import json
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from core.config import AUDIT_DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS review_decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    ai_risk_score REAL,
    ai_bucket TEXT,
    ai_reasons TEXT,
    ai_recommendation TEXT,
    human_decision TEXT NOT NULL,
    reviewer_note TEXT,
    reviewer_name TEXT,
    decided_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUDIT_DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def record_decision(
    entity_type: str,
    entity_id: str,
    ai_risk_score: float,
    ai_bucket: str,
    ai_reasons: list[str],
    ai_recommendation: str,
    human_decision: str,
    reviewer_note: str = "",
    reviewer_name: str = "",
) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO review_decisions
               (entity_type, entity_id, ai_risk_score, ai_bucket, ai_reasons,
                ai_recommendation, human_decision, reviewer_note, reviewer_name, decided_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entity_type,
                entity_id,
                ai_risk_score,
                ai_bucket,
                json.dumps(ai_reasons),
                ai_recommendation,
                human_decision,
                reviewer_note,
                reviewer_name,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def fetch_history(entity_type: str | None = None) -> pd.DataFrame:
    with _connect() as conn:
        query = "SELECT * FROM review_decisions"
        params = ()
        if entity_type:
            query += " WHERE entity_type = ?"
            params = (entity_type,)
        query += " ORDER BY decided_at DESC"
        return pd.read_sql_query(query, conn, params=params)


def decided_entity_ids(entity_type: str) -> set[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT entity_id FROM review_decisions WHERE entity_type = ?",
            (entity_type,),
        ).fetchall()
    return {r[0] for r in rows}


def audit_completeness(entity_type: str, flagged_ids: list[str]) -> float:
    if not flagged_ids:
        return 1.0
    decided = decided_entity_ids(entity_type)
    covered = sum(1 for i in flagged_ids if i in decided)
    return round(covered / len(flagged_ids), 3)
