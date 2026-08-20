"""Orchestrates the full workflow: validate -> engineer -> score -> ops intel ->
recommend -> governance. Cached as a resource because it holds fitted sklearn
models and is expensive to recompute (~seconds for 25k transactions).

Also records one observability row per real recompute (not per page view,
since the function body only executes on a cache miss) -- see
core/observability/store.py.
"""
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from core.audit.store import audit_completeness
from core.data.loader import load_all
from core.data.validation import validate_all
from core.evaluation.metrics import explainability_coverage
from core.features.engineering import build_transaction_features
from core.governance.checks import run_all as run_governance_checks
from core.insights.recommendations import generate_transaction_recommendations
from core.observability.store import record_pipeline_run
from core.ops.api_monitoring import enrich_api_logs
from core.ops.app_logs import enrich_application_logs
from core.ops.incidents import enrich_incidents
from core.ops.test_analytics import enrich_test_cases
from core.risk.scoring import score_transactions


@dataclass
class PipelineResult:
    raw: dict = field(default_factory=dict)
    issues: pd.DataFrame = None
    transactions_scored: pd.DataFrame = None
    incidents_enriched: pd.DataFrame = None
    api_logs_enriched: pd.DataFrame = None
    application_logs_enriched: pd.DataFrame = None
    test_cases_enriched: pd.DataFrame = None
    governance_metrics: list = field(default_factory=list)


_ANOMALY_MODEL_INFO = {
    "isolation_forest": {"n_estimators": 150, "contamination": "auto", "random_state": 42},
    "local_outlier_factor": {"n_neighbors": "min(20, n-1)", "novelty": False},
    "ensemble_weights": {"iso_score": 0.45, "lof_score": 0.45, "statistical_outlier": 0.10},
}


@st.cache_resource(show_spinner="Running risk & incident intelligence pipeline...")
def run_pipeline() -> PipelineResult:
    run_started_wall = datetime.now(timezone.utc)
    run_started = time.perf_counter()
    stage_durations: dict[str, float] = {}
    raw = {}

    def _timed(stage_name, fn, *args, **kwargs):
        t0 = time.perf_counter()
        out = fn(*args, **kwargs)
        stage_durations[stage_name] = round(time.perf_counter() - t0, 3)
        return out

    try:
        raw = _timed("data_load", load_all)
        issues = _timed("validation", validate_all, raw)

        features = _timed(
            "feature_engineering", build_transaction_features,
            raw["transactions"], raw["accounts"], raw["customers"],
        )
        scored = _timed("risk_scoring", score_transactions, features)
        scored = _timed("recommendations", generate_transaction_recommendations, scored)

        incidents_enriched = _timed("incident_enrichment", enrich_incidents, raw["incidents"])
        api_logs_enriched = _timed("api_enrichment", enrich_api_logs, raw["api_logs"])
        application_logs_enriched = _timed(
            "applog_enrichment", enrich_application_logs, raw["application_logs"]
        )
        test_cases_enriched = _timed("test_enrichment", enrich_test_cases, raw["test_cases"])

        flagged_txn_ids = scored.loc[
            scored["risk_bucket"].isin(["High", "Critical"]), "transaction_id"
        ].tolist()
        audit_pct = audit_completeness("transaction", flagged_txn_ids)
        explain_pct = explainability_coverage(scored)

        governance_metrics = _timed(
            "governance", run_governance_checks,
            risk_df=scored,
            incidents_df=incidents_enriched,
            issues_df=issues,
            audit_completeness=audit_pct,
            explainability_coverage=explain_pct,
            application_logs_df=application_logs_enriched,
        )
    except Exception as exc:
        record_pipeline_run(
            started_at=run_started_wall.isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=round(time.perf_counter() - run_started, 3),
            status="FAILED",
            error_message=str(exc),
            stage_durations=stage_durations,
            row_counts={name: len(df) for name, df in raw.items()},
            data_quality_issue_rows=None,
            anomaly_model_info=_ANOMALY_MODEL_INFO,
        )
        raise

    record_pipeline_run(
        started_at=run_started_wall.isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
        duration_seconds=round(time.perf_counter() - run_started, 3),
        status="SUCCESS",
        error_message=None,
        stage_durations=stage_durations,
        row_counts={name: len(df) for name, df in raw.items()},
        data_quality_issue_rows=int(issues["row_count"].sum()) if len(issues) else 0,
        anomaly_model_info=_ANOMALY_MODEL_INFO,
    )

    return PipelineResult(
        raw=raw,
        issues=issues,
        transactions_scored=scored,
        incidents_enriched=incidents_enriched,
        api_logs_enriched=api_logs_enriched,
        application_logs_enriched=application_logs_enriched,
        test_cases_enriched=test_cases_enriched,
        governance_metrics=governance_metrics,
    )
