import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.services.analytics_service import AnalyticsService  # noqa: E402
from dashboard.components.risk_copilot import render_risk_copilot  # noqa: E402
from dashboard.components.theme import (empty_state, page_header, risk_pill,  # noqa: E402
                                         section_title, sidebar_brand)

st.set_page_config(page_title="High Risk — FraudGuard AI", page_icon="🚨", layout="wide")
sidebar_brand()
page_header("🚨", "High Risk Queue", "HIGH and CRITICAL transactions ranked by risk score, with plain-language reasoning.")

init_db()
db = SessionLocal()

try:
    service = AnalyticsService(db)
    high_risk = service.high_risk(limit=100)
    if not high_risk.items:
        empty_state("No high-risk transactions yet. Run `python scripts/seed_db.py 100` to populate sample data.")
    else:
        items = list(high_risk.items)

        controls = st.columns([2, 2, 2])
        level_filter = controls[0].multiselect(
            "Risk level", sorted({i.risk_level for i in items})
        )
        decision_filter = controls[1].multiselect(
            "Decision", sorted({i.decision for i in items})
        )
        sort_by = controls[2].selectbox(
            "Sort by", ["Risk score (desc)", "Risk score (asc)"], index=0
        )

        if level_filter:
            items = [i for i in items if i.risk_level in level_filter]
        if decision_filter:
            items = [i for i in items if i.decision in decision_filter]
        items = sorted(
            items, key=lambda i: i.risk_score, reverse=(sort_by == "Risk score (desc)")
        )

        header_cols = st.columns([3, 1])
        header_cols[0].markdown(f"### {len(items)} items awaiting review")
        export_df = pd.DataFrame(
            [
                {
                    "transaction_id": i.transaction_id,
                    "user_id": i.user_id,
                    "amount": i.amount,
                    "risk_score": i.risk_score,
                    "risk_level": i.risk_level,
                    "decision": i.decision,
                    "reasons": "; ".join(i.reasons),
                }
                for i in items
            ]
        )
        header_cols[1].download_button(
            "⬇️ Export CSV",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name="fraudguard_high_risk_queue.csv",
            mime="text/csv",
            use_container_width=True,
        )

        for item in items:
            label = f"{item.transaction_id}  ·  {item.risk_level}  ·  score {item.risk_score:.0f}  ·  {item.decision}"
            with st.expander(label):
                render_risk_copilot(item.model_dump(), item.reasons)
finally:
    db.close()
