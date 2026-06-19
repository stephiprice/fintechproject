# Chat log, CreditPass

A record of how we used an AI coding agent (Claude Code, running Claude Opus 4.8 with the 1 million token context window) to build the MVP, and the key decisions we accepted or rejected along the way. This documents our agent orchestration, as asked in the assignment.

How we worked: we drove the agent feature by feature, reviewed every change, ran the app and the tests after each step, and committed in small chunks on a feature branch that we merged through a pull request. We accepted suggestions that improved explainability, safety, and reproducibility, and rejected ones that added complexity or hidden behaviour.

## Session 1, scaffolding the MVP (Track A)

Prompt focus: set up the repository, the shared scoring contract, the credit engine, synthetic data, and the Streamlit app.

Key decisions:

* Accepted: a rule based credit engine instead of a machine learning model. Reason: it is deterministic and fully explainable, which is the product's selling point, and it removes a heavy dependency that is hard to install and reproduce.
* Accepted: a single shared contract in decision.py (sub_score, flags, details) so the credit and KYC engines can be built in parallel without conflicts.
* Accepted: Streamlit for the UI, so the app runs with one command and demos well.
* Rejected: a database. For an MVP it adds setup with no demo value, so state is kept in memory and a CSV audit log.
* Verified: generated the three demo SMEs and confirmed they score Go, Review, and Decline.

## Session 2, documentation

Prompt focus: write the README and CLAUDE.md, and make the run instructions exactly reproducible.

Key decisions:

* Accepted: a step by step run guide with pinned dependencies and expected output, so a grader can reproduce the app without guesswork.
* Accepted: a CLAUDE.md that documents the architecture, the shared contract, and the ownership split, so the agent (and a reader) understands the boundaries.
* Accepted: a business plan mapping table that states honestly what is implemented and what is not.

## Session 3, hardening (security and robustness review)

Prompt focus: review the code as a strict grader and fix the real weaknesses.

Key decisions:

* Accepted and fixed: removed raw HTML rendering of user text, which had exposed the app to script injection through the company and UBO fields. The UI now uses native components only.
* Accepted: an input validation layer that checks and cleans uploaded files, so a bad CSV gives a clear message instead of a crash or a stack trace.
* Accepted: a capped upload size to limit denial of service from very large files.
* Accepted: a pytest suite covering the scoring outcomes, the sanctions auto decline, the contract shape, and the validation rejections.
* Accepted: an audit log of analyst decisions, in line with the business plan's four eyes and audit trail goals.
* Accepted: pinned dependency versions for reproducible installs.
* Accepted: a cash flow chart and a JSON export, to strengthen explainability and usability.
* Rejected: committing the audit log to the repository. It is runtime output, so it is gitignored.
* Deferred on purpose: PDF ingestion, live PSD2 and sanctions feeds, and authentication. These are named in the README as out of scope for the MVP.

## Notes

* Track B sessions (KYC screening and the credit memo) are added below by the second contributor.
