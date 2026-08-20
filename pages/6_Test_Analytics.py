import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from core.ops.test_analytics import failure_reason_breakdown, module_summary, release_readiness_score
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("Test Analytics")
result = run_pipeline()
tests = result.test_cases_enriched

pass_rate = tests["is_pass"].mean() * 100
readiness = release_readiness_score(tests)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Failed Tests", f"{tests['is_fail'].sum():,}")
c2.metric("Pass Rate", f"{pass_rate:.1f}%")
c3.metric("Quality Score", f"{(pass_rate*0.7 + tests['is_automated'].mean()*100*0.3):.1f}")
c4.metric("Release Readiness", f"{readiness:.1f}/100")

st.divider()
col1, col2 = st.columns(2)
with col1:
    breakdown = failure_reason_breakdown(tests)
    fig = px.bar(breakdown, x="failure_reason", y="count", title="Failures by Reason")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig, width="stretch")

with col2:
    module_fail = tests.groupby("test_module")["is_fail"].sum().reset_index(name="fail_count")
    fig2 = px.bar(module_fail.sort_values("fail_count", ascending=False), x="test_module", y="fail_count",
                  title="Failures by Test Module")
    fig2.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig2, width="stretch")

st.subheader("Module Quality Summary")
summary = module_summary(tests)
summary["pass_rate"] = (summary["pass_rate"] * 100).round(1)
summary["automation_rate"] = (summary["automation_rate"] * 100).round(1)
gb = GridOptionsBuilder.from_dataframe(summary)
gb.configure_default_column(filter=True, sortable=True, resizable=True)
gb.configure_column("quality_score", sort="asc")
AgGrid(summary, gridOptions=gb.build(), theme="balham", height=380)
