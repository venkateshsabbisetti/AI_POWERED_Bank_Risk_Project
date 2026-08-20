import pandas as pd
import plotly.express as px
import streamlit as st

from core.observability.store import fetch_pipeline_runs
from core.observability.trace import trace_incident, trace_transaction
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("Observability & Traceability")
result = run_pipeline()
scored = result.transactions_scored

tab_obs, tab_trace = st.tabs(["📊 Pipeline Observability", "🔍 Entity Traceability"])

with tab_obs:
    runs = fetch_pipeline_runs(limit=20)
    if runs.empty:
        st.info("No pipeline runs recorded yet.")
    else:
        latest = runs.iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Last Run (UTC)", pd.to_datetime(latest["started_at"]).strftime("%Y-%m-%d %H:%M:%S"))
        c2.metric("Duration", f"{latest['duration_seconds']:.2f}s" if latest["duration_seconds"] else "N/A")
        c3.metric("Status", latest["status"])
        total_rows = sum(latest["row_counts"].values()) if latest["row_counts"] else 0
        c4.metric("Rows Processed", f"{total_rows:,}")
        c5.metric(
            "Data Quality Issues",
            f"{latest['data_quality_issue_rows']:,}" if pd.notna(latest["data_quality_issue_rows"]) else "N/A",
        )

        if latest["status"] == "FAILED":
            st.error(f"Last run failed: {latest['error_message']}")

        st.divider()
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Stage Execution Timing (Last Run)")
            stage_df = pd.DataFrame(
                list(latest["stage_durations"].items()), columns=["stage", "seconds"]
            )
            if len(stage_df):
                fig = px.bar(stage_df, x="stage", y="seconds", title="Pipeline Stage Durations")
                fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No stage timing recorded for this run.")
        with col2:
            st.subheader("Anomaly Model Parameters")
            st.json(latest["anomaly_model_info"])

        st.divider()
        st.subheader("Pipeline Run History")
        st.caption(
            "A new row appears each time the pipeline actually recomputes -- on first "
            "load, or after clicking '🔄 Refresh Pipeline Data' in the sidebar. Page "
            "views in between reuse the cached result and do not add a row."
        )
        history_view = runs[["run_id", "started_at", "duration_seconds", "status", "data_quality_issue_rows"]].copy()
        history_view["total_rows"] = runs["row_counts"].apply(lambda d: sum(d.values()) if d else 0)
        st.dataframe(history_view, width="stretch", hide_index=True)

with tab_trace:
    st.caption(
        "Trace a single transaction or incident end-to-end: raw record → engineered "
        "features → triggered rules → anomaly score → final risk score → recommendation "
        "→ human decision. Everything shown is pulled directly from the pipeline's own "
        "computed output, not recomputed or approximated."
    )
    entity_type = st.radio("Entity Type", ["Transaction", "Incident"], horizontal=True)

    if entity_type == "Transaction":
        flagged_ids = scored.loc[
            scored["risk_bucket"].isin(["High", "Critical"]), "transaction_id"
        ].tolist()
        entity_id = st.selectbox(
            "Select or type a transaction ID",
            options=flagged_ids,
            index=0 if flagged_ids else None,
            accept_new_options=True,
        )
        if entity_id:
            trace = trace_transaction(entity_id, result)
            if trace is None:
                st.warning(f"No transaction found with ID '{entity_id}'.")
            else:
                with st.expander("1️⃣ Raw Transaction Record", expanded=True):
                    st.json(trace["raw"])
                with st.expander("2️⃣ Feature Engineering"):
                    st.json(trace["features"])
                with st.expander("3️⃣ Rule Engine — Triggered Rules"):
                    if trace["rules_fired"]:
                        st.dataframe(pd.DataFrame(trace["rules_fired"]), width="stretch", hide_index=True)
                    else:
                        st.success("No rules triggered for this transaction.")
                with st.expander("4️⃣ AI Anomaly Detection"):
                    st.json(trace["anomaly"])
                with st.expander("5️⃣ Risk Scoring — Category Points"):
                    cat_df = pd.DataFrame(
                        list(trace["category_points"].items()), columns=["category", "points"]
                    )
                    fig = px.bar(cat_df, x="category", y="points", title="Points Contributed per Category")
                    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=320)
                    st.plotly_chart(fig, width="stretch")
                with st.expander("6️⃣ Final Score & Recommendation", expanded=True):
                    f = trace["final"]
                    fc1, fc2, fc3 = st.columns(3)
                    fc1.metric("Risk Score", f"{f['risk_score']:.0f}")
                    fc2.metric("Bucket", f["risk_bucket"])
                    fc3.metric("Confidence", f"{f['confidence']*100:.0f}%")
                    st.info(f"**Recommendation:** {f['recommendation']}")
                with st.expander("7️⃣ Human Review"):
                    hr = trace["human_review"]
                    if hr is None or hr.empty:
                        st.warning("No human decision recorded yet for this transaction.")
                    else:
                        st.dataframe(hr, width="stretch", hide_index=True)

    else:
        incident_ids = result.incidents_enriched["incident_id"].tolist()
        entity_id = st.selectbox(
            "Select or type an incident ID",
            options=incident_ids,
            index=0 if incident_ids else None,
            accept_new_options=True,
        )
        if entity_id:
            trace = trace_incident(entity_id, result)
            if trace is None:
                st.warning(f"No incident found with ID '{entity_id}'.")
            else:
                with st.expander("1️⃣ Raw Incident Record", expanded=True):
                    st.json({k: str(v) for k, v in trace["raw"].items()})
                with st.expander("2️⃣ Computed Fields"):
                    st.json(trace["computed"])
                with st.expander("3️⃣ Reasons & Recommendation", expanded=True):
                    if trace["reasons"]:
                        for r in trace["reasons"]:
                            st.markdown(f"- {r}")
                    else:
                        st.success("No risk reasons flagged for this incident.")
                    st.info(f"**Recommendation:** {trace['recommendation']}")
                with st.expander("4️⃣ Human Review"):
                    st.warning("No review workflow implemented for incidents yet -- only flagged transactions go through Human Review today.")
