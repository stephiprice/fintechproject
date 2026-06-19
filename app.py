"""CreditPass -- SME loan-readiness copilot (MVP).

Streamlit app: an analyst uploads an SME's bank transactions and applicant
details, gets an explainable credit + KYC score with a Go / Review / Decline
recommendation, can record a decision (written to an audit log), and can
download the assessment.

Run:
    streamlit run app.py
"""

from __future__ import annotations

import glob
import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from creditpass.credit import score_credit
from creditpass.decision import combine
from creditpass.kyc import screen_kyc
from creditpass.validation import validate_transactions

SAMPLES_DIR = os.path.join("data", "samples")
AUDIT_LOG = "audit_log.csv"
SEV_EMOJI = {"high": "🔴", "medium": "🟠", "low": "🔵", "info": "⚪"}

SAMPLE_TEMPLATE = (
    "date,description,amount,balance\n"
    "2025-09-01,Customer deposit,1400.00,16400.00\n"
    "2025-09-01,Rent payment,-2500.00,13900.00\n"
    "2025-09-25,Payroll,-7000.00,6900.00\n"
)

st.set_page_config(page_title="CreditPass", page_icon="✅", layout="wide")


def load_samples() -> dict:
    """Map sample name -> csv path for any pre-generated demo files."""
    return {
        os.path.splitext(os.path.basename(p))[0]: p
        for p in sorted(glob.glob(os.path.join(SAMPLES_DIR, "*.csv")))
    }


def append_audit(result: dict, decision: str) -> None:
    """Append the analyst's decision to a local audit log (created if absent)."""
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "company": result["applicant"].get("company", ""),
        "country": result["applicant"].get("country", ""),
        "requested_amount": result["applicant"].get("requested_amount", ""),
        "recommendation": result["recommendation"],
        "overall_score": result["overall_score"],
        "analyst_decision": decision,
    }
    pd.DataFrame([row]).to_csv(
        AUDIT_LOG, mode="a", header=not os.path.exists(AUDIT_LOG), index=False
    )


# ---- Sidebar: applicant inputs -----------------------------------------
st.sidebar.title("CreditPass")
st.sidebar.caption("SME loan-readiness copilot")

samples = load_samples()
sample_choice = st.sidebar.selectbox(
    "Demo bank data", ["(upload my own)"] + list(samples.keys())
)
uploaded = st.sidebar.file_uploader("Bank transactions (CSV)", type="csv")
st.sidebar.download_button(
    "Download CSV template", SAMPLE_TEMPLATE, "creditpass_template.csv", "text/csv"
)

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
    # 1) Read + validate the file. Never let a raw stack trace reach the user.
    try:
        raw = get_transactions()
        if raw is None:
            st.warning("Upload a transactions CSV or pick a demo dataset in the sidebar.")
            st.stop()
        tx = validate_transactions(raw)
    except ValueError as exc:
        st.error(f"Could not read the transactions file: {exc}")
        st.stop()
    except Exception as exc:  # noqa: BLE001 - friendly message, never a stack trace
        st.error(f"Unexpected problem reading the file: {exc}")
        st.stop()

    applicant = {
        "company": company.strip(),
        "sector": sector.strip(),
        "country": country.strip(),
        "requested_amount": requested,
        "ubo_names": [n.strip() for n in ubo_raw.splitlines() if n.strip()],
    }

    # 2) Score. Guard so a data edge case shows a message, not a crash.
    try:
        credit = score_credit(tx, applicant)
        kyc = screen_kyc(applicant)
        st.session_state["result"] = combine(credit, kyc, applicant)
        st.session_state["tx"] = tx
        st.session_state.pop("decision", None)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Assessment failed: {exc}")
        st.stop()

result = st.session_state.get("result")
if not result:
    st.info("Fill in the applicant details on the left and click Assess application.")
    st.stop()

# ---- Headline (native colour, no raw HTML => no injection risk) ---------
rec = result["recommendation"]
a = result["applicant"]
{"Go": st.success, "Review": st.warning, "Decline": st.error}[rec](
    f"Recommendation: {rec}"
)

c1, c2, c3 = st.columns(3)
c1.metric("Overall score", result["overall_score"])
c2.metric("Credit sub-score", result["credit"]["sub_score"])
c3.metric("KYC sub-score", result["kyc"]["sub_score"])
st.caption(
    f"{a['company']} | {a['sector']} | {a['country']} | "
    f"EUR {a['requested_amount']:,} requested"
)

# ---- Drivers / flags (plain markdown, user input is NOT rendered as HTML)
st.subheader("Key risk flags")
if result["drivers"]:
    for f in result["drivers"]:
        emoji = SEV_EMOJI.get(f["severity"], "⚪")
        st.markdown(f"{emoji} **{f['label']}** ({f['severity']}): {f['detail']}")
else:
    st.success("No risk flags raised.")

# ---- Cash-flow chart (explainability) ----------------------------------
tx = st.session_state.get("tx")
if tx is not None and not tx.empty:
    st.subheader("Account balance over time")
    st.line_chart(tx[["date", "balance"]].set_index("date"))

# ---- Details -----------------------------------------------------------
col_a, col_b = st.columns(2)
with col_a:
    with st.expander("Credit details"):
        st.json(result["credit"]["details"])
with col_b:
    with st.expander("KYC details"):
        st.json(result["kyc"]["details"])

# ---- Analyst decision (human in the loop) + audit log ------------------
st.subheader("Analyst decision")
st.caption("CreditPass recommends; the credit officer decides. Each decision is logged.")
d1, d2, d3 = st.columns(3)
if d1.button("Approve (Go)", use_container_width=True):
    st.session_state["decision"] = "Go"
    append_audit(result, "Go")
if d2.button("Send to review", use_container_width=True):
    st.session_state["decision"] = "Review"
    append_audit(result, "Review")
if d3.button("Decline", use_container_width=True):
    st.session_state["decision"] = "Decline"
    append_audit(result, "Decline")
if "decision" in st.session_state:
    st.success(
        f"Analyst decision recorded: {st.session_state['decision']} "
        f"(saved to {AUDIT_LOG})"
    )

# ---- Export the assessment ---------------------------------------------
st.download_button(
    "Download assessment (JSON)",
    json.dumps(result, indent=2, default=str),
    file_name="creditpass_assessment.json",
    mime="application/json",
)

# ---- Draft credit memo (Track B, soft import) --------------------------
st.subheader("Draft credit memo")
try:
    from creditpass.memo import draft_memo

    st.markdown(draft_memo(result))
except ModuleNotFoundError:
    st.info("The AI drafted memo will appear here (Track B, creditpass/memo.py).")
