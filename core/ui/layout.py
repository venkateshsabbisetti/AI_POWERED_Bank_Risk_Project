"""Shared page shell used by app.py and every page under pages/."""
import streamlit as st

from core.ui.banner import render_banner

_CONFIGURED_KEY = "_page_config_set"


def page_shell(title: str, icon: str = "🏦") -> None:
    if not st.session_state.get(_CONFIGURED_KEY):
        try:
            st.set_page_config(
                page_title=f"{title} | Banking Risk Platform",
                page_icon=icon,
                layout="wide",
                initial_sidebar_state="expanded",
            )
        except st.errors.StreamlitAPIException:
            pass
        st.session_state[_CONFIGURED_KEY] = True

    render_banner()

    with st.sidebar:
        st.markdown("### 🏦 Banking Risk Platform")
        st.caption("AI Detects & Recommends · Human Decides")
        if st.button("🔄 Refresh Pipeline Data", width="stretch"):
            from core.pipeline import run_pipeline

            run_pipeline.clear()
            st.rerun()
        st.divider()

    st.title(title)
