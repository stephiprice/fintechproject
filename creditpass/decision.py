"""Shared scoring contract for CreditPass.

This is the ONE file both tracks depend on. The credit engine (Track A,
``credit.py``) and the KYC engine (Track B, ``kyc.py``) each return a result
dict in the shape documented below. ``combine()`` fuses them into a single
loan-readiness score and a Go / Review / Decline recommendation.

Result contract
---------------
Each engine returns:
    {
        "sub_score": float,        # 0-100, higher = lower risk
        "flags": [Flag, ...],      # see make_flag()
        "details": {str: Any},     # engine-specific numbers, shown in the UI
    }

A Flag is:
    {
        "code": str,        # machine id, e.g. "NEG_BALANCE_DAYS"
        "label": str,       # short human label
        "severity": str,    # "info" | "low" | "medium" | "high"
        "detail": str,      # one-line explanation including the number
    }
"""

from __future__ import annotations

from typing import Any, Dict, List

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3}

# Weights for fusing the two sub-scores into the overall score.
CREDIT_WEIGHT = 0.6
KYC_WEIGHT = 0.4

# Score thresholds for the recommendation.
GO_THRESHOLD = 70
REVIEW_THRESHOLD = 45


def make_flag(code: str, label: str, severity: str, detail: str) -> Dict[str, str]:
    """Build a single risk flag in the shared format."""
    if severity not in SEVERITY_ORDER:
        raise ValueError(f"Unknown severity: {severity!r}")
    return {"code": code, "label": label, "severity": severity, "detail": detail}


def empty_result(sub_score: float = 100.0) -> Dict[str, Any]:
    """A neutral result (used by stubs or when an engine has nothing to flag)."""
    return {"sub_score": sub_score, "flags": [], "details": {}}


def combine(
    credit: Dict[str, Any],
    kyc: Dict[str, Any],
    applicant: Dict[str, Any],
) -> Dict[str, Any]:
    """Fuse the credit and KYC results into one decision.

    Decision logic, in plain English:
      * Any HIGH-severity flag (e.g. a sanctions hit or an unaffordable loan)
        is an automatic Decline, regardless of the numeric score.
      * Otherwise, a score at/above GO_THRESHOLD with no medium flags -> Go.
      * A score at/above REVIEW_THRESHOLD -> Review.
      * Below that -> Decline.
    """
    credit_score = float(credit.get("sub_score", 0))
    kyc_score = float(kyc.get("sub_score", 0))
    overall = round(CREDIT_WEIGHT * credit_score + KYC_WEIGHT * kyc_score, 1)

    all_flags: List[Dict[str, str]] = list(credit.get("flags", [])) + list(kyc.get("flags", []))
    has_high = any(f["severity"] == "high" for f in all_flags)
    has_medium = any(f["severity"] == "medium" for f in all_flags)

    if has_high:
        recommendation = "Decline"
    elif overall >= GO_THRESHOLD and not has_medium:
        recommendation = "Go"
    elif overall >= REVIEW_THRESHOLD:
        recommendation = "Review"
    else:
        recommendation = "Decline"

    # Drivers = the flags that most influenced the decision, worst first.
    drivers = sorted(
        all_flags, key=lambda f: SEVERITY_ORDER[f["severity"]], reverse=True
    )

    return {
        "applicant": applicant,
        "overall_score": overall,
        "recommendation": recommendation,
        "credit": credit,
        "kyc": kyc,
        "flags": all_flags,
        "drivers": drivers,
    }
