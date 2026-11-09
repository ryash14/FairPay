"""Every request the dashboard sends to the service passes through here."""
import httpx
import streamlit as st

from config import config


def call_service(method, path, query, payload, waiting_message):
    """One call to the service with the signed-in person's token; an error reply stops the page."""
    headers = {}
    token = st.session_state.get("session_token")
    if token:
        headers[config.SESSION_TOKEN_HEADER] = token

    def send():
        return httpx.request(method, config.API_BASE_URL + path, params=query, json=payload, headers=headers,
                             timeout=config.API_REQUEST_TIMEOUT_SECONDS)

    if waiting_message:
        try:
            with st.spinner(waiting_message, show_time=True):
                response = send()
        except TypeError:
            with st.spinner(waiting_message):
                response = send()
    else:
        response = send()

    if response.status_code >= 400:
        if response.headers.get("content-type", "").startswith("application/json"):
            detail = response.json().get("detail", response.text)
            if isinstance(detail, list):
                detail = "; ".join(str(item.get("msg", item)) for item in detail)
            st.error(detail)
        else:
            st.error(f"The service answered {response.status_code}: {response.text}")
        st.stop()
    return response.json()
