# Build prompt

This is the specification given to the coding agent (Claude Code) at the start of the project. It is kept here for transparency about how the MVP was built.

## Goal

Build the MVP for CreditPass, the SME loan readiness copilot from our business plan. An analyst uploads an SME's bank transactions and applicant details and gets one explainable score that combines credit risk and KYC/CDD compliance risk, a Go, Review, or Decline recommendation, and the risk flags behind it. The analyst makes the final decision.

## Tech and constraints

* Python and Streamlit. No database.
* The scoring must be deterministic and rule based, not a black box. Explainability is the product's selling point and keeps the score in the EU AI Act lower risk decision support category.
* No heavy machine learning dependencies. Standard library plus pandas, numpy, and streamlit only.
* The app must run with a single command and a short setup, with pinned dependencies for reproducibility.
* Use synthetic, reproducible demo data. No real customer data.
* Keep a human in the loop. The app recommends, the analyst decides.

## Features to implement

1. Upload a transactions CSV, or pick a built in demo SME.
2. Credit scoring from cash flow stability, negative balance days, debt burden, and affordability of the requested loan.
3. KYC/CDD screening: UBO completeness, sanctions and PEP matching, high risk country.
4. Fuse the two into a single 0 to 100 score and a Go, Review, or Decline recommendation, with a high severity flag forcing a Decline.
5. Show the risk flags and the numbers behind them, plus a cash flow chart.
6. Let the analyst record a decision, written to an audit log, and download the assessment.

## Collaboration structure

Two contributors working in parallel against one shared contract (creditpass/decision.py):

* Track A: credit scoring engine, shared contract, synthetic data, Streamlit app.
* Track B: KYC/CDD screening engine and the AI drafted credit memo.
