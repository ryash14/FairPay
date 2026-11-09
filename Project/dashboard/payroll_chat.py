"""The payroll chat: answers from the documents, one language model call per question."""
import streamlit as st

from config import config
from dashboard.api_client import call_service
from dashboard.ui import apply_style, badge_text


def render_payroll_chat_page():
    apply_style()
    st.header(config.PAGE_CHAT)
    guide, conversation = st.columns([1, 2.3], gap="large")

    with guide:
        with st.container(border=True):
            st.markdown("**What I answer**")
            st.markdown("  \n".join(badge_text(kind, config.CHAT_TYPE_BADGE_COLOURS) for kind in config.CHAT_TYPE_OPTIONS))
            schedules = ", ".join(config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION.values())
            st.caption(f"Answers come only from {config.ORGANISATION_NAME}'s pay schedules ({schedules}), the Pay Query "
                       f"Policy, the commitments ({config.COMMITMENTS_DOCUMENT}) and the resolution guides. A rate is "
                       f"always read from its own classification's schedule. I remember your last "
                       f"{config.CHAT_HISTORY_TURN_LIMIT} exchanges.")
            if st.session_state.get("role") not in config.CHAT_FIGURE_ROLES:
                st.info("You hear a pay query's status and when it last changed, never a figure. "
                        + config.CHAT_AMOUNTS_IN_WRITING_MESSAGE)

    with conversation:
        turns = call_service("GET", "/chat/turns", {"turn_limit": config.CHAT_PAGE_TURN_LIMIT}, None, None)
        if not turns:
            st.caption("Ask about a rate, a rule, what an employee can do, or where a pay query has got to.")
        for turn in reversed(turns):
            with st.chat_message("user"):
                st.markdown(turn["question_text"])
            with st.chat_message("assistant"):
                tags = [badge_text(turn["question_type"], config.CHAT_TYPE_BADGE_COLOURS)]
                if turn["was_refused"]:
                    tags.append(badge_text("Refused"))
                st.markdown(" ".join(tags))
                st.markdown(turn["answer_text"])
                if turn["source_documents"]:
                    st.caption(f"From {turn['source_documents']}")

    question = st.chat_input("Ask the payroll assistant")
    if question is not None:
        trimmed = question.strip()
        if len(trimmed) < config.CHAT_QUESTION_MINIMUM_CHARACTERS:
            st.warning("Please ask a whole question.")
        else:
            call_service("POST", "/chat/ask", None, {"question": trimmed},
                         "Searching the documents. This makes one language model call.")
            st.rerun()
