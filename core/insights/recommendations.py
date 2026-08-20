"""Rule-based recommendation templates keyed on (bucket, dominant risk category)."""
import pandas as pd

_CATEGORY_LABELS = {
    "kyc_points": "KYC",
    "account_points": "Account",
    "amount_points": "Amount",
    "behavioral_points": "Behavioral",
    "fraud_signals_points": "Fraud Signals",
    "governance_points": "Governance",
}

_TEMPLATES = [
    ("Critical", "KYC", "Immediately suspend processing and escalate to compliance for identity re-verification before any further action."),
    ("Critical", "Account", "Freeze account activity and escalate to fraud investigation before allowing further transactions."),
    ("Critical", None, "Prioritize manual investigation and validate customer identity and account status before processing."),
    ("High", "KYC", "Prioritize manual investigation and validate customer identity and account status before processing."),
    ("High", "Account", "Validate account status and ownership before releasing this transaction."),
    ("High", None, "Route to a senior analyst for manual review before final disposition."),
    ("Medium", None, "Flag for standard review queue; verify supporting documentation before approval."),
    ("Low", None, "Monitor account; no immediate action required."),
]


def _dominant_category(row: pd.Series) -> str:
    points = {label: row[col] for col, label in _CATEGORY_LABELS.items()}
    return max(points, key=points.get)


def recommend_for_transaction(row: pd.Series) -> tuple[str, float]:
    bucket = row["risk_bucket"]
    dominant = _dominant_category(row)
    for b, cat, template in _TEMPLATES:
        if b == bucket and (cat is None or cat == dominant):
            recommendation = template
            break
    else:
        recommendation = "Monitor account; no immediate action required."

    confidence = min(1.0, row["risk_score"] / 100 + 0.1 * len(row["reasons"]))
    return recommendation, round(confidence, 2)


def generate_transaction_recommendations(scored_df: pd.DataFrame) -> pd.DataFrame:
    df = scored_df.copy()
    results = df.apply(recommend_for_transaction, axis=1, result_type="expand")
    df["recommendation"] = results[0]
    df["confidence"] = results[1]
    df["dominant_category"] = df.apply(_dominant_category, axis=1)
    return df


def top_recommendations(scored_df: pd.DataFrame, n: int = 25) -> pd.DataFrame:
    flagged = scored_df[scored_df["risk_bucket"].isin(["High", "Critical"])]
    return flagged.sort_values("risk_score", ascending=False).head(n)
