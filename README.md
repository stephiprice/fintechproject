# CreditPass

**An explainable SME loan readiness copilot for community and cooperative banks.**

CreditPass takes an SME's bank transaction history and applicant details and returns a single loan readiness score. The score combines credit risk and KYC/CDD compliance risk. It gives a clear Go, Review, or Decline recommendation and lists the exact risk flags behind it. The credit officer stays in the loop and makes the final decision. CreditPass simply gets them there in minutes instead of hours.

This is the MVP for Assignment 2 of FinTech: Business Models and Application (RSM). It implements the key features of the CreditPass business plan from Assignment 1.

## Key features

* **Upload bank data:** the analyst uploads a transactions CSV, or picks a built in demo SME.
* **Credit scoring:** transparent, rule based scoring of cash flow stability, negative balance days, existing debt burden, and affordability of the requested loan. It is deterministic and fully explainable, so there is no black box.
* **KYC/CDD screening:** UBO completeness, sanctions and PEP matching, and high risk country checks.
* **Fused decision:** a single score from 0 to 100 and a Go, Review, or Decline recommendation.
* **Explainability:** every recommendation lists the exact flags and the numbers behind them.
* **Human in the loop:** the analyst records the final decision. CreditPass only advises.
* **Cash flow chart:** the account balance is plotted over time, so the analyst sees the story behind the score.
* **Validated input:** uploaded files are checked and cleaned before scoring, with clear error messages instead of crashes.
* **Audit log:** every analyst decision is written to a local audit log with a timestamp.
* **Export:** the full assessment can be downloaded as a JSON file.

## How it works

The flow has four steps:

1. The analyst provides a bank transactions CSV and a short applicant form.
2. credit.py produces a credit sub score, and kyc.py produces a KYC sub score.
3. decision.py combines the two sub scores into one overall score and a Go, Review, or Decline recommendation. Any high severity flag forces a Decline.
4. app.py shows the result and lets the analyst record the final decision.

The score is deterministic and traceable to its inputs. This keeps the high stakes part out of the EU AI Act high risk decisioning category. The AI drafted credit memo (Track B) only drafts text and cites its sources. It never changes the score.

## How to run

You need Python 3.10 or newer and Git installed. Follow these steps exactly. Run one line at a time and wait for each to finish.

**Step 1. Get the code.**

```
git clone https://github.com/stephiprice/fintechproject.git
cd fintechproject
```

**Step 2. Create a virtual environment.**

```
python -m venv .venv
```

**Step 3. Activate the virtual environment.**

On Windows (PowerShell):

```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```
source .venv/bin/activate
```

Your prompt now starts with `(.venv)`.

**Step 4. Install the dependencies.**

```
python -m pip install -r requirements.txt
```

**Step 5. Generate the demo data.**

```
python data/generate_synthetic.py
```

Expected output: three lines confirming that healthy.csv, marginal.csv, and risky.csv were written.

**Step 6. Run the app.**

```
streamlit run app.py
```

Your browser opens at http://localhost:8501. If it asks for an email, press Enter to skip.

**Step 7. Use it.**

In the sidebar, choose a demo dataset (healthy, marginal, or risky), then click Assess application. To stop the app, press Ctrl plus C in the terminal.

## Run the tests

The test suite checks the scoring logic and the input validation.

```
python -m pip install -r requirements-dev.txt
python -m pytest
```

You should see all tests pass.

## Repository structure

* app.py : the Streamlit UI. Upload, assess, decide.
* creditpass/decision.py : the shared contract. Combines credit and KYC into a decision.
* creditpass/credit.py : the credit scoring engine (Track A).
* creditpass/kyc.py : the KYC/CDD screening engine (Track B).
* creditpass/validation.py : checks and cleans uploaded transaction files.
* data/generate_synthetic.py : builds three demo SME profiles.
* data/samples/ : the generated demo CSV files.
* tests/ : the pytest test suite.
* .streamlit/config.toml : app settings, including the upload size limit.
* requirements.txt : the Python dependencies to run the app.
* requirements-dev.txt : extra dependencies to run the tests.
* CLAUDE.md : instructions for AI coding agents.
* prompt.md : the original build specification given to the agent.
* chat_log.md : a record of the AI sessions and the decisions we accepted or rejected.
* README.md : this file.

## Mapping to the business plan

Implemented in this MVP:

* Combined credit and KYC score.
* Go, Review, or Decline recommendation.
* Explainable risk flags.
* Human in the loop decision.

In progress (Track B):

* AI drafted credit memo with citations.

Not in this MVP, planned for later:

* Live PSD2 ingestion. The MVP uses CSV upload instead.
* Real sanctions and PEP data feeds. These are mocked for the demo.
* Continuous monitoring after the loan is approved.

## Demo data

The demo SME profiles are synthetic. They are generated by data/generate_synthetic.py with a fixed random seed, so they are fully reproducible. No real customer data is used. The three profiles show each outcome: a healthy SME (Go), a stretched but viable SME (Review), and a distressed SME (Decline).

## Security and robustness

* Uploaded files are validated and cleaned in creditpass/validation.py before any scoring. Bad files produce a clear message, never a crash or a stack trace.
* User text (company name, UBO names) is never rendered as raw HTML, so the app is not exposed to script injection through the inputs.
* The upload size is capped in .streamlit/config.toml to limit denial of service from very large files.
* Dependencies are pinned to exact versions for reproducible installs.
* Analyst decisions are recorded in a local audit log, in line with the four eyes and audit trail goals of the business plan.

## Team and collaboration

Two contributors built this, working in parallel on separate branches and integrating through pull requests.

* Valentine Lusson, Track A: credit scoring engine, shared decision contract, synthetic data, Streamlit dashboard.
* Stephanie Price, Track B: KYC/CDD screening engine, mock compliance data, AI drafted credit memo.

The single integration point is creditpass/decision.py. Both engines build against it, so the two tracks develop independently without conflicts.

## Development setup and AI tooling

The code is Python with the Streamlit framework. We built it with Claude Code, the agentic command line tool from Anthropic, running Claude Opus 4.8 with the 1 million token context window.

Why this agent: Claude Code edits files, runs the app and the tests, and fixes errors on its own inside the project folder, so it works from the whole codebase rather than a single snippet. The large context window let it hold the full repository, the business plan, and the assignment brief in mind at once.

How we orchestrate it: a CLAUDE.md file in the repository root gives the agent persistent project rules (the architecture, the shared contract, and the ownership split between the two tracks). We worked one feature at a time, reviewed every change, ran the tests after each step, and committed in small chunks. The suggestions we accepted and rejected are recorded in chat_log.md.

The authors reviewed and accepted all design decisions, the scoring logic, and the final code.

## License

MIT License. See the LICENSE file.

Copyright 2026 Valentine Lusson and Stephanie Price.
