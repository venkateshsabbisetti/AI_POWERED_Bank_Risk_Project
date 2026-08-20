import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from core.ops.incidents import severity_trend, team_summary
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("Operational Dashboard")
result = run_pipeline()
inc = result.incidents_enriched

c1, c2, c3, c4 = st.columns(4)
c1.metric("Open Incidents", f"{(inc['incident_status'] != 'CLOSED').sum():,}")
c2.metric("SLA Breaches", f"{(inc['sla_breached']=='Y').sum():,}")
c3.metric("SLA Breach Rate", f"{(inc['sla_breached']=='Y').mean()*100:.1f}%")
c4.metric("Mean Resolution (hrs)", f"{inc['resolution_hours'].mean():.1f}")

st.divider()
col1, col2 = st.columns(2)
with col1:
    trend = severity_trend(inc)
    fig = px.line(trend, x="report_date", y="incident_count", color="severity",
                  title="Incident Severity Trend (Monthly)")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig, width="stretch")

with col2:
    team = team_summary(inc)
    fig2 = px.bar(team.sort_values("mean_resolution_hours"), x="assigned_team", y="mean_resolution_hours",
                  title="Mean Resolution Time by Team", color="sla_breach_rate",
                  color_continuous_scale="Reds")
    fig2.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig2, width="stretch")

st.subheader("Team-wise Incident Analysis")
team_display = team_summary(inc)
team_display["sla_breach_rate"] = (team_display["sla_breach_rate"] * 100).round(1)
team_display["mean_resolution_hours"] = team_display["mean_resolution_hours"].round(1)
gb = GridOptionsBuilder.from_dataframe(team_display)
gb.configure_default_column(filter=True, sortable=True, resizable=True)
AgGrid(team_display, gridOptions=gb.build(), theme="balham", height=280)

st.subheader("Flagged Incidents (Breached / Repeated / Missing RCA)")
flagged = inc[inc["reasons"].apply(len) > 0].copy()
flagged["reasons"] = flagged["reasons"].apply(lambda r: "; ".join(r))
cols = ["incident_id", "incident_title", "severity", "assigned_team", "reasons", "recommendation"]
gb2 = GridOptionsBuilder.from_dataframe(flagged[cols])
gb2.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
gb2.configure_default_column(filter=True, sortable=True, resizable=True)
AgGrid(flagged[cols], gridOptions=gb2.build(), theme="balham", height=400)
