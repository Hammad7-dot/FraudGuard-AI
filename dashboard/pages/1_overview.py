import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.services.analytics_service import AnalyticsService  # noqa: E402
from dashboard.components.theme import (empty_state, page_header, section_title,  # noqa: E402
                                         sidebar_brand)

st.set_page_config(page_title="Overview — FraudGuard AI", page_icon="📊", layout="wide")
sidebar_brand()
page_header("📊", "Overview", "Portfolio-wide KPIs across every scored transaction.")

init_db()
db = SessionLocal()
service = AnalyticsService(db)

try:
    overview = service.overview()

    section_title("Volume & outcomes")
    cols = st.columns(4)
    cols[0].metric("Total Transactions", f"{overview.total_transactions:,}")
    cols[1].metric("Fraud Detected", f"{overview.fraud_detected:,}")
    cols[2].metric("Fraud Rate", f"{overview.fraud_rate * 100:.2f}%")
    cols[3].metric("Blocked", f"{overview.blocked:,}")

    section_title("Risk & performance")
    cols2 = st.columns(4)
    cols2[0].metric("Review", f"{overview.review:,}")
    cols2[1].metric("Avg Risk Score", f"{overview.avg_risk_score:.1f}")
    cols2[2].metric("High-Risk Count", f"{overview.high_risk_count:,}")
    cols2[3].metric("Avg Processing Time", f"{overview.avg_processing_time_ms:.1f} ms")

    trends = service.fraud_trends(hours=24 * 7)
    section_title("Fraud rate — last 7 days")
    if trends.points:
        df = pd.DataFrame([p.model_dump() for p in trends.points])
        st.area_chart(df.set_index("bucket")["fraud_rate"], color="#5E6AD2")
    else:
        empty_state("No transaction data yet. Run `python scripts/seed_db.py 100` to populate sample data.")
except Exception as exc:
    st.warning(f"Could not load overview: {exc}")
finally:
    db.close()
