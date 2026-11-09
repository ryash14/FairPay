"""Step 6: the dashboard. Run with:  streamlit run run_dashboard.py"""
import socket
from urllib.parse import urlparse

import streamlit as st

from config import config
from dashboard.api_client import call_service
from dashboard.audit_trail import render_audit_trail_page
from dashboard.decision_queue import render_decision_queue_page
from dashboard.payroll_chat import render_payroll_chat_page
from dashboard.query_detail import render_query_detail_page
from dashboard.query_queue import render_query_queue_page
from dashboard.ui import apply_style

PAGE_RENDERERS = {
    config.PAGE_QUEUE: (render_query_queue_page, ":material/format_list_numbered:"),
    config.PAGE_QUERY: (render_query_detail_page, ":material/receipt_long:"),
    config.PAGE_DECISION: (render_decision_queue_page, ":material/gavel:"),
    config.PAGE_AUDIT: (render_audit_trail_page, ":material/fact_check:"),
    config.PAGE_CHAT: (render_payroll_chat_page, ":material/forum:"),
}
SESSION_KEYS = ["username", "display_name", "role", "session_token", "pages", "areas"]


def service_is_listening():
    address = urlparse(config.API_BASE_URL)
    try:
        with socket.create_connection((address.hostname, address.port or 80), timeout=2):
            return True
    except OSError:
        return False


def draw_sign_in():
    _, middle, _ = st.columns([1, 1.2, 1])
    with middle:
        st.write("")
        st.title(config.DASHBOARD_TITLE)
        st.caption(config.DASHBOARD_SUBTITLE)
        with st.form("sign_in"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
        if submitted:
            reply = call_service("POST", "/auth/signin", None,
                                 {"username": username.strip(), "password": password}, None)
            st.session_state.update(reply)
            st.rerun()


def draw_sidebar():
    with st.sidebar:
        st.markdown(f"### {config.DASHBOARD_TITLE}")
        st.caption(config.DASHBOARD_SUBTITLE)
        st.divider()
        st.markdown(f"**{st.session_state['display_name']}**  \n{st.session_state['role']}")
        if st.button("Sign out", width="stretch"):
            call_service("POST", "/auth/signout", None, None, None)
            st.session_state.clear()
            st.rerun()


def main():
    st.set_page_config(page_title=config.DASHBOARD_TITLE, layout="wide")
    apply_style()
    if not service_is_listening():
        st.error(f"{config.API_TITLE} is not answering at {config.API_BASE_URL}. Start it from the Project folder with "
                 f"`python3 run_api_service.py`, then reload this page.")
        st.stop()
    if not st.session_state.get("session_token"):
        draw_sign_in()
        return
    draw_sidebar()
    pages = [st.Page(PAGE_RENDERERS[name][0], title=name, icon=PAGE_RENDERERS[name][1],
                     url_path=name.lower().replace(" ", "-")) for name in st.session_state["pages"]]
    st.navigation(pages).run()


if __name__ == "__main__":
    main()
