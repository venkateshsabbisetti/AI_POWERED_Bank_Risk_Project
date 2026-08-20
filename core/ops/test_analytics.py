"""Test pass-rate, quality score, and release-readiness analytics."""
import pandas as pd


def enrich_test_cases(test_cases: pd.DataFrame) -> pd.DataFrame:
    df = test_cases.copy()
    df["is_pass"] = df["execution_status"] == "PASS"
    df["is_fail"] = df["execution_status"] == "FAIL"
    df["is_blocked"] = df["execution_status"] == "BLOCKED"
    df["is_automated"] = df["automation_status"].isin(["AUTOMATED", "CANDIDATE"])
    return df


def module_summary(enriched: pd.DataFrame) -> pd.DataFrame:
    total = enriched.groupby("test_module").size().rename("total_tests")
    summary = enriched.groupby("test_module").agg(
        pass_count=("is_pass", "sum"),
        fail_count=("is_fail", "sum"),
        blocked_count=("is_blocked", "sum"),
        automation_rate=("is_automated", "mean"),
    )
    summary = summary.join(total)
    summary["pass_rate"] = (summary["pass_count"] / summary["total_tests"]).round(3)
    summary["quality_score"] = (
        summary["pass_rate"] * 70 + summary["automation_rate"] * 30
    ).round(1)
    return summary.reset_index().sort_values("quality_score")


def failure_reason_breakdown(enriched: pd.DataFrame) -> pd.DataFrame:
    return (
        enriched[enriched["is_fail"] & enriched["failure_reason"].notna()]
        .groupby("failure_reason")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )


def release_readiness_score(enriched: pd.DataFrame) -> float:
    pass_rate = enriched["is_pass"].mean()
    automation_rate = enriched["is_automated"].mean()
    blocked_rate = enriched["is_blocked"].mean()
    score = pass_rate * 60 + automation_rate * 30 - blocked_rate * 20
    return round(max(0.0, min(100.0, score)), 1)
