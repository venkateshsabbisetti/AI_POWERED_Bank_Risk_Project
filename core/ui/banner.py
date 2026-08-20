"""CSS-only scrolling marquee banner + enterprise dark-blue theme injection."""
import streamlit as st

from core.config import COLOR_ACCENT, COLOR_NAVY, COLOR_NAVY_LIGHT, COLOR_PANEL, COLOR_TEXT

_BANNER_TEXT = "AI Powered Banking Risk Application"

_STYLE_BLOCK = f"""
<style>
.app-banner {{
    background: linear-gradient(90deg, {COLOR_NAVY} 0%, {COLOR_NAVY_LIGHT} 100%);
    overflow: hidden;
    white-space: nowrap;
    border-bottom: 3px solid {COLOR_ACCENT};
    padding: 10px 0;
    margin: -1rem -1rem 1rem -1rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.4);
}}
.app-banner__track {{
    display: inline-flex;
    animation: app-banner-scroll 18s linear infinite;
}}
.app-banner__track span {{
    padding: 0 4rem;
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: {COLOR_TEXT};
    text-transform: uppercase;
}}
@keyframes app-banner-scroll {{
    from {{ transform: translateX(0); }}
    to {{ transform: translateX(-50%); }}
}}
@media (max-width: 768px) {{
    .app-banner__track span {{ font-size: 0.85rem; padding: 0 2rem; }}
}}

/* Enterprise banking dark-blue theme touches */
[data-testid="stSidebar"] {{
    background-color: {COLOR_NAVY};
    border-right: 1px solid {COLOR_NAVY_LIGHT};
}}
div[data-testid="stMetric"] {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_NAVY_LIGHT};
    border-radius: 8px;
    padding: 12px 16px;
}}
h1, h2, h3 {{
    color: {COLOR_TEXT};
}}
</style>
"""

_BANNER_HTML = f"""
<div class="app-banner">
  <div class="app-banner__track">
    <span>{_BANNER_TEXT}</span><span>{_BANNER_TEXT}</span><span>{_BANNER_TEXT}</span>
    <span>{_BANNER_TEXT}</span><span>{_BANNER_TEXT}</span><span>{_BANNER_TEXT}</span>
  </div>
</div>
"""


def render_banner() -> None:
    st.markdown(_STYLE_BLOCK + _BANNER_HTML, unsafe_allow_html=True)
