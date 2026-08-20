import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from core.ops.api_monitoring import api_health_scores, response_time_trend, status_code_distribution
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("API Monitoring")
result = run_pipeline()
api = result.api_logs_enriched

health = api_health_scores(api)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Slow API Calls", f"{api['is_slow'].sum():,}")
c2.metric("HTTP Failures (5xx)", f"{api['is_http_failure'].sum():,}")
c3.metric("Timeout Rate", f"{api['is_timeout'].mean()*100:.1f}%")
c4.metric("Mean Health Score", f"{health['health_score'].mean():.1f}")

st.divider()
col1, col2 = st.columns(2)
with col1:
    status_dist = status_code_distribution(api)
    fig = px.bar(status_dist, x="status_bucket", y="count", color="status_bucket",
                 title="HTTP Status Code Distribution",
                 color_discrete_map={
                     "2xx Success": "#22c55e", "3xx Redirect": "#3b82f6",
                     "4xx Client Error": "#eab308", "5xx Server Error": "#ef4444",
                 })
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380, showlegend=False)
    st.plotly_chart(fig, width="stretch")

with col2:
    trend = response_time_trend(api)
    fig2 = px.line(trend, x="date", y="avg_response_time_ms", color="environment",
                   title="Response Time Trend by Environment")
    fig2.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig2, width="stretch")

st.subheader("Service Health Scores (Lowest First = Highest Priority)")
gb = GridOptionsBuilder.from_dataframe(health)
gb.configure_default_column(filter=True, sortable=True, resizable=True)
gb.configure_column("health_score", sort="asc")
AgGrid(health, gridOptions=gb.build(), theme="balham", height=420)
