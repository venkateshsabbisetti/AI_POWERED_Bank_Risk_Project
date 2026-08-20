"""Join customers/accounts/transactions and derive risk-relevant features."""
import numpy as np
import pandas as pd


def build_transaction_features(
    transactions: pd.DataFrame, accounts: pd.DataFrame, customers: pd.DataFrame
) -> pd.DataFrame:
    df = transactions.merge(
        accounts[
            ["account_id", "customer_id", "account_status", "freeze_status",
             "account_type", "current_balance", "available_balance", "opening_date"]
        ],
        on="account_id",
        how="left",
        suffixes=("", "_acct"),
    )
    df["account_customer_mismatch"] = df["customer_id"] != df["customer_id_acct"]

    df = df.merge(
        customers[
            ["customer_id", "kyc_status", "customer_status", "risk_category",
             "customer_segment", "customer_since"]
        ],
        left_on="customer_id",
        right_on="customer_id",
        how="left",
    )

    now = pd.Timestamp.now()
    df["customer_tenure_days"] = (now - df["customer_since"]).dt.days.clip(lower=0)
    df["account_age_days"] = (now - df["opening_date"]).dt.days.clip(lower=0)

    df["log_amount"] = np.log1p(df["transaction_amount"].clip(lower=0))
    type_stats = df.groupby("transaction_type")["transaction_amount"].transform(
        lambda s: (s - s.mean()) / (s.std(ddof=0) if s.std(ddof=0) > 0 else 1)
    )
    df["amount_zscore_within_type"] = type_stats

    df["hour_of_day"] = df["transaction_datetime"].dt.hour

    # New-beneficiary flag: first time this (customer_id, beneficiary_id) pair appears
    df = df.sort_values("transaction_datetime")
    pair_key = df["customer_id"].astype(str) + "|" + df["beneficiary_id"].astype(str)
    df["is_new_beneficiary"] = ~pair_key.duplicated(keep="first")

    # Possible duplicate transaction: same account+amount within 60 seconds
    dup_key = (
        df["account_id"].astype(str)
        + "|"
        + df["transaction_amount"].round(2).astype(str)
    )
    df["_dup_key"] = dup_key
    df["is_possible_duplicate"] = df.duplicated(subset=["_dup_key"], keep=False) & (
        df.groupby("_dup_key")["transaction_datetime"].transform(
            lambda s: (s.max() - s.min()).total_seconds() if len(s) > 1 else 999999
        )
        < 60
    )
    df = df.drop(columns=["_dup_key"])

    df["balance_utilization_ratio"] = np.where(
        df["current_balance"] > 0,
        1 - (df["available_balance"] / df["current_balance"]).clip(0, 2),
        0,
    )

    return df.sort_index()
