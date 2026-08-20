"""Combine rule engine points + ML anomaly score into a final 0-100 risk score."""
import pandas as pd

from core.config import RISK_BUCKETS, RISK_WEIGHTS
from core.risk.anomaly import compute_anomaly_scores
from core.risk.rule_engine import apply_rules


def _bucket_for(score: float) -> str:
    for low, high, label in RISK_BUCKETS:
        if low <= score <= high:
            return label
    return "Critical" if score > RISK_BUCKETS[-1][1] else "Low"


def score_transactions(features_df: pd.DataFrame) -> pd.DataFrame:
    anomaly_out = compute_anomaly_scores(features_df)
    features_with_anomaly = pd.concat(
        [features_df, anomaly_out[["behavioral_anomaly_score"]]], axis=1
    )
    rules_out = apply_rules(features_with_anomaly)

    behavioral_points = anomaly_out["behavioral_anomaly_score"] * RISK_WEIGHTS["behavioral"]

    category_cols = [c for c in rules_out.columns if c.endswith("_points")]
    raw_score = rules_out[category_cols].sum(axis=1) + behavioral_points
    raw_score = raw_score.clip(0, 100)

    behavioral_reason = pd.Series(
        [
            ["Unusual customer behaviour pattern (ML anomaly detection)"] if s > 0.85 else []
            for s in anomaly_out["behavioral_anomaly_score"]
        ],
        index=features_df.index,
    )

    combined_reasons = [
        r + b for r, b in zip(rules_out["rule_reasons"], behavioral_reason)
    ]
    combined_reasons = [list(dict.fromkeys(r)) for r in combined_reasons]  # dedupe, preserve order

    result = pd.DataFrame(
        {
            "risk_score": raw_score.round(1),
            "risk_bucket": raw_score.apply(_bucket_for),
            "reasons": combined_reasons,
            "kyc_points": rules_out["kyc_points"],
            "account_points": rules_out["account_points"],
            "amount_points": rules_out["amount_points"],
            "behavioral_points": behavioral_points.round(1),
            "fraud_signals_points": rules_out["fraud_signals_points"],
            "governance_points": rules_out["governance_points"],
            "iso_score": anomaly_out["iso_score"].round(3),
            "lof_score": anomaly_out["lof_score"].round(3),
            "statistical_outlier": anomaly_out["statistical_outlier"],
            "behavioral_anomaly_score": anomaly_out["behavioral_anomaly_score"].round(3),
        },
        index=features_df.index,
    )
    return pd.concat([features_df, result], axis=1)
