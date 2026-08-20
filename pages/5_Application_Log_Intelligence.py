import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from core.ops.app_logs import correlate_with_incidents_and_api, error_code_breakdown, failure_trend
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("Application Log Intelligence")
result = run_pipeline()
logs = result.application_logs_enriched

c1, c2, c3 = st.columns(3)
c1.metric("Total Log Entries", f"{len(logs):,}")
c2.metric("Error/Fatal Entries", f"{logs['is_error'].sum():,}")
c3.metric("Error Rate", f"{logs['is_error'].mean()*100:.1f}%")

st.divider()
col1, col2 = st.columns(2)
with col1:
    breakdown = error_code_breakdown(logs).head(20)
    fig = px.bar(breakdown, x="error_code", y="count", color="application_module",
                 title="Error-Code Analysis by Module")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=400)
    st.plotly_chart(fig, width="stretch")

with col2:
    trend = failure_trend(logs)
    fig2 = px.line(trend, x="date", y="error_count", color="log_level", title="Failure Trend Over Time")
    fig2.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=400)
    st.plotly_chart(fig2, width="stretch")

st.subheader("Root-Cause Breakdown by Module")
module_errors = logs[logs["is_error"]].groupby("application_module").size().reset_index(name="error_count")
fig3 = px.bar(module_errors.sort_values("error_count", ascending=False), x="application_module", y="error_count",
              title="Errors by Application Module")
fig3.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=350)
st.plotly_chart(fig3, width="stretch")

st.subheader("Correlation Analysis: App Logs -> API Logs -> Incidents")
correlated = correlate_with_incidents_and_api(logs, result.raw["api_logs"], result.raw["incidents"])
correlated_display = correlated[
    ["log_id", "application_module", "error_code", "api_name", "response_code",
     "api_error_code", "incident_id", "severity", "sla_breached"]
].dropna(subset=["incident_id"]).head(200)
gb = GridOptionsBuilder.from_dataframe(correlated_display)
gb.configure_default_column(filter=True, sortable=True, resizable=True)
AgGrid(correlated_display, gridOptions=gb.build(), theme="balham", height=380)
