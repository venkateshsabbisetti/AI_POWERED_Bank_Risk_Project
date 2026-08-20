"""Unsupervised behavioral anomaly scoring: IsolationForest + LOF + statistical z-score.

No ground-truth labels (fraud_flag) are used here -- this stays strictly
unsupervised so it can be fairly evaluated against fraud_flag later.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import OneHotEncoder

_NUMERIC_FEATURES = [
    "log_amount",
    "amount_zscore_within_type",
    "hour_of_day",
    "customer_tenure_days",
    "account_age_days",
    "balance_utilization_ratio",
]
_FLAG_FEATURES = ["is_new_beneficiary", "is_possible_duplicate", "account_customer_mismatch"]
_CATEGORICAL_FEATURES = ["transaction_channel", "transaction_type"]


def _percentile_rank(values: np.ndarray) -> np.ndarray:
    order = values.argsort()
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(values))
    return ranks / max(len(values) - 1, 1)


def compute_anomaly_scores(features_df: pd.DataFrame) -> pd.DataFrame:
    n = len(features_df)
    numeric = features_df[_NUMERIC_FEATURES].fillna(0).to_numpy(dtype=float)
    flags = features_df[_FLAG_FEATURES].fillna(False).astype(float).to_numpy()

    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    cat = encoder.fit_transform(features_df[_CATEGORICAL_FEATURES].fillna("UNKNOWN").astype(str))

    X = np.hstack([numeric, flags, cat])
    X = np.nan_to_num(X)

    iso = IsolationForest(contamination="auto", random_state=42, n_estimators=150)
    iso.fit(X)
    iso_raw = -iso.decision_function(X)  # higher = more anomalous
    iso_score = _percentile_rank(iso_raw)

    n_neighbors = min(20, max(n - 1, 1))
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, novelty=False)
    lof.fit_predict(X)
    lof_raw = -lof.negative_outlier_factor_
    lof_score = _percentile_rank(lof_raw)

    log_amount = features_df["log_amount"].fillna(0).to_numpy()
    mean, std = log_amount.mean(), log_amount.std() or 1.0
    z_scores = np.abs((log_amount - mean) / std)
    stat_flag = (z_scores > 3).astype(float)

    behavioral_score = 0.45 * iso_score + 0.45 * lof_score + 0.10 * stat_flag
    behavioral_score = np.clip(behavioral_score, 0, 1)

    return pd.DataFrame(
        {
            "iso_score": iso_score,
            "lof_score": lof_score,
            "statistical_outlier": stat_flag.astype(bool),
            "behavioral_anomaly_score": behavioral_score,
        },
        index=features_df.index,
    )
