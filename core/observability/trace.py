"""Assemble an end-to-end lineage view for a single transaction or incident.

Everything here is derived on demand from the already-computed PipelineResult
in memory -- no separate storage needed, since the scored/enriched dataframes
already carry every intermediate value (features, rule points, anomaly
scores, final score, recommendation).
"""
import pandas as pd

from core.audit.store import fetch_history
from core.governance.checks import mask_pii
from core.risk.rule_engine import reason_lookup

_FEATURE_FIELDS = [
    "customer_tenure_days",
    "account_age_days",
    "log_amount",
    "amount_zscore_within_type",
    "hour_of_day",
    "is_new_beneficiary",
    "is_possible_duplicate",
    "account_customer_mismatch",
    "balance_utilization_ratio",
]

_RAW_TXN_FIELDS = [
    "transaction_id",
    "transaction_datetime",
    "transaction_type",
    "transaction_channel",
    "transaction_amount",
    "currency",
    "transaction_status",
    "settlement_status",
    "customer_id",
    "account_id",
    "beneficiary_id",
    "ip_address",
    "kyc_status",
    "account_status",
]


def trace_transaction(transaction_id: str, result) -> dict | None:
    scored = result.transactions_scored
    match = scored[scored["transaction_id"] == transaction_id]
    if match.empty:
        return None
    row = match.iloc[0]

    raw_fields = [f for f in _RAW_TXN_FIELDS if f in row.index]
    raw_masked = mask_pii(pd.DataFrame([row[raw_fields]])).iloc[0]

    lookup = reason_lookup()
    rules_fired = []
    for reason in row["reasons"]:
        rule = lookup.get(reason)
        if rule is not None:
            rules_fired.append({"reason": reason, "category": rule.category, "points": rule.points})
        else:
            rules_fired.append(
                {"reason": reason, "category": "behavioral", "points": round(float(row["behavioral_points"]), 1)}
            )

    history = fetch_history("transaction")
    review = history[history["entity_id"] == transaction_id] if len(history) else history

    return {
        "raw": raw_masked.to_dict(),
        "features": {f: row[f] for f in _FEATURE_FIELDS if f in row.index},
        "rules_fired": rules_fired,
        "anomaly": {
            "iso_score": float(row["iso_score"]),
            "lof_score": float(row["lof_score"]),
            "statistical_outlier": bool(row["statistical_outlier"]),
            "behavioral_anomaly_score": float(row["behavioral_anomaly_score"]),
            "behavioral_points": float(row["behavioral_points"]),
        },
        "category_points": {
            "KYC": float(row["kyc_points"]),
            "Account": float(row["account_points"]),
            "Amount": float(row["amount_points"]),
            "Behavioral": float(row["behavioral_points"]),
            "Fraud Signals": float(row["fraud_signals_points"]),
            "Governance": float(row["governance_points"]),
        },
        "final": {
            "risk_score": float(row["risk_score"]),
            "risk_bucket": row["risk_bucket"],
            "recommendation": row["recommendation"],
            "confidence": float(row["confidence"]),
        },
        "human_review": review,
    }


_RAW_INCIDENT_FIELDS = [
    "incident_id",
    "reported_datetime",
    "resolved_datetime",
    "severity",
    "incident_status",
    "application_module",
    "assigned_team",
    "assigned_engineer",
    "root_cause",
    "sla_hours",
    "sla_breached",
]


def trace_incident(incident_id: str, result) -> dict | None:
    enriched = result.incidents_enriched
    match = enriched[enriched["incident_id"] == incident_id]
    if match.empty:
        return None
    row = match.iloc[0]

    raw_fields = [f for f in _RAW_INCIDENT_FIELDS if f in row.index]
    return {
        "raw": {f: row[f] for f in raw_fields},
        "computed": {
            "resolution_hours": row["resolution_hours"],
            "computed_sla_breach": bool(row["computed_sla_breach"]),
            "module_occurrence_30d": int(row["module_occurrence_30d"]),
            "is_repeated_incident": bool(row["is_repeated_incident"]),
        },
        "reasons": row["reasons"],
        "recommendation": row["recommendation"],
        "human_review": None,  # no review workflow implemented for incidents yet
    }
