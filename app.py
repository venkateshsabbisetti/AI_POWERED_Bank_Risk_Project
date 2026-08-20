import plotly.graph_objects as go
import streamlit as st

from core.governance.checks import compliance_score
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("AI Powered Banking Risk & Production Incident Monitoring")

st.markdown(
    """
This platform analyzes banking transactions, customer/account data, production
incidents, API logs, application logs, test execution results, and reference
datasets to proactively identify fraud risks, operational failures, SLA
breaches, data-quality issues, technical hotspots, and governance violations.

**Principle:** AI Detects and Recommends · Human Reviews · Human Makes the Final Banking Decision
"""
)

with st.spinner("Loading pipeline..."):
    result = run_pipeline()

st.subheader("Pipeline Stages")
stages = [
    "Data Validation", "Feature Engineering", "Rule Engine + AI Anomaly Detection",
    "Risk Scoring", "Incident Intelligence", "AI Insights", "Recommendations",
    "Human Review", "Final Decision",
]
cols = st.columns(len(stages))
for c, stage in zip(cols, stages):
    c.markdown(
        f"<div style='background:#132339;border:1px solid #16326b;border-radius:8px;"
        f"padding:10px 6px;text-align:center;font-size:0.78rem;color:#e8eef7;min-height:70px;'>"
        f"{stage}</div>",
        unsafe_allow_html=True,
    )

st.divider()
st.subheader("At a Glance")

scored = result.transactions_scored
incidents = result.incidents_enriched
api_logs = result.api_logs_enriched
tests = result.test_cases_enriched
gov_metrics = result.governance_metrics
gov_score = compliance_score(gov_metrics)

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Customers", f"{len(result.raw['customers']):,}")
c2.metric("Accounts", f"{len(result.raw['accounts']):,}")
c3.metric("Transactions", f"{len(scored):,}")
c4.metric("Incidents", f"{len(result.raw['incidents']):,}")
c5.metric("Failed Tests", f"{tests['is_fail'].sum():,}")
c6.metric("APIs Monitored", f"{result.raw['api_logs']['api_name'].nunique():,}")
c7.metric("High/Critical Risk", f"{(scored['risk_bucket'].isin(['High','Critical'])).sum():,}")

st.divider()
col_risk, col_ops, col_gov = st.columns(3)

with col_risk:
    st.markdown("##### 🏦 Banking Risk")
    bucket_counts = scored["risk_bucket"].value_counts().reindex(["Low", "Medium", "High", "Critical"]).fillna(0)
    fig = go.Figure(
        go.Bar(
            x=bucket_counts.index,
            y=bucket_counts.values,
            marker_color=["#22c55e", "#eab308", "#f97316", "#ef4444"],
        )
    )
    fig.update_layout(
        title="Transaction Risk Distribution",
        template="plotly_dark",
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        height=300,
        margin=dict(t=40, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Details → **Banking Risk** dashboard")

with col_ops:
    st.markdown("##### ⚙️ Operational Health")
    breach_rate = (incidents["sla_breached"] == "Y").mean() * 100
    open_incidents = (incidents["incident_status"] != "CLOSED").sum()
    mean_resolution = incidents["resolution_hours"].mean()
    st.metric("SLA Breach Rate", f"{breach_rate:.1f}%")
    st.metric("Open Incidents", f"{open_incidents:,}")
    st.metric("Mean Resolution Time", f"{mean_resolution:.1f} h" if mean_resolution == mean_resolution else "N/A")
    st.caption("Details → **Operational** / **API Monitoring** dashboards")

with col_gov:
    st.markdown("##### 🛡️ Governance & Compliance")
    attention_count = sum(1 for m in gov_metrics if m.status == "ATTENTION")
    compliant_count = sum(1 for m in gov_metrics if m.status == "COMPLIANT")
    st.metric("Compliance Score", f"{gov_score}/100")
    st.metric("Controls Compliant", f"{compliant_count} / {len(gov_metrics)}")
    st.metric("Controls Needing Attention", f"{attention_count}")
    st.caption("Full breakdown & improvement plan → **Governance** dashboard")

st.divider()
issue_count = int(result.issues["row_count"].sum()) if len(result.issues) else 0
if issue_count:
    st.warning(f"⚠️ {issue_count} data-quality issue rows detected across validation rules — see **Executive Overview** for details.")
else:
    st.success("✅ No data-quality issues detected.")

st.caption("Use the sidebar to navigate between Executive Overview, Banking Risk, Operational, "
           "API Monitoring, Application Log Intelligence, Test Analytics, AI Recommendations, "
           "Governance, Human Review, and Model Evaluation dashboards.")
