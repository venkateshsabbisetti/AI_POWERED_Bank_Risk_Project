import plotly.graph_objects as go
import streamlit as st

from core.governance.checks import compliance_score, score_breakdown, simulate_score
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("Governance Dashboard")
result = run_pipeline()
metrics = result.governance_metrics
score = compliance_score(metrics)

fig = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": "Overall Compliance Score"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#3b82f6"},
            "steps": [
                {"range": [0, 50], "color": "#ef4444"},
                {"range": [50, 80], "color": "#eab308"},
                {"range": [80, 100], "color": "#22c55e"},
            ],
        },
    )
)
fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=280)
st.plotly_chart(fig, width="stretch")

st.caption(
    "The compliance score averages only genuinely computable sub-scores below. "
    "Checks marked 'Not Applicable' are excluded from the numeric average and shown "
    "as qualitative status only, to avoid overstating what this prototype can measure."
)

st.divider()

status_icon = {"COMPLIANT": "🟢", "ATTENTION": "🟡", "NOT_APPLICABLE": "⚪"}

st.subheader("DPDP Act Compliance")
for m in [m for m in metrics if m.category == "DPDP"]:
    st.markdown(f"{status_icon[m.status]} **{m.name}** — {m.value}")

st.subheader("RBI Governance Controls")
for m in [m for m in metrics if m.category == "RBI"]:
    st.markdown(f"{status_icon[m.status]} **{m.name}** — {m.value}")

st.divider()
st.subheader("Score Breakdown & Improvement Plan")
st.caption(
    "Each scored metric contributes equally to the compliance average above. This table "
    "ranks them by how many points each is costing, with the concrete action that would "
    "close that gap -- nothing here changes the score itself, it only explains it."
)
breakdown = score_breakdown(metrics)
st.dataframe(
    breakdown,
    width="stretch",
    hide_index=True,
    height=(len(breakdown) + 1) * 35 + 3,
    column_config={
        "Metric": st.column_config.TextColumn(width="medium"),
        "Recommended Action": st.column_config.TextColumn(width="large"),
    },
)

attention_names = {
    m.name for m in metrics if m.status == "ATTENTION" and m.numeric_score is not None
}
if attention_names:
    projected = simulate_score(metrics, attention_names)
    st.info(
        f"**What-if projection:** if every metric currently marked 🟡 ATTENTION above the "
        f"'Recommended Action' column were fully addressed, the compliance score would rise "
        f"from **{score}** to **{projected}/100**. This is a planning projection, not a "
        f"change to the live score -- it moves only as those real actions happen."
    )
else:
    st.success("No ATTENTION items remain among the scored metrics.")

st.caption(
    "For full pipeline run history and a step-by-step trace of exactly how any single "
    "transaction or incident reached its final score, see the **Observability & "
    "Traceability** dashboard."
)
