"""KYC / compliance screening engine.

>>> TRACK B (Stephanie) OWNS THIS FILE <<<

This is a minimal PLACEHOLDER so the app runs end-to-end while Track A is
built. Replace it with the full implementation: real mock sanctions / PEP /
adverse-media lists (e.g. data/sanctions_mock.json), UBO completeness, and
high-risk sector & country checks.

IMPORTANT: keep the return shape identical to the contract in decision.py
(``sub_score``, ``flags``, ``details``) so the two tracks stay compatible.
"""

from __future__ import annotations

from typing import Any, Dict, List

from creditpass.decision import make_flag

# Tiny inline mock lists -- Track B replaces these with proper data files.
_MOCK_SANCTIONS = {"john doe", "ivan petrov", "acme shell ltd"}
_HIGH_RISK_COUNTRIES = {"IR", "KP", "RU", "SY"}


def screen_kyc(applicant: Dict[str, Any]) -> Dict[str, Any]:
    """Return a KYC sub-result following the shared decision contract."""
    flags: List[Dict[str, str]] = []
    score = 100.0

    ubos = [u.strip().lower() for u in applicant.get("ubo_names", []) if u.strip()]

    for name in ubos:
        if name in _MOCK_SANCTIONS:
            flags.append(make_flag(
                "SANCTIONS_HIT", "Sanctions / watchlist match", "high",
                f"UBO '{name.title()}' matches the mock sanctions list.",
            ))
            score -= 60

    if not ubos:
        flags.append(make_flag(
            "UBO_MISSING", "UBO information missing", "medium",
            "No ultimate beneficial owner was provided.",
        ))
        score -= 20

    country = str(applicant.get("country", "")).upper()
    if country in _HIGH_RISK_COUNTRIES:
        flags.append(make_flag(
            "HIGH_RISK_COUNTRY", "High-risk country", "medium",
            f"Registered in a high-risk jurisdiction ({country}).",
        ))
        score -= 20

    score = round(max(min(score, 100.0), 0.0), 1)
    return {"sub_score": score, "flags": flags, "details": {"ubo_count": len(ubos)}}
