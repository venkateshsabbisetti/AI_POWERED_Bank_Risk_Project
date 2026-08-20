"""Declarative, extensible rule registry for transaction risk scoring.

Each rule is a predicate over a transaction feature row that, when true,
contributes `points` to a `category` and records a human-readable `reason`.
fraud_flag is intentionally NEVER read here -- it is held out as ground truth
for the Model Evaluation page (see core/evaluation/metrics.py).
"""
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from core.config import HIGH_VALUE_TXN_THRESHOLD_INR, RISK_WEIGHTS


@dataclass
class Rule:
    rule_id: str
    category: str
    points: float
    reason: str
    predicate: Callable[[pd.DataFrame], pd.Series]


_REGISTRY: list[Rule] = []


def register_rule(rule_id: str, category: str, points: float, reason: str):
    def decorator(predicate: Callable[[pd.DataFrame], pd.Series]):
        _REGISTRY.append(Rule(rule_id, category, points, reason, predicate))
        return predicate

    return decorator


# ---------------------------------------------------------------- KYC (cap 20)
@register_rule("KYC_REJECTED", "kyc", 20, "Rejected KYC customer")
def _r1(df):
    return df["kyc_status"] == "REJECTED"


@register_rule("KYC_EXPIRED", "kyc", 15, "Expired KYC")
def _r2(df):
    return df["kyc_status"] == "EXPIRED"


@register_rule("KYC_PENDING", "kyc", 8, "KYC verification pending")
def _r3(df):
    return df["kyc_status"] == "PENDING"


# ------------------------------------------------------------ Account (cap 20)
@register_rule("ACCOUNT_CLOSED", "account", 20, "Transaction on closed account")
def _r4(df):
    return df["account_status"] == "CLOSED"


@register_rule("ACCOUNT_BLOCKED", "account", 18, "Transaction on blocked account")
def _r5(df):
    return df["account_status"] == "BLOCKED"


@register_rule("ACCOUNT_DORMANT", "account", 12, "Dormant account activity")
def _r6(df):
    return df["account_status"] == "DORMANT"


@register_rule("ACCOUNT_FROZEN", "account", 10, "Frozen account")
def _r7(df):
    return df["freeze_status"] == "Y"


# ------------------------------------------------------------- Amount (cap 15)
@register_rule("AMOUNT_STATISTICAL_OUTLIER", "amount", 10, "Amount is a statistical outlier for its transaction type")
def _r8(df):
    return df["amount_zscore_within_type"].abs() > 3


@register_rule("AMOUNT_HIGH_VALUE", "amount", 15, "High-value transaction amount")
def _r9(df):
    return df["transaction_amount"] > HIGH_VALUE_TXN_THRESHOLD_INR


# --------------------------------------------------- Behavioral (cap 15, ML)
@register_rule("BEHAVIORAL_ANOMALY", "behavioral", 15, "Unusual customer behaviour pattern (ML anomaly detection)")
def _r10(df):
    return df["behavioral_anomaly_score"] > 0.85


# ------------------------------------------------------- Fraud signals (cap 15)
@register_rule("POSSIBLE_DUPLICATE", "fraud_signals", 8, "Possible duplicate transaction")
def _r11(df):
    return df["is_possible_duplicate"]


@register_rule("SETTLEMENT_INCONSISTENCY", "fraud_signals", 7, "Settlement status inconsistent with transaction status")
def _r12(df):
    return (df["transaction_status"] == "SUCCESS") & (df["settlement_status"] == "FAILED")


@register_rule("NEW_UNVERIFIED_BENEFICIARY", "fraud_signals", 6, "First-time beneficiary for this customer")
def _r13(df):
    return df["is_new_beneficiary"] & (df["transaction_amount"] > HIGH_VALUE_TXN_THRESHOLD_INR / 2)


@register_rule("MISSING_IP_ADDRESS", "fraud_signals", 5, "Missing IP address on transaction")
def _r14(df):
    return df["ip_address"].isna() | (df["ip_address"].astype(str).str.len() == 0)


# --------------------------------------------------------- Governance (cap 15)
@register_rule("FUTURE_DATED_TXN", "governance", 15, "Future-dated transaction")
def _r15(df):
    return df["transaction_datetime"] > pd.Timestamp.now()


@register_rule("ACCOUNT_CUSTOMER_MISMATCH", "governance", 12, "Suspicious customer-account mapping")
def _r16(df):
    return df["account_customer_mismatch"].fillna(False)


@register_rule("INVALID_CURRENCY", "governance", 8, "Invalid or unsupported currency code")
def _r17(df):
    from core.config import ALLOWED_CURRENCIES

    return ~df["currency"].isin(ALLOWED_CURRENCIES)


def reason_lookup() -> dict[str, Rule]:
    """Map a rule's human-readable reason string back to its Rule (category/points/id)."""
    return {r.reason: r for r in _REGISTRY}


def apply_rules(features_df: pd.DataFrame) -> pd.DataFrame:
    """Returns one row per transaction: category point totals (capped) + reasons list."""
    n = len(features_df)
    category_points = {cat: np.zeros(n) for cat in RISK_WEIGHTS}
    reasons_per_row: list[list[tuple[float, str]]] = [[] for _ in range(n)]

    for rule in _REGISTRY:
        mask = rule.predicate(features_df).fillna(False).to_numpy()
        if not mask.any():
            continue
        category_points[rule.category][mask] += rule.points
        idxs = np.flatnonzero(mask)
        for i in idxs:
            reasons_per_row[i].append((rule.points, rule.reason))

    result = pd.DataFrame(index=features_df.index)
    for cat, weight in RISK_WEIGHTS.items():
        if cat == "behavioral":
            continue  # behavioral is folded in from anomaly score directly by scoring.py
        result[f"{cat}_points"] = np.minimum(category_points[cat], weight)

    ordered_reasons = [
        [reason for _, reason in sorted(rl, key=lambda t: -t[0])] for rl in reasons_per_row
    ]
    result["rule_reasons"] = ordered_reasons
    return result
