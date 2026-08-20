"""Slow-API detection, HTTP failure analysis, and service health scoring."""
import numpy as np
import pandas as pd


def enrich_api_logs(api_logs: pd.DataFrame) -> pd.DataFrame:
    df = api_logs.copy()
    p95 = df.groupby("api_name")["response_time_ms"].transform(lambda s: s.quantile(0.95))
    df["is_slow"] = df["response_time_ms"] > p95
    df["is_http_failure"] = df["response_code"] >= 500
    df["is_client_error"] = df["response_code"].between(400, 499)
    df["is_timeout"] = df["timeout_flag"] == "Y"
    return df


def api_health_scores(enriched: pd.DataFrame) -> pd.DataFrame:
    grouped = enriched.groupby("api_name").agg(
        total_calls=("log_id", "count"),
        failure_rate=("is_http_failure", "mean"),
        timeout_rate=("is_timeout", "mean"),
        slow_rate=("is_slow", "mean"),
        p95_response_ms=("response_time_ms", lambda s: s.quantile(0.95)),
        mean_response_ms=("response_time_ms", "mean"),
    ).reset_index()

    grouped["health_score"] = (
        100
        - grouped["failure_rate"] * 50
        - grouped["timeout_rate"] * 30
        - grouped["slow_rate"] * 20
    ).clip(0, 100).round(1)
    return grouped.sort_values("health_score")


def response_time_trend(enriched: pd.DataFrame) -> pd.DataFrame:
    df = enriched.copy()
    df["date"] = df["timestamp"].dt.to_period("D").dt.to_timestamp()
    return (
        df.groupby(["date", "environment"])["response_time_ms"]
        .mean()
        .reset_index(name="avg_response_time_ms")
    )


def status_code_distribution(enriched: pd.DataFrame) -> pd.DataFrame:
    def bucket(code):
        if code < 300:
            return "2xx Success"
        if code < 400:
            return "3xx Redirect"
        if code < 500:
            return "4xx Client Error"
        return "5xx Server Error"

    df = enriched.copy()
    df["status_bucket"] = df["response_code"].apply(bucket)
    return df.groupby("status_bucket").size().reset_index(name="count")
