import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.evaluation.metrics import (
    evaluate_fraud_model,
    explainability_coverage,
    failure_clustering_rank_agreement,
    incident_prioritization_consistency,
    sla_detection_accuracy,
    slow_api_detection_rate,
    threshold_sweep,
)
from core.ops.test_analytics import module_summary
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("Model Evaluation")
result = run_pipeline()
scored = result.transactions_scored

st.markdown(
    "`fraud_flag` is held out strictly as ground truth on this page and is **never** "
    "used as an input to the rule engine or anomaly model, to avoid label leakage."
)

eval_result = evaluate_fraud_model(scored)

if "error" in eval_result:
    st.warning(eval_result["error"])
else:
    st.subheader("Classification Metrics vs. Ground Truth (fraud_flag)")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Precision", f"{eval_result['precision']*100:.1f}%")
    c2.metric("Recall", f"{eval_result['recall']*100:.1f}%")
    c3.metric("F1 Score", f"{eval_result['f1_score']*100:.1f}%")
    c4.metric("ROC AUC", f"{eval_result['roc_auc']*100:.1f}%")
    c5.metric("False Positive Rate", f"{eval_result['false_positive_rate']*100:.1f}%")
    c6.metric("False Negative Rate", f"{eval_result['false_negative_rate']*100:.1f}%")

    st.caption(
        f"Baseline (dataset's own pre-existing risk_score > 60): "
        f"Precision {eval_result['baseline_comparison']['baseline_precision']*100:.1f}%, "
        f"Recall {eval_result['baseline_comparison']['baseline_recall']*100:.1f}%, "
        f"F1 {eval_result['baseline_comparison']['baseline_f1']*100:.1f}%"
    )

    col1, col2 = st.columns(2)
    with col1:
        roc = eval_result["roc_curve"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=roc["fpr"], y=roc["tpr"], mode="lines", name="ROC Curve"))
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random", line=dict(dash="dash")))
        fig.update_layout(title="ROC Curve", xaxis_title="FPR", yaxis_title="TPR",
                           template="plotly_dark", paper_bgcolor="#0b1220", height=380)
        st.plotly_chart(fig, width="stretch")

    with col2:
        cm = eval_result["confusion_matrix"]
        fig2 = px.imshow(
            [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]],
            text_auto=True,
            x=["Pred: Not Fraud", "Pred: Fraud"],
            y=["Actual: Not Fraud", "Actual: Fraud"],
            color_continuous_scale="Blues",
            title="Confusion Matrix",
        )
        fig2.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
        st.plotly_chart(fig2, width="stretch")

    st.subheader("Threshold Sweep")
    sweep = threshold_sweep(scored)
    fig3 = px.line(sweep, x="threshold", y=["precision", "recall", "f1"],
                   title="Precision / Recall / F1 vs. Risk Score Threshold")
    fig3.add_vline(x=61, line_dash="dash", annotation_text="High-risk cutoff (61)")
    fig3.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig3, width="stretch")

st.divider()
st.subheader("Operational Metrics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("SLA Detection Accuracy", f"{sla_detection_accuracy(result.incidents_enriched)*100:.1f}%")
c2.metric("Incident Prioritization Consistency", f"{incident_prioritization_consistency(result.raw['incidents'])*100:.1f}%")
c3.metric("Slow API Detection Rate", f"{slow_api_detection_rate(result.api_logs_enriched)*100:.1f}%")
rank_agreement = failure_clustering_rank_agreement(module_summary(result.test_cases_enriched))
c4.metric("Test Failure Rank Agreement", f"{rank_agreement:.2f}" if rank_agreement == rank_agreement else "N/A")

st.divider()
st.subheader("Governance Metrics")
c1, c2 = st.columns(2)
c1.metric("Explainability Coverage", f"{explainability_coverage(scored)*100:.1f}%")
audit_metric = next((m for m in result.governance_metrics if "Audit" in m.name), None)
c2.metric("Audit Completeness", audit_metric.value if audit_metric else "N/A")
