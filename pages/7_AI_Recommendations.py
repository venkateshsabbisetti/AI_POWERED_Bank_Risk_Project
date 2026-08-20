import streamlit as st

from core.governance.checks import mask_pii
from core.insights.recommendations import top_recommendations
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("AI Recommendations")
result = run_pipeline()
scored = result.transactions_scored
inc = result.incidents_enriched

st.subheader("Prioritized Transaction Actions")
top_txn = top_recommendations(scored, n=15)
top_txn = mask_pii(top_txn)

for _, row in top_txn.iterrows():
    with st.expander(
        f"🔴 {row['transaction_id']} · {row['risk_bucket']} · Score {row['risk_score']:.0f} · "
        f"Confidence {row['confidence']*100:.0f}%"
    ):
        st.markdown("**Reasons:**")
        for r in row["reasons"]:
            st.markdown(f"- {r}")
        st.markdown(f"**Recommendation:** {row['recommendation']}")
        st.progress(min(1.0, row["confidence"]))

st.divider()
st.subheader("Prioritized Incident Actions")
top_inc = inc[inc["reasons"].apply(len) > 0].sort_values(
    "module_occurrence_30d", ascending=False
).head(10)

for _, row in top_inc.iterrows():
    with st.expander(f"🟠 {row['incident_id']} · {row['severity']} · {row['application_module']}"):
        st.markdown("**Reasons:**")
        for r in row["reasons"]:
            st.markdown(f"- {r}")
        st.markdown(f"**Recommendation:** {row['recommendation']}")
