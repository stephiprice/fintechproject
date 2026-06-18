"""CreditPass -- SME loan-readiness copilot (MVP).

Streamlit app: an analyst uploads an SME's bank transactions and applicant
details, gets an explainable credit + KYC score with a Go / Review / Decline
recommendation, and records a decision (human in the loop).

Run:
    streamlit run app.py
"""

from __future__ import annotations

import glob
import os

import pandas as pd
import streamlit as st

from creditpass.credit import score_credit
from creditpass.decision import combine
from creditpass.kyc import screen_kyc

SAMPLES_DIR = os.path.join("data", "samples")
REC_COLORS = {"Go": "#1a7f37", "Review": "#9a6700", "Decline": "#cf222e"}
SEV_COLORS = {"high": "#cf222e", "medium": "#9a6700", "low": "#0969da", "info": "#57606a"}

st.set_page_config(page_title="CreditPass", page_icon="✅", layout="wide")


def load_samples() -> dict:
    """Map sample name -> csv path for any pre-generated demo files."""
    return {
        os.path.splitext(os.path.basename(p))[0]: p
        for p in sorted(glob.glob(os.path.join(SAMPLES_DIR, "*.csv")))
    }


def severity_badge(sev: str) -> str:
    color = SEV_COLORS.get(sev, "#57606a")
    return f"<span style='color:{color};font-weight:600'>{sev.upper()}</span>"


# ---- Sidebar: applicant inputs -----------------------------------------
st.sidebar.title("CreditPass")
st.sidebar.caption("SME loan-readiness copilot")

samples = load_samples()
sample_choice = st.sidebar.selectbox(
    "Demo bank data", ["(upload my own)"] + list(samples.keys())
)
uploaded = st.sidebar.file_uploader("Bank transactions (CSV)", type="csv")

st.sidebar.markdown("**Applicant**")
company = st.sidebar.text_input("Company name", "Bakery De Korenbloem BV")
sector = st.sidebar.text_input("Sector", "Food retail")
country = st.sidebar.text_input("Country (ISO code)", "NL")
requested = st.sidebar.number_input(
    "Requested amount (EUR)", min_value=0, max_value=1_000_000, value=50_000, step=5_000
)
ubo_raw = st.sidebar.text_area("UBO names (one per line)", "Anna de Vries")
assess = st.sidebar.button("Assess application", type="primary", use_container_width=True)


def get_transactions():
    """Read transactions from an upload or a selected sample file."""
    if uploaded is not None:
        return pd.read_csv(uploaded)
    if sample_choice in samples:
        return pd.read_csv(samples[sample_choice])
    return None


# ---- Run assessment ----------------------------------------------------
st.title("Loan-readiness assessment")

if assess:
    tx = get_transactions()
    if tx is None:
        st.warning("Upload a transactions CSV or pick a demo dataset in the sidebar.")
        st.stop()

    applicant = {
        "company": company,
        "sector": sector,
        "country": country,
        "requested_amount": requested,
        "ubo_names": [n for n in ubo_raw.splitlines() if n.strip()],
    }

    credit = score_credit(tx, applicant)
    kyc = screen_kyc(applicant)
    st.session_state["result"] = combine(credit, kyc, applicant)
    st.session_state.pop("decision", None)  # reset prior analyst decision

result = st.session_state.get("result")
if not result:
    st.info("Fill in the applicant details on the left and click **Assess application**.")
    st.stop()

# ---- Headline ----------------------------------------------------------
rec = result["recommendation"]
c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
c1.markdown(
    f"### Recommendation: <span style='color:{REC_COLORS[rec]}'>{rec}</span>",
    unsafe_allow_html=True,
)
c2.metric("Overall score", result["overall_score"])
c3.metric("Credit sub-score", result["credit"]["sub_score"])
c4.metric("KYC sub-score", result["kyc"]["sub_score"])

a = result["applicant"]
st.caption(
    f"{a['company']} · {a['sector']} · {a['country']} · "
    f"€{a['requested_amount']:,} requested"
)

# ---- Drivers / flags ---------------------------------------------------
st.subheader("Key risk flags")
if result["drivers"]:
    for f in result["drivers"]:
        st.markdown(
            f"- {severity_badge(f['severity'])} **{f['label']}** — {f['detail']}",
            unsafe_allow_html=True,
        )
else:
    st.success("No risk flags raised.")

# ---- Details (explainability) ------------------------------------------
col_a, col_b = st.columns(2)
with col_a:
    with st.expander("Credit details"):
        st.json(result["credit"]["details"])
with col_b:
    with st.expander("KYC details"):
        st.json(result["kyc"]["details"])

# ---- Analyst decision (human in the loop) ------------------------------
st.subheader("Analyst decision")
st.caption("CreditPass recommends; the credit officer decides.")
d1, d2, d3 = st.columns(3)
if d1.button("✅ Approve (Go)", use_container_width=True):
    st.session_state["decision"] = "Go"
if d2.button("🔍 Send to review", use_container_width=True):
    st.session_state["decision"] = "Review"
if d3.button("❌ Decline", use_container_width=True):
    st.session_state["decision"] = "Decline"
if "decision" in st.session_state:
    st.success(f"Analyst decision recorded: **{st.session_state['decision']}**")

# ---- Memo placeholder (Track B) ----------------------------------------
st.subheader("Draft credit memo")
st.info("The AI-drafted memo will appear here (Track B · creditpass/memo.py).")
