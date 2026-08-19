"""FraudGuard AI Streamlit dashboard entrypoint. Reads directly from the DB for reliability
in local/demo environments (also works if the API is running, via components that call it)."""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.components.theme import page_header, sidebar_brand, section_title  # noqa: E402

st.set_page_config(page_title="FraudGuard AI", page_icon="🛡️", layout="wide")

sidebar_brand()
page_header(
    "🛡️",
    "FraudGuard AI",
    "Real-time fraud detection & risk engine — FastAPI + XGBoost + Isolation Forest + rule engine",
)

section_title("Explore")

cards = [
    ("📊", "Overview", "KPIs, fraud rate and the weekly trend at a glance."),
    ("💳", "Transactions", "Browse the most recent scored transactions."),
    ("🚨", "High Risk", "Review queue for HIGH/CRITICAL transactions with plain-language reasoning."),
    ("📈", "Trends", "Fraud rate and volume over a configurable time window."),
    ("🧠", "Model Metrics", "Training metrics for the XGBoost classifier and Isolation Forest."),
]

cols = st.columns(len(cards))
for col, (icon, name, desc) in zip(cols, cards):
    with col:
        st.markdown(
            f"""
            <div class="fg-nav-card">
                <div class="fg-icon">{icon}</div>
                <h4>{name}</h4>
                <p>{desc}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("")
st.info(
    "👈 Use the sidebar to navigate between pages. Data is read directly from the configured "
    "`DATABASE_URL` (or the API, if `API_BASE_URL` is set).",
    icon="💡",
)

api_base = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
copilot_url = api_base.rsplit("/api", 1)[0] + "/ui/"
st.markdown(
    f"""
    <a href="{copilot_url}" target="_blank" style="text-decoration:none;">
        <div class="fg-nav-card" style="border-color:#7c7ff2;">
            <div class="fg-icon">🛡️</div>
            <h4>Open Risk Copilot UI</h4>
            <p>The real-time single-page dashboard with live chat-style explanations, same data as this app.</p>
        </div>
    </a>
    """,
    unsafe_allow_html=True,
)
