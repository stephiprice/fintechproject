"""Tests for Track B: KYC screening and the credit memo.

Includes a "destruction" section that throws malformed and hostile inputs at
the screening engine to prove it never crashes and always returns a valid
result in the shared contract shape.

Run from the project root:
    python -m pytest
"""

from __future__ import annotations

import pytest

from creditpass.kyc import screen_kyc
from creditpass.memo import draft_memo

BASE = {
    "company": "Bakery BV",
    "sector": "Food retail",
    "country": "NL",
    "requested_amount": 50_000,
    "ubo_names": ["Anna de Vries"],
}


def _assert_contract(result):
    assert isinstance(result, dict)
    assert {"sub_score", "flags", "details"} <= set(result)
    assert 0.0 <= result["sub_score"] <= 100.0
    assert isinstance(result["flags"], list)
    for flag in result["flags"]:
        assert {"code", "label", "severity", "detail"} <= set(flag)
        assert flag["severity"] in {"info", "low", "medium", "high"}


# --- Functional screening -----------------------------------------------

def test_clean_applicant_passes():
    result = screen_kyc(BASE)
    _assert_contract(result)
    assert result["sub_score"] == 100.0
    assert result["flags"] == []


def test_sanctioned_ubo_is_high_severity():
    result = screen_kyc({**BASE, "ubo_names": ["John Doe"]})
    _assert_contract(result)
    assert any(f["code"] == "SANCTIONS_HIT" and f["severity"] == "high" for f in result["flags"])


def test_sanctioned_company_is_flagged():
    result = screen_kyc({**BASE, "company": "Acme Shell Ltd"})
    assert any(f["code"] == "SANCTIONS_HIT" for f in result["flags"])


def test_pep_match_is_medium():
    result = screen_kyc({**BASE, "ubo_names": ["Maria Santos"]})
    assert any(f["code"] == "PEP_MATCH" and f["severity"] == "medium" for f in result["flags"])


def test_prohibited_country_is_high():
    result = screen_kyc({**BASE, "country": "KP"})
    assert any(f["code"] == "PROHIBITED_COUNTRY" and f["severity"] == "high" for f in result["flags"])


def test_high_risk_country_is_medium():
    result = screen_kyc({**BASE, "country": "RU"})
    assert any(f["code"] == "HIGH_RISK_COUNTRY" and f["severity"] == "medium" for f in result["flags"])


def test_high_risk_sector_flagged():
    result = screen_kyc({**BASE, "sector": "Crypto exchange"})
    assert any(f["code"] == "HIGH_RISK_SECTOR" for f in result["flags"])


def test_missing_ubo_flagged():
    result = screen_kyc({**BASE, "ubo_names": []})
    assert any(f["code"] == "UBO_MISSING" for f in result["flags"])


def test_name_matching_is_case_and_punctuation_insensitive():
    result = screen_kyc({**BASE, "ubo_names": ["  JOHN   DOE. "]})
    assert any(f["code"] == "SANCTIONS_HIT" for f in result["flags"])


# --- Destruction: hostile and malformed inputs --------------------------

@pytest.mark.parametrize("applicant", [
    {},                                             # empty
    {"ubo_names": None},                            # None where a list is expected
    {"ubo_names": "Anna de Vries"},                 # a string, not a list
    {"ubo_names": [None, "", "  ", 12345]},          # junk entries
    {"ubo_names": ["<script>alert(1)</script>"]},    # injection attempt
    {"country": None, "sector": None, "company": None},  # all None
    {"requested_amount": "fifty thousand"},          # wrong type
    {"sector": "Dairy farms"},                       # must NOT match "arms"
    {"ubo_names": ["x" * 5000]},                      # very long name
])
def test_screen_never_crashes(applicant):
    result = screen_kyc(applicant)
    _assert_contract(result)


def test_farms_does_not_match_arms():
    """Whole-word matching: a farm is not an arms dealer."""
    result = screen_kyc({**BASE, "sector": "Dairy farms"})
    assert not any(f["code"] == "HIGH_RISK_SECTOR" for f in result["flags"])


def test_non_dict_input_does_not_crash():
    _assert_contract(screen_kyc(None))


# --- Memo -----------------------------------------------------------------

def _full_result():
    kyc = screen_kyc(BASE)
    credit = {"sub_score": 88.0, "details": {
        "avg_monthly_revenue": 18000, "monthly_surplus": 4200,
        "estimated_payment": 1389, "affordability_ratio": 0.33,
        "negative_balance_days": 0, "debt_to_revenue": 0.04,
    }, "flags": []}
    return {
        "applicant": BASE, "overall_score": 92.8, "recommendation": "Go",
        "credit": credit, "kyc": kyc,
        "flags": [], "drivers": [],
    }


def test_memo_is_nonempty_markdown():
    memo = draft_memo(_full_result())
    assert isinstance(memo, str) and len(memo) > 100
    assert "Credit memo" in memo
    assert "Recommendation: Go" in memo


def test_memo_handles_empty_result():
    memo = draft_memo({})
    assert isinstance(memo, str) and len(memo) > 0


def test_memo_handles_none():
    memo = draft_memo(None)
    assert isinstance(memo, str) and len(memo) > 0
