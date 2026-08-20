import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from core.config import RISK_BUCKET_COLORS
from core.governance.checks import mask_pii
from core.pipeline import run_pipeline
from core.ui.layout import page_shell

page_shell("Banking Risk Dashboard")
result = run_pipeline()
scored = result.transactions_scored

st.subheader("Scored Transactions")
display_cols = [
    "transaction_id", "customer_id", "account_id", "transaction_amount", "currency",
    "account_status", "kyc_status", "risk_score", "risk_bucket", "reasons", "recommendation",
]
display_df = mask_pii(scored[display_cols].copy())
display_df["reasons"] = display_df["reasons"].apply(lambda r: "; ".join(r) if r else "")

gb = GridOptionsBuilder.from_dataframe(display_df)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)
gb.configure_default_column(filter=True, sortable=True, resizable=True)
gb.configure_column("risk_score", sort="desc")
AgGrid(display_df, gridOptions=gb.build(), theme="balham", height=420, fit_columns_on_grid_load=False)

st.divider()
col1, col2 = st.columns(2)

with col1:
    heat = scored.pivot_table(
        index="transaction_channel", columns="risk_bucket", values="transaction_id", aggfunc="count", fill_value=0
    )
    heat = heat.reindex(columns=["Low", "Medium", "High", "Critical"], fill_value=0)
    fig = px.imshow(heat, text_auto=True, aspect="auto", title="Anomaly Heatmap: Channel x Risk Bucket",
                     color_continuous_scale="Reds")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig, width="stretch")

with col2:
    seg = scored.groupby(["customer_segment", "risk_bucket"]).size().reset_index(name="count")
    fig2 = px.bar(
        seg, x="customer_segment", y="count", color="risk_bucket", barmode="stack",
        color_discrete_map=RISK_BUCKET_COLORS, title="Customer Risk Segmentation",
    )
    fig2.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig2, width="stretch")

col3, col4 = st.columns(2)
with col3:
    acct = scored.groupby(["account_status", "risk_bucket"]).size().reset_index(name="count")
    fig3 = px.bar(
        acct, x="account_status", y="count", color="risk_bucket", barmode="stack",
        color_discrete_map=RISK_BUCKET_COLORS, title="Account Risk Analysis",
    )
    fig3.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380)
    st.plotly_chart(fig3, width="stretch")

with col4:
    fraud = scored.groupby("fraud_flag").agg(
        count=("transaction_id", "count"), mean_score=("risk_score", "mean")
    ).reset_index()
    fig4 = px.bar(fraud, x="fraud_flag", y="mean_score", color="fraud_flag",
                  title="Fraud Indicator vs. Mean Risk Score",
                  color_discrete_map={"Y": "#ef4444", "N": "#22c55e"})
    fig4.update_layout(template="plotly_dark", paper_bgcolor="#0b1220", height=380, showlegend=False)
    st.plotly_chart(fig4, width="stretch")
