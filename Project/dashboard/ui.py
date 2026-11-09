"""Small display helpers shared by the pages: badges, money and layout. No business rule lives here."""
import streamlit as st

from config import config

NEUTRAL = getattr(config, "NEUTRAL_BADGE_COLOUR", "gray")

STYLE = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1320px;}
h1, h2, h3 {letter-spacing: -0.01em;}
[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); border-radius: 10px; padding: 12px 14px;}
[data-testid="stMetricLabel"] p {font-size: .82rem; opacity: .8;}
.fp-caption {opacity: .72; font-size: .92rem; margin-top: -.4rem; margin-bottom: 1rem;}
.fp-card {border: 1px solid rgba(128,128,128,.25); border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;}
.fp-kv {display: grid; grid-template-columns: 220px 1fr; row-gap: 6px; column-gap: 12px; font-size: .95rem;}
.fp-kv div:nth-child(odd) {opacity: .7;}
.fp-mono {font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .88rem; white-space: pre-wrap;}
</style>
"""


def apply_style():
    st.markdown(STYLE, unsafe_allow_html=True)


def badge(label, colours=None):
    colour = (colours or {}).get(label, NEUTRAL)
    if hasattr(st, "badge"):
        st.badge(str(label), color=colour)
    else:
        st.markdown(f":{colour}-badge[{label}]")


def badge_text(label, colours=None):
    colour = (colours or {}).get(label, NEUTRAL)
    return f":{colour}-badge[{label}]"


def badges(*pairs):
    st.markdown(" ".join(badge_text(label, colours) for label, colours in pairs if label is not None))


def aud(value):
    return "—" if value is None else f"AUD {value}"


def caption(text):
    st.markdown(f'<div class="fp-caption">{text}</div>', unsafe_allow_html=True)


def key_values(pairs):
    cells = "".join(f"<div>{key}</div><div>{'—' if value is None else value}</div>" for key, value in pairs)
    st.markdown(f'<div class="fp-kv">{cells}</div>', unsafe_allow_html=True)


def labelled_text(text):
    """A stored document written as LABEL: text blocks, shown with its labels in bold."""
    if not text:
        st.caption("Not written.")
        return
    for block in text.split("\n\n"):
        label, _, body = block.partition(": ")
        st.markdown(f"**{label}**")
        st.markdown(body.replace("\n", "  \n"))
