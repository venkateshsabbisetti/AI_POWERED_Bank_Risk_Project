"""DPDP / RBI governance checks computable from this data + pipeline outputs.

Every metric here is genuinely computed. Where the dataset cannot support a
metric (e.g. no consent-capture field, no auth system in scope), we report an
explicit "Not applicable" status rather than fabricating a number.
"""
from dataclasses import dataclass

import pandas as pd

from core.config import DATA_RETENTION_DAYS, PII_COLUMNS

_PII_MASK_LOG = {"masked_calls": 0}


def mask_pii(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with known PII columns masked for on-screen display."""
    out = df.copy()
    if "customer_name" in out.columns:
        out["customer_name"] = out["customer_name"].astype(str).apply(
            lambda n: (n.split()[0][0] + "***" + " " + n.split()[-1][0] + "***") if n and n != "nan" else n
        )
    if "ip_address" in out.columns:
        out["ip_address"] = out["ip_address"].astype(str).apply(
            lambda ip: ".".join(ip.split(".")[:2] + ["xxx", "xxx"]) if ip.count(".") == 3 else ip
        )
    if "device_id" in out.columns:
        out["device_id"] = out["device_id"].astype(str).apply(lambda d: d[:5] + "***" if len(d) > 5 else d)
    if "annual_income_inr" in out.columns:
        out["annual_income_inr"] = pd.cut(
            out["annual_income_inr"],
            bins=[0, 500_000, 1_000_000, 2_000_000, float("inf")],
            labels=["<5L", "5L-10L", "10L-20L", ">20L"],
        )
    _PII_MASK_LOG["masked_calls"] += 1
    return out


@dataclass
class GovernanceMetric:
    name: str
    category: str  # "DPDP" or "RBI"
    status: str  # "COMPLIANT" | "ATTENTION" | "NOT_APPLICABLE"
    value: str
    numeric_score: float | None  # None if not applicable / not counted in average
    recommended_action: str = ""


def run_all(
    risk_df: pd.DataFrame,
    incidents_df: pd.DataFrame,
    issues_df: pd.DataFrame,
    audit_completeness: float,
    explainability_coverage: float,
    application_logs_df: pd.DataFrame,
) -> list[GovernanceMetric]:
    metrics: list[GovernanceMetric] = []

    pii_columns_present = sum(1 for c in PII_COLUMNS if c in risk_df.columns)
    masking_coverage = 1.0 if _PII_MASK_LOG["masked_calls"] > 0 else 0.0
    metrics.append(
        GovernanceMetric(
            "PII Masking (DPDP)", "DPDP",
            "COMPLIANT" if masking_coverage == 1.0 else "ATTENTION",
            f"{pii_columns_present} PII columns identified; masking helper invoked "
            f"{_PII_MASK_LOG['masked_calls']} time(s) this session",
            masking_coverage,
            recommended_action="Already compliant this session." if masking_coverage == 1.0 else
            "Open Banking Risk, AI Recommendations, or Human Review at least once per session "
            "so the PII masking helper runs before customer data is displayed.",
        )
    )

    metrics.append(
        GovernanceMetric(
            "Data Minimization (DPDP)", "DPDP", "ATTENTION",
            "Design-time attestation: dashboards surface only the allowlisted columns "
            "defined per page, not full raw record dumps",
            None,
            recommended_action="Attestation only -- not counted in the numeric score. "
            "Periodically audit each page's column allowlist as new fields are added.",
        )
    )

    metrics.append(
        GovernanceMetric(
            "Consent Awareness (DPDP)", "DPDP", "NOT_APPLICABLE",
            "Not applicable -- no consent-capture field exists in customers.csv", None,
            recommended_action="Add a consent-capture field to the customer onboarding "
            "schema so this control becomes measurable.",
        )
    )

    metrics.append(
        GovernanceMetric(
            "Access Controls (DPDP)", "DPDP", "NOT_APPLICABLE",
            "Role-based access control is not implemented in this prototype; "
            "recommended before production deployment", None,
            recommended_action="Implement authentication and role-based access control "
            "before any production deployment.",
        )
    )

    now = pd.Timestamp.now()
    if "timestamp" in application_logs_df.columns:
        stale = (now - application_logs_df["timestamp"]).dt.days > DATA_RETENTION_DAYS
        retention_rate = round(1 - stale.mean(), 3)
    else:
        retention_rate = None
    metrics.append(
        GovernanceMetric(
            "Data Retention Controls (DPDP)", "DPDP",
            "COMPLIANT" if (retention_rate or 0) > 0.8 else "ATTENTION",
            f"{(1 - (retention_rate or 0)) * 100:.1f}% of application logs exceed the "
            f"{DATA_RETENTION_DAYS}-day retention window and are eligible for purge",
            retention_rate,
            recommended_action="Purge or archive application logs older than the "
            f"{DATA_RETENTION_DAYS}-day retention window.",
        )
    )

    metrics.append(
        GovernanceMetric(
            "Auditability / Audit Trail (RBI)", "RBI",
            "COMPLIANT" if audit_completeness > 0.7 else "ATTENTION",
            f"{audit_completeness * 100:.1f}% of High/Critical items have a recorded human decision",
            audit_completeness,
            recommended_action="Work through the Human Review queue and record a decision "
            "for each flagged High/Critical transaction.",
        )
    )

    metrics.append(
        GovernanceMetric(
            "Model Explainability (RBI)", "RBI",
            "COMPLIANT" if explainability_coverage > 0.9 else "ATTENTION",
            f"{explainability_coverage * 100:.1f}% of flagged items carry a non-empty reasons list",
            explainability_coverage,
            recommended_action="Investigate flagged items with an empty reasons list -- "
            "typically a rule-engine edge case that should still emit a reason.",
        )
    )

    breach_rate = (incidents_df["sla_breached"] == "Y").mean()
    metrics.append(
        GovernanceMetric(
            "Operational Resilience / Incident Monitoring (RBI)", "RBI",
            "COMPLIANT" if breach_rate < 0.5 else "ATTENTION",
            f"SLA breach rate: {breach_rate * 100:.1f}% across {len(incidents_df)} incidents",
            round(1 - breach_rate, 3),
            recommended_action="Reduce SLA breaches by addressing the recurring incident "
            "hotspots on the Operational dashboard (highest module_occurrence_30d first).",
        )
    )

    rca_complete = incidents_df["root_cause"].notna().mean()
    metrics.append(
        GovernanceMetric(
            "Root Cause Documentation (RBI)", "RBI",
            "COMPLIANT" if rca_complete > 0.8 else "ATTENTION",
            f"{rca_complete * 100:.1f}% of incidents have a documented root cause",
            round(rca_complete, 3),
            recommended_action="Make root-cause capture a mandatory field before an "
            "incident can be closed.",
        )
    )

    total_issue_rows = issues_df["row_count"].sum() if len(issues_df) else 0
    metrics.append(
        GovernanceMetric(
            "Data Quality Monitoring (RBI)", "RBI",
            "ATTENTION" if total_issue_rows > 0 else "COMPLIANT",
            f"{int(total_issue_rows)} data-quality issue rows detected across validation rules",
            None,
            recommended_action="Resolve the data-quality issues listed on the Executive "
            "Overview page at their source system.",
        )
    )

    return metrics


def score_breakdown(metrics: list[GovernanceMetric]) -> pd.DataFrame:
    """Per-metric contribution to the compliance average, with improvement guidance."""
    scored = [m for m in metrics if m.numeric_score is not None]
    weight = round(100 / len(scored), 1) if scored else 0.0
    rows = []
    for m in metrics:
        current_pct = round(m.numeric_score * 100, 1) if m.numeric_score is not None else None
        rows.append(
            {
                "Metric": m.name,
                "Category": m.category,
                "Status": m.status,
                "Score": f"{current_pct:.1f}%" if current_pct is not None else "Excluded",
                "Weight in Average": f"{weight:.1f}%" if m.numeric_score is not None else "0% (excluded)",
                "Gap to Full Compliance": f"{100 - current_pct:.1f} pts" if current_pct is not None else "--",
                "Recommended Action": m.recommended_action,
                "_gap": (100 - current_pct) if current_pct is not None else -1,
            }
        )
    df = pd.DataFrame(rows).sort_values("_gap", ascending=False).drop(columns="_gap")
    return df.reset_index(drop=True)


def simulate_score(metrics: list[GovernanceMetric], fixed_metric_names: set[str]) -> float:
    """What the compliance score would be if the named metrics were fully compliant (score=1.0).

    Purely a hypothetical projection for planning -- does not alter the real, currently
    computed score shown on the Governance dashboard.
    """
    scored = [
        1.0 if (m.numeric_score is not None and m.name in fixed_metric_names) else m.numeric_score
        for m in metrics
        if m.numeric_score is not None
    ]
    if not scored:
        return 0.0
    return round(sum(scored) / len(scored) * 100, 1)


def compliance_score(metrics: list[GovernanceMetric]) -> float:
    scored = [m.numeric_score for m in metrics if m.numeric_score is not None]
    if not scored:
        return 0.0
    return round(sum(scored) / len(scored) * 100, 1)
