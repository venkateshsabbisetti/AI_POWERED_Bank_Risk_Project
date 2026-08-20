import streamlit as st

from core.audit.store import decided_entity_ids, fetch_history, record_decision
from core.governance.checks import mask_pii
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("Human Review & Final Decision")
result = run_pipeline()
scored = result.transactions_scored

st.markdown(
    "AI detects and recommends; a human reviewer makes the final banking decision. "
    "Decisions below are written to a persistent audit trail (`audit/audit_trail.db`)."
)

tab_queue, tab_history = st.tabs(["📋 Review Queue", "🗂️ Decision History"])

with tab_queue:
    already_decided = decided_entity_ids("transaction")
    flagged = scored[scored["risk_bucket"].isin(["High", "Critical"])]
    queue = flagged[~flagged["transaction_id"].isin(already_decided)].sort_values(
        "risk_score", ascending=False
    )

    st.metric("Items Awaiting Review", len(queue))

    if len(queue) == 0:
        st.success("No flagged transactions awaiting review.")
    else:
        options = queue["transaction_id"].tolist()
        selected_id = st.selectbox("Select a flagged transaction", options)
        row = queue[queue["transaction_id"] == selected_id].iloc[0]
        display_row = mask_pii(queue[queue["transaction_id"] == selected_id]).iloc[0]

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Transaction:** {row['transaction_id']}")
            st.markdown(f"**Customer:** {display_row['customer_name'] if 'customer_name' in display_row else row['customer_id']}")
            st.markdown(f"**Amount:** {row['transaction_amount']:,.2f} {row['currency']}")
            st.markdown(f"**Account Status:** {row['account_status']} · **KYC Status:** {row['kyc_status']}")
            st.markdown("**Reasons:**")
            for r in row["reasons"]:
                st.markdown(f"- {r}")
            st.info(f"**AI Recommendation:** {row['recommendation']}")
        with col2:
            st.metric("Risk Score", f"{row['risk_score']:.0f}")
            st.metric("Bucket", row["risk_bucket"])
            st.metric("Confidence", f"{row['confidence']*100:.0f}%")

        with st.form("decision_form"):
            decision = st.radio("Human Decision", ["APPROVE", "REJECT", "ESCALATE"], horizontal=True)
            reviewer_name = st.text_input("Reviewer Name")
            note = st.text_area("Reviewer Note")
            submitted = st.form_submit_button("Submit Decision")
            if submitted:
                record_decision(
                    entity_type="transaction",
                    entity_id=row["transaction_id"],
                    ai_risk_score=float(row["risk_score"]),
                    ai_bucket=row["risk_bucket"],
                    ai_reasons=row["reasons"],
                    ai_recommendation=row["recommendation"],
                    human_decision=decision,
                    reviewer_note=note,
                    reviewer_name=reviewer_name,
                )
                st.success(f"Decision '{decision}' recorded for {row['transaction_id']}.")
                st.rerun()

with tab_history:
    history = fetch_history("transaction")
    if len(history) == 0:
        st.info("No decisions recorded yet.")
    else:
        st.dataframe(history, width="stretch", height=450)
