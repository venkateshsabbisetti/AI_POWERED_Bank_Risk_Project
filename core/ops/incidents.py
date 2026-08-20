"""SLA breach, hotspot, and repeat-incident intelligence over incidents.csv."""
import pandas as pd


def enrich_incidents(incidents: pd.DataFrame) -> pd.DataFrame:
    df = incidents.copy()
    resolved = df["resolved_datetime"].notna()
    df["resolution_hours"] = None
    df.loc[resolved, "resolution_hours"] = (
        (df.loc[resolved, "resolved_datetime"] - df.loc[resolved, "reported_datetime"]).dt.total_seconds() / 3600
    )
    df["computed_sla_breach"] = df["resolution_hours"].notna() & (
        df["resolution_hours"] > df["sla_hours"]
    )

    df = df.sort_values("reported_datetime")
    df["module_occurrence_30d"] = 0
    for module, group in df.groupby("application_module"):
        times = group["reported_datetime"]
        counts = []
        for t in times:
            window_start = t - pd.Timedelta(days=30)
            counts.append(((times > window_start) & (times <= t)).sum())
        df.loc[group.index, "module_occurrence_30d"] = counts
    df["is_repeated_incident"] = df["module_occurrence_30d"] > 3

    reasons = []
    for _, row in df.iterrows():
        r = []
        if row["sla_breached"] == "Y":
            r.append(f"SLA breached ({row['sla_hours']}h allowed)")
        if row["is_repeated_incident"]:
            r.append(f"Repeated incident in {row['application_module']} ({int(row['module_occurrence_30d'])}x in 30 days)")
        if pd.isna(row["root_cause"]):
            r.append("Missing root cause analysis")
        if pd.isna(row["assigned_engineer"]):
            r.append("Missing incident ownership")
        if row["severity"] in ("SEV1", "SEV2") and row["incident_status"] != "CLOSED":
            r.append(f"Open {row['severity']} incident")
        reasons.append(r)
    df["reasons"] = reasons
    df["recommendation"] = df["reasons"].apply(
        lambda r: "Escalate to incident commander and validate RCA before closure."
        if r
        else "No immediate action required."
    )
    return df.sort_index()


def team_summary(enriched: pd.DataFrame) -> pd.DataFrame:
    return (
        enriched.groupby("assigned_team")
        .agg(
            total_incidents=("incident_id", "count"),
            sla_breach_rate=("sla_breached", lambda s: (s == "Y").mean()),
            mean_resolution_hours=("resolution_hours", "mean"),
            open_incidents=("incident_status", lambda s: (s != "CLOSED").sum()),
        )
        .reset_index()
    )


def severity_trend(enriched: pd.DataFrame) -> pd.DataFrame:
    df = enriched.copy()
    df["report_date"] = df["reported_datetime"].dt.to_period("M").dt.to_timestamp()
    return (
        df.groupby(["report_date", "severity"])
        .size()
        .reset_index(name="incident_count")
    )
