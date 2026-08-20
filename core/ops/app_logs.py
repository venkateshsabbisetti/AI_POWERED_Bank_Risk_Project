"""Error-code analysis, root-cause breakdown, and cross-system correlation."""
import pandas as pd


def enrich_application_logs(app_logs: pd.DataFrame) -> pd.DataFrame:
    df = app_logs.copy()
    df["is_error"] = df["log_level"].isin(["ERROR", "FATAL"])
    return df


def error_code_breakdown(enriched: pd.DataFrame) -> pd.DataFrame:
    errs = enriched[enriched["is_error"]]
    return (
        errs.groupby(["error_code", "application_module"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )


def failure_trend(enriched: pd.DataFrame) -> pd.DataFrame:
    df = enriched.copy()
    df["date"] = df["timestamp"].dt.to_period("D").dt.to_timestamp()
    return (
        df[df["is_error"]]
        .groupby(["date", "log_level"])
        .size()
        .reset_index(name="error_count")
    )


def correlate_with_incidents_and_api(
    app_logs: pd.DataFrame, api_logs: pd.DataFrame, incidents: pd.DataFrame
) -> pd.DataFrame:
    """Join application error logs to API logs and incidents via shared transaction_id."""
    errs = app_logs[app_logs["is_error"] & app_logs["transaction_id"].notna()]
    joined = errs.merge(
        api_logs[["transaction_id", "api_name", "response_code", "error_code"]].rename(
            columns={"error_code": "api_error_code"}
        ),
        on="transaction_id",
        how="left",
    )
    joined = joined.merge(
        incidents[["related_transaction_id", "incident_id", "severity", "sla_breached"]].rename(
            columns={"related_transaction_id": "transaction_id"}
        ),
        on="transaction_id",
        how="left",
    )
    return joined
