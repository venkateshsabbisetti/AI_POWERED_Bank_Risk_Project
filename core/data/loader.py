"""Cached CSV readers for the eight source datasets."""
import pandas as pd
import streamlit as st

from core.config import CSV_PATHS


def _normalize_codes(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
    return df


@st.cache_data(show_spinner=False)
def load_customers() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATHS["customers"], parse_dates=["customer_since"])
    return _normalize_codes(df, ["risk_category", "kyc_status", "customer_status", "customer_segment"])


@st.cache_data(show_spinner=False)
def load_accounts() -> pd.DataFrame:
    df = pd.read_csv(
        CSV_PATHS["accounts"],
        parse_dates=["opening_date", "last_transaction_date"],
    )
    return _normalize_codes(df, ["account_type", "currency", "account_status", "freeze_status"])


@st.cache_data(show_spinner=False)
def load_transactions() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATHS["transactions"], parse_dates=["transaction_datetime"])
    # Rename the dataset's own pre-existing risk_score to avoid colliding with
    # our computed risk_score column; kept as an independent baseline for
    # comparison on the Model Evaluation page.
    df = df.rename(columns={"risk_score": "baseline_risk_score"})
    return _normalize_codes(
        df,
        [
            "transaction_type",
            "transaction_channel",
            "currency",
            "transaction_status",
            "failure_reason",
            "settlement_status",
            "fraud_flag",
        ],
    )


@st.cache_data(show_spinner=False)
def load_incidents() -> pd.DataFrame:
    df = pd.read_csv(
        CSV_PATHS["incidents"],
        parse_dates=["reported_datetime", "resolved_datetime"],
    )
    return _normalize_codes(
        df,
        ["severity", "priority", "environment", "incident_status", "assigned_team", "sla_breached"],
    )


@st.cache_data(show_spinner=False)
def load_api_logs() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATHS["api_logs"], parse_dates=["timestamp"])
    return _normalize_codes(
        df, ["api_name", "request_method", "environment", "error_code", "timeout_flag"]
    )


@st.cache_data(show_spinner=False)
def load_application_logs() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATHS["application_logs"], parse_dates=["timestamp"])
    return _normalize_codes(df, ["log_level", "application_module", "service_name", "error_code"])


@st.cache_data(show_spinner=False)
def load_test_cases() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATHS["test_cases"], parse_dates=["last_execution_date"])
    return _normalize_codes(
        df, ["test_module", "test_type", "priority", "automation_status", "execution_status"]
    )


@st.cache_data(show_spinner=False)
def load_reference_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATHS["reference_data"])
    return _normalize_codes(df, ["reference_type", "code"])


def load_all() -> dict[str, pd.DataFrame]:
    return {
        "customers": load_customers(),
        "accounts": load_accounts(),
        "transactions": load_transactions(),
        "incidents": load_incidents(),
        "api_logs": load_api_logs(),
        "application_logs": load_application_logs(),
        "test_cases": load_test_cases(),
        "reference_data": load_reference_data(),
    }
