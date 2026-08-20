import plotly.express as px
import streamlit as st

from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("Executive Overview")
result = run_pipeline()
scored = result.transactions_scored

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Total Customers", f"{len(result.raw['customers']):,}")
c2.metric("Total Accounts", f"{len(result.raw['accounts']):,}")
c3.metric("Total Transactions", f"{len(scored):,}")
c4.metric("Total Incidents", f"{len(result.raw['incidents']):,}")
c5.metric("Failed Tests", f"{(result.test_cases_enriched['is_fail']).sum():,}")
c6.metric("APIs Monitored", f"{result.raw['api_logs']['api_name'].nunique():,}")
c7.metric("SLA Breach Rate", f"{(result.incidents_enriched['sla_breached']=='Y').mean()*100:.1f}%")

st.divider()

col1, col2 = st.columns(2)
with col1:
    bucket_counts = scored["risk_bucket"].value_counts().reindex(
        ["Low", "Medium", "High", "Critical"]
    ).fillna(0).reset_index()
    bucket_counts.columns = ["Risk Bucket", "Count"]
    fig = px.pie(
        bucket_counts, names="Risk Bucket", values="Count",
        color="Risk Bucket",
        color_discrete_map={"Low": "#22c55e", "Medium": "#eab308", "High": "#f97316", "Critical": "#ef4444"},
        title="Overall Risk Distribution",
    )
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig, width="stretch")

with col2:
    daily = scored.set_index("transaction_datetime").resample("D").size().reset_index(name="volume")
    daily.columns = ["date", "volume"]
    fig2 = px.line(daily, x="date", y="volume", title="Daily Transaction Volume")
    fig2.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig2, width="stretch")

st.subheader("Data Quality Issues Detected")
if len(result.issues):
    st.dataframe(result.issues.sort_values("row_count", ascending=False), width="stretch")
else:
    st.success("No data quality issues detected.")
