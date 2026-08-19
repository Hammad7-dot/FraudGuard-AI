"""Shared visual theme for the FraudGuard AI dashboard.

Design language adapted from Linear's DESIGN.md (voltagent/awesome-design-md):
an ultra-dark near-black canvas (#010102) with a four-step surface ladder,
a single chromatic accent (lavender-blue #5e6ad2) reserved for the brand
mark, focus rings, and primary CTAs only — never decoratively — light-gray
primary text, hairline 1px borders, 12-16px card radii, and a 4px spacing
base. Centralizes CSS and small render helpers (KPI cards, badges, section
headers) so every page shares one consistent, polished look instead of bare
st.metric/st.dataframe defaults.
"""
from __future__ import annotations

import html as _html

import streamlit as st

# ---------------------------------------------------------------- tokens --
# Linear-inspired palette: near-black canvas, 4-step surface ladder,
# lavender-blue as the single accent (never decorative).

CANVAS = "#010102"
SURFACE_1 = "#0F1011"   # base card surface
SURFACE_2 = "#141516"
SURFACE_3 = "#191A1B"   # elevated / hovered surface
BORDER = "#232426"      # hairline border

TEXT = "#F7F8F8"        # primary text
TEXT_MUTED = "#8A8F98"  # secondary text

ACCENT = "#5E6AD2"       # lavender-blue — brand mark, focus rings, primary CTAs only
ACCENT_HOVER = "#828FFF"
ACCENT_SOFT = "#5E6AD21F"

RISK_COLORS = {
    "LOW": "#4CB782",
    "MEDIUM": "#E2B203",
    "HIGH": "#EB5757",
    "CRITICAL": "#F2555A",
}

DECISION_COLORS = {
    "APPROVE": "#4CB782",
    "REVIEW": "#E2B203",
    "BLOCK": "#F2555A",
}

# kept for backwards-compat imports elsewhere
BG_CARD = SURFACE_1
BG_CARD_BORDER = BORDER

_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    .stApp {{ background: {CANVAS}; }}

    /* ---- layout polish ---- */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }}

    /* hide default streamlit chrome bits that look unfinished */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{background: transparent;}}

    /* ---- sidebar branding ---- */
    section[data-testid="stSidebar"] {{
        background: {SURFACE_1};
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] .stMarkdown p {{
        color: {TEXT_MUTED};
    }}
    section[data-testid="stSidebar"] a {{ color: {TEXT} !important; font-size: 0.88rem; }}
    section[data-testid="stSidebar"] li[data-testid="stSidebarNavItems"] a[aria-current="page"] {{
        background: {ACCENT_SOFT} !important;
        color: {ACCENT_HOVER} !important;
        border-radius: 6px;
    }}

    /* ---- typography ---- */
    h1, h2, h3, p, span, div, label {{ color: {TEXT}; }}
    h1, h2, h3 {{
        letter-spacing: -0.02em;
        font-weight: 600 !important;
    }}
    p {{ color: {TEXT_MUTED}; }}

    /* ---- native metric cards ---- */
    div[data-testid="stMetric"] {{
        background: {SURFACE_1};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 16px 18px 14px 18px;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {TEXT_MUTED} !important;
        font-size: 0.76rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }}
    div[data-testid="stMetricValue"] {{
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
        color: {TEXT} !important;
        font-variant-numeric: tabular-nums;
    }}

    /* ---- dataframes ---- */
    div[data-testid="stDataFrame"] {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        overflow: hidden;
        font-variant-numeric: tabular-nums;
    }}

    /* ---- expander (used by high-risk queue) ---- */
    div[data-testid="stExpander"] {{
        background: {SURFACE_1};
        border: 1px solid {BORDER} !important;
        border-radius: 12px !important;
        margin-bottom: 10px;
    }}
    div[data-testid="stExpander"] summary:hover {{
        background: {SURFACE_3};
    }}

    /* ---- buttons / interactive controls -> accent used sparingly ---- */
    button[kind="primary"], .stButton>button {{
        border-radius: 8px !important;
        background: {ACCENT} !important;
        color: {TEXT} !important;
        border: none !important;
    }}
    div[data-baseweb="select"] > div {{
        border-radius: 8px !important;
        border-color: {BORDER} !important;
        background: {SURFACE_1} !important;
    }}
    input {{ border-radius: 8px !important; background: {SURFACE_1} !important; color: {TEXT} !important; }}
    div[data-testid="stSliderThumbValue"] {{ color: {ACCENT_HOVER} !important; }}
    div[role="slider"] {{ background: {ACCENT} !important; }}
    div[data-baseweb="slider"] div[style*="background-color"] {{ background: {ACCENT} !important; }}

    /* ---- custom components ---- */
    .fg-hero {{
        padding: 36px 34px;
        border-radius: 16px;
        background: {SURFACE_1};
        border: 1px solid {BORDER};
        margin-bottom: 26px;
        position: relative;
        overflow: hidden;
    }}
    .fg-hero::before {{
        content: "";
        position: absolute;
        top: -40%; right: -10%;
        width: 380px; height: 380px;
        background: radial-gradient(circle, {ACCENT}33 0%, transparent 70%);
        pointer-events: none;
    }}
    .fg-hero > * {{ position: relative; z-index: 1; }}
    .fg-hero h1 {{
        margin: 0 0 8px 0;
        font-size: 2rem;
        color: {TEXT} !important;
        font-weight: 600 !important;
        letter-spacing: -0.03em;
    }}
    .fg-hero p {{
        color: {TEXT_MUTED} !important;
        margin: 0;
        font-size: 0.98rem;
        font-weight: 400;
    }}
    .fg-pill {{
        display: inline-block;
        padding: 3px 12px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        margin-right: 6px;
    }}
    .fg-nav-card {{
        background: {SURFACE_1};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        transition: border-color 0.15s ease, background 0.15s ease;
    }}
    .fg-nav-card:hover {{
        border-color: {ACCENT};
        background: {SURFACE_2};
    }}
    .fg-nav-card .fg-icon {{
        font-size: 1.3rem;
        width: 38px; height: 38px;
        display: flex; align-items: center; justify-content: center;
        background: {SURFACE_3};
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    .fg-nav-card h4 {{ margin: 12px 0 4px 0; color: {TEXT}; font-weight: 600; }}
    .fg-nav-card p {{ color: {TEXT_MUTED}; font-size: 0.85rem; margin: 0; }}

    .fg-section-title {{
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {TEXT_MUTED};
        font-weight: 600;
        margin: 32px 0 10px 0;
    }}

    .fg-empty {{
        border: 1px dashed {BORDER};
        border-radius: 12px;
        padding: 28px;
        text-align: center;
        color: {TEXT_MUTED};
        background: {SURFACE_1};
        font-size: 0.9rem;
    }}
</style>
"""


def inject_base_style() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    inject_base_style()
    sub = f"<p>{_html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="fg-hero">
            <h1>{icon} {_html.escape(title)}</h1>
            {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(label: str) -> None:
    st.markdown(f'<div class="fg-section-title">{_html.escape(label)}</div>', unsafe_allow_html=True)


def pill(text: str, color: str) -> str:
    return (
        f'<span class="fg-pill" style="background:{color}26; color:{color}; '
        f'border:1px solid {color}55;">{_html.escape(str(text))}</span>'
    )


def risk_pill(level: str) -> str:
    return pill(level, RISK_COLORS.get(level, TEXT_MUTED))


def decision_pill(decision: str) -> str:
    return pill(decision, DECISION_COLORS.get(decision, TEXT_MUTED))


def empty_state(message: str) -> None:
    st.markdown(f'<div class="fg-empty">{_html.escape(message)}</div>', unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.sidebar.markdown(
        f"""
        <div style="padding: 4px 0 18px 0; border-bottom:1px solid {BORDER}; margin-bottom: 12px;">
            <div style="font-size:1.05rem; font-weight:700; color:{TEXT};">◆ FraudGuard AI</div>
            <div style="color:{TEXT_MUTED}; font-size:0.76rem;">Real-time risk engine</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
