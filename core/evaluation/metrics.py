"""Model evaluation against held-out ground truth + operational/governance metrics.

fraud_flag is read here ONLY as ground truth -- never as a scoring input
(see core/risk/rule_engine.py docstring for the leakage rationale).
"""
import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def evaluate_fraud_model(scored_df: pd.DataFrame) -> dict:
    y_true = (scored_df["fraud_flag"] == "Y").astype(int)
    y_pred = scored_df["risk_bucket"].isin(["High", "Critical"]).astype(int)
    y_score = scored_df["risk_score"] / 100.0

    if y_true.sum() == 0 or y_true.sum() == len(y_true):
        return {"error": "Ground truth has no positive/negative variance; cannot evaluate."}

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_true, y_score)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0

    fpr_curve, tpr_curve, thresholds = roc_curve(y_true, y_score)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "roc_curve": {"fpr": fpr_curve.tolist(), "tpr": tpr_curve.tolist()},
        "baseline_comparison": _baseline_comparison(scored_df, y_true),
    }


def _baseline_comparison(scored_df: pd.DataFrame, y_true: pd.Series) -> dict:
    """Naive baseline: flag if the dataset's own pre-existing baseline_risk_score > 60."""
    baseline_pred = (scored_df["baseline_risk_score"] > 60).astype(int)
    return {
        "baseline_precision": round(precision_score(y_true, baseline_pred, zero_division=0), 4),
        "baseline_recall": round(recall_score(y_true, baseline_pred, zero_division=0), 4),
        "baseline_f1": round(f1_score(y_true, baseline_pred, zero_division=0), 4),
    }


def threshold_sweep(scored_df: pd.DataFrame, step: int = 5) -> pd.DataFrame:
    y_true = (scored_df["fraud_flag"] == "Y").astype(int)
    rows = []
    for t in range(0, 101, step):
        y_pred = (scored_df["risk_score"] > t).astype(int)
        rows.append(
            {
                "threshold": t,
                "precision": precision_score(y_true, y_pred, zero_division=0),
                "recall": recall_score(y_true, y_pred, zero_division=0),
                "f1": f1_score(y_true, y_pred, zero_division=0),
            }
        )
    return pd.DataFrame(rows)


def sla_detection_accuracy(enriched_incidents: pd.DataFrame) -> float:
    agree = (enriched_incidents["computed_sla_breach"]) == (enriched_incidents["sla_breached"] == "Y")
    return round(agree.mean(), 4)


def incident_prioritization_consistency(incidents: pd.DataFrame) -> float:
    sev_to_priority = {"SEV1": "P1", "SEV2": "P2", "SEV3": "P3", "SEV4": "P4"}
    expected = incidents["severity"].map(sev_to_priority)
    return round((expected == incidents["priority"]).mean(), 4)


def slow_api_detection_rate(enriched_api_logs: pd.DataFrame) -> float:
    proxy_positive = (enriched_api_logs["is_timeout"]) | (enriched_api_logs["response_code"] >= 500)
    if proxy_positive.sum() == 0:
        return 0.0
    return round((enriched_api_logs["is_slow"] & proxy_positive).sum() / proxy_positive.sum(), 4)


def failure_clustering_rank_agreement(module_summary: pd.DataFrame) -> float:
    """Spearman correlation between quality-score rank and actual fail-rate rank per module."""
    df = module_summary.copy()
    df["fail_rate"] = df["fail_count"] / df["total_tests"]
    return round(df["quality_score"].corr(df["fail_rate"], method="spearman") * -1, 4)


def explainability_coverage(scored_df: pd.DataFrame) -> float:
    flagged = scored_df[scored_df["risk_bucket"].isin(["High", "Critical"])]
    if len(flagged) == 0:
        return 1.0
    return round((flagged["reasons"].apply(len) > 0).mean(), 4)
