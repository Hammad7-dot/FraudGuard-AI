import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.models.risk_assessment import RiskAssessment  # noqa: E402
from app.models.transaction import Transaction  # noqa: E402
from dashboard.components.theme import (RISK_COLORS, empty_state, page_header,  # noqa: E402
                                         section_title, sidebar_brand)

st.set_page_config(page_title="Transactions — FraudGuard AI", page_icon="💳", layout="wide")
sidebar_brand()
page_header("💳", "Transactions", "The most recent transactions scored by the risk engine.")

init_db()
db = SessionLocal()

try:
    rows = (
        db.query(Transaction, RiskAssessment)
        .join(RiskAssessment, RiskAssessment.transaction_id == Transaction.transaction_id)
        .order_by(Transaction.timestamp.desc())
        .limit(500)
        .all()
    )
    if rows:
        data = [
            {
                "transaction_id": tx.transaction_id,
                "user_id": tx.user_id,
                "amount": tx.amount,
                "currency": tx.currency,
                "country": tx.country,
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "decision": risk.decision,
                "timestamp": tx.timestamp,
            }
            for tx, risk in rows
        ]
        df = pd.DataFrame(data)

        section_title("Filter")
        fcols = st.columns(3)
        levels = fcols[0].multiselect("Risk level", sorted(df["risk_level"].unique()))
        decisions = fcols[1].multiselect("Decision", sorted(df["decision"].unique()))
        search_user = fcols[2].text_input("User ID contains")

        filtered = df
        if levels:
            filtered = filtered[filtered["risk_level"].isin(levels)]
        if decisions:
            filtered = filtered[filtered["decision"].isin(decisions)]
        if search_user:
            filtered = filtered[filtered["user_id"].str.contains(search_user, case=False, na=False)]

        header_cols = st.columns([3, 1])
        header_cols[0].markdown(f"### Results ({len(filtered):,} of {len(df):,})")
        header_cols[1].download_button(
            "⬇️ Export CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="fraudguard_transactions.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True,
            column_config={
                "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
                "risk_score": st.column_config.ProgressColumn(
                    "Risk Score", min_value=0, max_value=100, format="%.0f"
                ),
                "risk_level": st.column_config.TextColumn("Risk Level"),
                "decision": st.column_config.TextColumn("Decision"),
                "timestamp": st.column_config.DatetimeColumn("Timestamp"),
            },
        )
    else:
        empty_state("No transactions yet. Run `python scripts/seed_db.py 100` to populate sample data.")
finally:
    db.close()
