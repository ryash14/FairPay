"""The query queue page: every open pay query, most money at stake first."""
from decimal import Decimal

import pandas as pd
import streamlit as st

from config import config
from dashboard.api_client import call_service
from dashboard.ui import apply_style, aud, caption


def render_query_queue_page():
    apply_style()
    st.header(config.PAGE_QUEUE)
    caption("Every open pay query, with its pay period worked out again on the entitled classification and every rate "
            "read from that classification's own schedule. Most money at stake first.")

    everything = call_service("GET", "/queue", {"direction": config.QUEUE_DIRECTION_ALL}, None, None)
    warranted = sum(1 for row in everything if row["correction_warranted"])
    underpaid = sum(1 for row in everything if row["direction"] == config.UNDERPAID)
    overpaid = sum(1 for row in everything if row["direction"] == config.OVERPAID)
    top = everything[0] if everything else None
    columns = st.columns(5)
    columns[0].metric("Open pay queries", len(everything))
    columns[1].metric(f"Wrong by AUD {config.CORRECTION_THRESHOLD_AUD} or more", warranted)
    columns[2].metric("Underpaid", underpaid)
    columns[3].metric("Overpaid", overpaid)
    columns[4].metric("Most at stake", aud(top["money_at_stake_aud"]) if top else "—",
                      help=top["query_reference"] if top else None)

    direction = st.segmented_control("Show", config.QUEUE_DIRECTION_OPTIONS, default=config.QUEUE_DIRECTION_ALL,
                                     key="queue_direction") or config.QUEUE_DIRECTION_ALL
    rows = call_service("GET", "/queue", {"direction": direction}, None, None)
    if not rows:
        st.info("No open pay query has that direction.")
        return

    table = pd.DataFrame([{
        "Reference": row["query_reference"], "Centre": row["payroll_centre"],
        "Paid as": row["paid_classification"], "Entitled to": row["entitled_classification"],
        "Paid": float(Decimal(row["amount_paid_aud"])), "Pay owed": float(Decimal(row["entitled_pay_aud"])),
        "At stake": float(Decimal(row["money_at_stake_aud"])), "Direction": row["direction"],
        "Correct it": row["correction_warranted"], "Correction score": row["correction_probability"],
        "Band": row["correction_band"],
    } for row in rows])
    money = st.column_config.NumberColumn(format="AUD %.2f")
    selection = st.dataframe(
        table, hide_index=True, width="stretch", height=560, on_select="rerun", selection_mode="single-row",
        key="queue_table",
        column_config={
            "Reference": st.column_config.TextColumn(pinned=True),
            "Paid": money, "Pay owed": money, "At stake": money,
            "Correct it": st.column_config.CheckboxColumn(help=f"Out by AUD {config.CORRECTION_THRESHOLD_AUD} or more"),
            "Correction score": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0, format="%.2f"),
        })
    chosen = selection.selection.rows if selection and hasattr(selection, "selection") else []
    if chosen:
        reference = table.iloc[chosen[0]]["Reference"]
        st.session_state["focus_query"] = reference
        st.success(f"{reference} is ready on the {config.PAGE_QUERY} page.")
    else:
        st.caption(f"{len(rows)} pay queries shown. Select a row to open it on the {config.PAGE_QUERY} page.")
