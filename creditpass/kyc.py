"""KYC / CDD screening engine (Track B).

Screens an applicant against mock sanctions, PEP, and adverse-media lists, and
checks UBO completeness, country risk, and sector risk. It returns a result in
the shared contract shape from decision.py (sub_score, flags, details), so it
plugs straight into combine() alongside the credit engine.

The screening data lives in data/sanctions_mock.json. It is synthetic; no real
sanctions or PEP data is used. If the file is missing or unreadable the engine
falls back to a small built-in list, so screening never silently passes.

Design notes for robustness:
  * Inputs are untrusted. Every field is read defensively (missing keys, wrong
    types, None values, and stray whitespace are all handled).
  * Names are normalised (lowercased, punctuation stripped, whitespace
    collapsed) before matching, so "John  Doe" and "john doe." both match.
  * Sector keywords match on whole words, so "farms" never matches "arms".
  * A high-severity flag (sanctions hit or prohibited country) drives an
    automatic Decline in decision.combine().
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from creditpass.decision import make_flag

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sanctions_mock.json")

# Used only if the data file is missing or invalid, so screening still runs.
_FALLBACK = {
    "sanctions": ["John Doe", "Ivan Petrov", "Acme Shell Ltd"],
    "pep": [],
    "adverse_media": [],
    "prohibited_countries": ["KP", "IR", "SY"],
    "high_risk_countries": ["RU"],
    "high_risk_sectors": ["crypto", "gambling", "arms"],
}


def _normalize(text: Any) -> str:
    """Lowercase, strip punctuation, and collapse whitespace for matching."""
    text = re.sub(r"[^a-z0-9 ]", " ", str(text).lower())
    return re.sub(r"\s+", " ", text).strip()


def _load_lists() -> Dict[str, Any]:
    """Load and pre-process the screening lists, with a safe fallback."""
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        data = _FALLBACK

    return {
        "sanctions": {_normalize(n) for n in data.get("sanctions", []) if str(n).strip()},
        "pep": {_normalize(n) for n in data.get("pep", []) if str(n).strip()},
        "adverse_media": {_normalize(n) for n in data.get("adverse_media", []) if str(n).strip()},
        "prohibited_countries": {str(c).upper().strip() for c in data.get("prohibited_countries", [])},
        "high_risk_countries": {str(c).upper().strip() for c in data.get("high_risk_countries", [])},
        "high_risk_sectors": [str(s).lower().strip() for s in data.get("high_risk_sectors", []) if str(s).strip()],
    }


def _collect_names(applicant: Dict[str, Any]) -> List[tuple]:
    """Return (kind, name) pairs to screen: the UBOs and the company itself."""
    raw = applicant.get("ubo_names") or []
    if isinstance(raw, str):  # tolerate a single string instead of a list
        raw = [raw]
    try:
        ubos = [str(u).strip() for u in raw if str(u).strip()]
    except TypeError:  # not iterable
        ubos = []

    pairs = [("UBO", u) for u in ubos]
    company = str(applicant.get("company", "")).strip()
    if company:
        pairs.append(("Company", company))
    return ubos, pairs


def screen_kyc(applicant: Dict[str, Any]) -> Dict[str, Any]:
    """Return a KYC sub-result following the shared decision contract."""
    if not isinstance(applicant, dict):
        applicant = {}

    lists = _load_lists()
    flags: List[Dict[str, str]] = []
    score = 100.0

    ubos, names_to_check = _collect_names(applicant)
    matched = {"sanctions": [], "pep": [], "adverse_media": []}

    # --- Name screening (sanctions / PEP / adverse media) -----------------
    for kind, name in names_to_check:
        n = _normalize(name)
        if not n:
            continue
        if n in lists["sanctions"]:
            matched["sanctions"].append(name)
            flags.append(make_flag(
                "SANCTIONS_HIT", "Sanctions or watchlist match", "high",
                f"{kind} '{name}' matches the sanctions list.",
            ))
            score -= 60
        if n in lists["pep"]:
            matched["pep"].append(name)
            flags.append(make_flag(
                "PEP_MATCH", "Politically exposed person", "medium",
                f"{kind} '{name}' matches the PEP list.",
            ))
            score -= 25
        if n in lists["adverse_media"]:
            matched["adverse_media"].append(name)
            flags.append(make_flag(
                "ADVERSE_MEDIA", "Adverse media match", "medium",
                f"{kind} '{name}' appears in adverse media.",
            ))
            score -= 20

    # --- UBO completeness -------------------------------------------------
    if not ubos:
        flags.append(make_flag(
            "UBO_MISSING", "UBO information missing", "medium",
            "No ultimate beneficial owner was provided.",
        ))
        score -= 20

    # --- Country risk -----------------------------------------------------
    country = str(applicant.get("country", "")).upper().strip()
    if country in lists["prohibited_countries"]:
        flags.append(make_flag(
            "PROHIBITED_COUNTRY", "Prohibited jurisdiction", "high",
            f"Registered in a prohibited jurisdiction ({country}).",
        ))
        score -= 60
        country_status = "prohibited"
    elif country in lists["high_risk_countries"]:
        flags.append(make_flag(
            "HIGH_RISK_COUNTRY", "High-risk country", "medium",
            f"Registered in a high-risk jurisdiction ({country}).",
        ))
        score -= 20
        country_status = "high_risk"
    else:
        country_status = "ok"

    # --- Sector risk (whole-word match to avoid false positives) ----------
    sector = str(applicant.get("sector", "")).lower()
    hit_sector = next(
        (s for s in lists["high_risk_sectors"]
         if s and re.search(r"\b" + re.escape(s) + r"\b", sector)),
        None,
    )
    if hit_sector:
        flags.append(make_flag(
            "HIGH_RISK_SECTOR", "High-risk sector", "medium",
            f"Operates in a higher-risk sector ({hit_sector}).",
        ))
        score -= 15

    score = round(max(min(score, 100.0), 0.0), 1)
    details = {
        "ubo_count": len(ubos),
        "names_screened": len(names_to_check),
        "sanctions_matches": matched["sanctions"],
        "pep_matches": matched["pep"],
        "adverse_media_matches": matched["adverse_media"],
        "country": country or "unknown",
        "country_status": country_status,
        "high_risk_sector": hit_sector or "none",
    }
    return {"sub_score": score, "flags": flags, "details": details}
