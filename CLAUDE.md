# CLAUDE.md. Agent instructions for CreditPass

Project specific guidance for AI coding agents (Claude Code, Codex, and similar) working in this repo. Read this before making changes.

## What this project is

CreditPass is an MVP that scores SME loan applications. It combines credit risk and KYC/CDD compliance risk into one explainable recommendation: Go, Review, or Decline. A human credit officer makes the final call. Stack: Python and Streamlit. There is no database and no ML training. Scoring is deterministic and rule based on purpose.

## Architecture

Respect these boundaries:

* app.py : the Streamlit UI. It orchestrates a request. It contains no scoring logic.
* creditpass/decision.py : the shared contract. It combines the two sub scores into a recommendation. Edit with care.
* creditpass/credit.py : the credit scoring engine (cash flow, debt, affordability). Track A.
* creditpass/kyc.py : the KYC/CDD screening engine (UBO, sanctions, country). Track B.
* creditpass/validation.py : validates and cleans uploaded transaction files before scoring.
* data/generate_synthetic.py : reproducible synthetic demo data with a fixed seed.
* tests/ : the pytest suite. Run python -m pytest before merging.

Core principle: keep the deterministic decision separate from any generated text. The score is explainable and traceable to its inputs. This is the product's selling point, and it keeps the score in the EU AI Act lower risk decision support category. Any text written by an LLM (the credit memo) must only draft text and cite sources. It must never compute or change the score.

## The shared contract (do not break)

Both credit.py and kyc.py must return a dict with exactly this shape:

```
{
    "sub_score": float,        # 0 to 100, higher means lower risk
    "flags": [ ... ],          # built only with decision.make_flag(...)
    "details": { ... },        # JSON serializable numbers for the UI
}
```

Rules:

* Build every flag with decision.make_flag(code, label, severity, detail).
* severity is one of "info", "low", "medium", or "high".
* A "high" severity flag is an automatic Decline in decision.combine(). Use it only for genuinely disqualifying findings, such as a sanctions hit or an unaffordable loan.
* If you change the contract in decision.py, update both engines and the UI in the same change.

## Track B memo interface

creditpass/memo.py must expose draft_memo(result: dict) -> str that returns a markdown credit memo. The result argument is the dict returned by decision.combine(). app.py imports this automatically when the file exists, and shows a placeholder until then, so the app always runs. The memo may only describe and cite numbers that are already in result. It must never compute or change the score.

## Ownership (this is a two person project)

* Track A (Valentine): app.py, creditpass/credit.py, creditpass/decision.py, data/generate_synthetic.py.
* Track B (Stephanie): creditpass/kyc.py, mock compliance data, creditpass/memo.py (the memo).

When working in one track, do not edit the other track's files without coordinating. Prefer a pull request comment over a silent cross track edit. decision.py is co owned. Changes to it need both tracks to agree, because it is the integration point.

## Conventions

* Python 3.10 or newer. Use the standard library plus pandas, numpy, and streamlit only. Do not add heavy ML dependencies such as xgboost or scikit-learn. Rule based and explainable is a deliberate choice.
* Keep scoring functions pure. Inputs go in, a result dict comes out. No global state and no file reads or writes.
* Comment why, not what. Match the existing comment style.
* Every point a score loses should map to a named feature and, where relevant, a flag. Never an unexplained number.
* Never commit secrets, API keys, or the .venv folder. See .gitignore.
* Validate all uploaded data through creditpass/validation.py before scoring. Never trust raw input.
* Never render user supplied text as raw HTML. Do not use unsafe_allow_html with applicant or UBO fields.
* Add or update a test in tests/ when you change scoring logic or the contract.

## How to run and verify

```
python -m pip install -r requirements.txt
python data/generate_synthetic.py
streamlit run app.py
```

Quick logic check. This should print Go, Review, and Decline for the three demo SMEs:

```
python -c "import pandas as pd; from creditpass.credit import score_credit; from creditpass.kyc import screen_kyc; from creditpass.decision import combine; [print(n, combine(score_credit(pd.read_csv(f'data/samples/{n}.csv'), {'requested_amount':50000,'country':'NL','ubo_names':['Anna de Vries']}), screen_kyc({'country':'NL','ubo_names':['Anna de Vries']}), {})['recommendation']) for n in ['healthy','marginal','risky']]"
```

## Guardrails

* Keep the human in the loop framing. The app recommends and the analyst decides. Do not add fully automated approval.
* Do not add real customer data. Demo data must stay synthetic and reproducible.
* Prefer small, reviewable commits with clear messages. This is a collaborative graded repo.
