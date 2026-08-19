import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.services.analytics_service import AnalyticsService  # noqa: E402
from dashboard.components.theme import (empty_state, page_header, section_title,  # noqa: E402
                                         sidebar_brand)

st.set_page_config(page_title="Trends — FraudGuard AI", page_icon="📈", layout="wide")
sidebar_brand()
page_header("📈", "Fraud Trends", "Volume, fraud rate, and average risk score over a configurable window.")

init_db()
db = SessionLocal()

try:
    service = AnalyticsService(db)
    hours = st.slider("Window (hours)", 1, 24 * 14, 24 * 7)
    trends = service.fraud_trends(hours=hours)
    if trends.points:
        df = pd.DataFrame([p.model_dump() for p in trends.points]).set_index("bucket")

        latest = trends.points[-1]
        cols = st.columns(3)
        cols[0].metric("Latest bucket volume", f"{latest.transaction_count:,}")
        cols[1].metric("Latest fraud rate", f"{latest.fraud_rate * 100:.2f}%")
        cols[2].metric("Latest avg risk score", f"{latest.avg_risk_score:.1f}")

        section_title("Transactions per bucket")
        st.bar_chart(df["transaction_count"], color="#5E6AD2")
        section_title("Fraud rate per bucket")
        st.line_chart(df["fraud_rate"], color="#EB5757")
        section_title("Average risk score per bucket")
        st.line_chart(df["avg_risk_score"], color="#E2B203")
    else:
        empty_state("No trend data yet. Run `python scripts/seed_db.py 100` to populate sample data.")
finally:
    db.close()
