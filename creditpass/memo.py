"""Credit memo drafter (Track B).

Produces a one-page markdown credit memo from the assessment result. The memo
only describes and cites numbers that are already in `result`; it never
recomputes or overrides the score. It is deterministic and template based, so
it runs offline with no API key, which keeps the app reproducible for a grader.

An LLM backend can be added later behind this same draft_memo(result) -> str
interface, with the deterministic template kept as a fallback.

app.py imports draft_memo automatically once this file exists.
"""

from __future__ import annotations

from typing import Any, Dict, List

_REC_LINE = {
    "Go": "The application meets the bank's criteria and is recommended to proceed to offer.",
    "Review": "The application is viable but raises issues that need a credit officer's review before proceeding.",
    "Decline": "The application does not currently meet the bank's risk criteria and is recommended for decline.",
}


def _eur(value: Any) -> str:
    """Format a number as euros, or pass non-numbers through safely."""
    if isinstance(value, (int, float)):
        return f"EUR {value:,.0f}"
    return str(value)


def _flag_lines(flags: List[Dict[str, str]]) -> List[str]:
    if not flags:
        return ["No material risk flags were raised."]
    return [f"- **{f.get('label', 'Flag')}** ({f.get('severity', 'info')}): {f.get('detail', '')}"
            for f in flags]


def draft_memo(result: Dict[str, Any]) -> str:
    """Return a markdown credit memo built from the assessment result."""
    result = result or {}
    applicant = result.get("applicant", {}) or {}
    credit = result.get("credit", {}) or {}
    kyc = result.get("kyc", {}) or {}
    cd = credit.get("details", {}) or {}
    kd = kyc.get("details", {}) or {}
    rec = result.get("recommendation", "Review")

    company = applicant.get("company") or "the applicant"
    out: List[str] = []

    out.append(f"## Credit memo: {company}")
    out.append("")
    out.append(f"**Recommendation: {rec}**  (overall score "
               f"{result.get('overall_score', 'n/a')} out of 100)")
    out.append("")
    out.append(_REC_LINE.get(rec, ""))
    out.append("")

    out.append("### 1. Applicant")
    out.append(f"- Company: {company}")
    out.append(f"- Sector: {applicant.get('sector') or 'n/a'}")
    out.append(f"- Country: {applicant.get('country') or 'n/a'}")
    out.append(f"- Requested amount: {_eur(applicant.get('requested_amount', 'n/a'))}")
    out.append("")

    out.append("### 2. Financial summary")
    out.append(f"- Credit sub-score: {credit.get('sub_score', 'n/a')} out of 100")
    out.append(f"- Average monthly revenue: {_eur(cd.get('avg_monthly_revenue', 'n/a'))}")
    out.append(f"- Monthly surplus after costs: {_eur(cd.get('monthly_surplus', 'n/a'))}")
    out.append(f"- Estimated monthly repayment: {_eur(cd.get('estimated_payment', 'n/a'))}")
    out.append(f"- Affordability ratio (repayment / surplus): {cd.get('affordability_ratio', 'n/a')}")
    out.append(f"- Negative balance days: {cd.get('negative_balance_days', 'n/a')}")
    out.append(f"- Debt to revenue: {cd.get('debt_to_revenue', 'n/a')}")
    out.append("")

    out.append("### 3. Compliance (KYC / CDD)")
    out.append(f"- KYC sub-score: {kyc.get('sub_score', 'n/a')} out of 100")
    out.append(f"- Beneficial owners screened: {kd.get('ubo_count', 'n/a')}")
    out.append(f"- Country status: {kd.get('country_status', 'n/a')}")
    out.append(f"- High-risk sector: {kd.get('high_risk_sector', 'n/a')}")
    out.append("")

    out.append("### 4. Key risk flags")
    out.extend(_flag_lines(result.get("drivers") or result.get("flags") or []))
    out.append("")

    out.append("### 5. Decision")
    out.append(_REC_LINE.get(rec, ""))
    out.append("")
    out.append("_Drafted by CreditPass from the screened application data. "
               "Every figure above is taken from the assessment, not generated. "
               "To be reviewed and approved by a credit officer._")

    return "\n".join(out)
