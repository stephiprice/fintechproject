"""Tests for the CreditPass scoring pipeline.

Run from the project root:
    python -m pytest

The session fixture regenerates the demo CSVs so the tests are self-contained.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pandas as pd
import pytest

from creditpass.credit import score_credit
from creditpass.decision import combine
from creditpass.kyc import screen_kyc
from creditpass.validation import validate_transactions

ROOT = os.path.dirname(os.path.dirname(__file__))
BASE_APPLICANT = {
    "company": "Test BV",
    "sector": "Food",
    "country": "NL",
    "requested_amount": 50_000,
    "ubo_names": ["Anna de Vries"],
}


@pytest.fixture(scope="session", autouse=True)
def _demo_data():
    """Generate the demo CSVs once before the tests run."""
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "data", "generate_synthetic.py")],
        check=True,
        cwd=ROOT,
    )


def _assess(name: str, applicant: dict) -> dict:
    tx = pd.read_csv(os.path.join(ROOT, "data", "samples", f"{name}.csv"))
    tx = validate_transactions(tx)
    return combine(score_credit(tx, applicant), screen_kyc(applicant), applicant)


def test_healthy_is_go():
    assert _assess("healthy", BASE_APPLICANT)["recommendation"] == "Go"


def test_marginal_is_review():
    assert _assess("marginal", BASE_APPLICANT)["recommendation"] == "Review"


def test_risky_is_decline():
    assert _assess("risky", BASE_APPLICANT)["recommendation"] == "Decline"


def test_sanctions_hit_forces_decline():
    """A sanctioned UBO must Decline even on an otherwise healthy applicant."""
    flagged = {**BASE_APPLICANT, "ubo_names": ["John Doe"]}
    assert _assess("healthy", flagged)["recommendation"] == "Decline"


def test_contract_shape():
    tx = validate_transactions(
        pd.read_csv(os.path.join(ROOT, "data", "samples", "healthy.csv"))
    )
    result = score_credit(tx, BASE_APPLICANT)
    assert {"sub_score", "flags", "details"} <= set(result)
    assert 0.0 <= result["sub_score"] <= 100.0


def test_validation_rejects_missing_column():
    with pytest.raises(ValueError):
        validate_transactions(pd.DataFrame({"date": ["2025-09-01"], "amount": [100]}))


def test_validation_rejects_empty():
    empty = pd.DataFrame(columns=["date", "description", "amount", "balance"])
    with pytest.raises(ValueError):
        validate_transactions(empty)


def test_validation_rejects_bad_amount():
    bad = pd.DataFrame(
        {
            "date": ["2025-09-01"],
            "description": ["x"],
            "amount": ["not a number"],
            "balance": [100],
        }
    )
    with pytest.raises(ValueError):
        validate_transactions(bad)
