"""A plain-language explanation panel for a selected transaction."""
from __future__ import annotations

import streamlit as st

from dashboard.components.theme import decision_pill, risk_pill


def render_risk_copilot(transaction: dict, reasons: list[str]) -> None:
    level = transaction.get("risk_level", "LOW")
    decision = transaction.get("decision", "APPROVE")
    score = transaction.get("risk_score", 0)

    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.markdown(
            f"{risk_pill(level)} {decision_pill(decision)}  &nbsp; **Score:** {score:.0f}/100",
            unsafe_allow_html=True,
        )
    with header_cols[1]:
        st.metric("Risk score", f"{score:.0f}", label_visibility="collapsed")

    st.progress(min(max(int(score), 0), 100))

    amount_str = f"{transaction.get('amount', 'N/A')} {transaction.get('currency', '')}".strip()
    plain_language = (
        f"This transaction of **{amount_str}** "
        f"was assigned a risk score of **{score:.0f}/100** ({level}). "
        f"Based on this, the system recommends: **{decision}**."
    )
    st.write(plain_language)

    if reasons:
        st.markdown("**Why:**")
        for r in reasons:
            st.markdown(f"- {r}")
    else:
        st.caption("No specific risk indicators were recorded for this transaction.")
