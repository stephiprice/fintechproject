"""Credit scoring engine (Track A).

Transparent, rule-based scoring of an SME's repayment capacity from its bank
transaction history. It is deterministic and fully explainable by design:
every point deducted maps to a named feature and a flag. That "no black box"
property is exactly the CreditPass selling point, and it keeps the high-stakes
part of the system out of the EU AI Act's high-risk decisioning category.

Expected transactions CSV columns:
    date        (parseable date)
    description (text)
    amount      (float; positive = money in, negative = money out)
    balance     (float; running account balance after the transaction)
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from creditpass.decision import make_flag

# Assumed loan term (months) used to estimate the monthly repayment burden.
ASSUMED_TERM_MONTHS = 36
# Words that mark an outflow as existing debt service.
DEBT_KEYWORDS = ("loan", "repayment", "interest", "lease", "credit")


def _monthly_revenue(tx: pd.DataFrame) -> pd.Series:
    """Total inflow per calendar month."""
    inflows = tx[tx["amount"] > 0].copy()
    if inflows.empty:
        return pd.Series(dtype=float)
    inflows["month"] = inflows["date"].dt.to_period("M")
    return inflows.groupby("month")["amount"].sum()


def score_credit(tx: pd.DataFrame, applicant: Dict[str, Any]) -> Dict[str, Any]:
    """Return a credit sub-result following the shared decision contract."""
    tx = tx.copy()
    tx["date"] = pd.to_datetime(tx["date"])
    tx = tx.sort_values("date")

    flags = []
    score = 100.0

    # --- Feature 1: revenue stability (coefficient of variation) ----------
    monthly_rev = _monthly_revenue(tx)
    avg_revenue = float(monthly_rev.mean()) if not monthly_rev.empty else 0.0
    if len(monthly_rev) >= 2 and avg_revenue > 0:
        cov = float(monthly_rev.std() / monthly_rev.mean())
    else:
        cov = 0.0
    # cov 0 = perfectly stable; > ~0.2 starts to hurt, capped at 30 points.
    score -= min(max(cov - 0.2, 0) * 60, 30)
    if cov > 0.4:
        flags.append(make_flag(
            "REVENUE_VOLATILITY", "Volatile revenue", "medium",
            f"Monthly revenue is unstable (coefficient of variation {cov:.0%}).",
        ))

    # --- Feature 2: negative balance days ---------------------------------
    neg_days = int((tx["balance"] < 0).sum())
    score -= min(neg_days * 1.5, 25)
    if neg_days >= 10:
        flags.append(make_flag(
            "NEG_BALANCE_DAYS", "Frequent negative balance", "high",
            f"Account was overdrawn on {neg_days} recorded transactions.",
        ))
    elif neg_days > 0:
        flags.append(make_flag(
            "NEG_BALANCE_DAYS", "Some negative balance days", "low",
            f"Account was overdrawn on {neg_days} recorded transactions.",
        ))

    # --- Feature 3: existing debt burden ----------------------------------
    desc = tx["description"].astype(str).str.lower()
    is_debt = desc.apply(lambda d: any(k in d for k in DEBT_KEYWORDS))
    n_months = max(len(monthly_rev), 1)
    monthly_debt = float(-tx.loc[is_debt & (tx["amount"] < 0), "amount"].sum()) / n_months
    debt_ratio = (monthly_debt / avg_revenue) if avg_revenue > 0 else 0.0
    score -= min(max(debt_ratio - 0.2, 0) * 80, 25)
    if debt_ratio > 0.35:
        flags.append(make_flag(
            "DEBT_BURDEN", "High existing debt burden", "medium",
            f"Existing debt service is ~{debt_ratio:.0%} of monthly revenue.",
        ))

    # --- Feature 4: affordability of the requested loan -------------------
    requested = float(applicant.get("requested_amount", 0) or 0)
    avg_outflow = float(-tx[tx["amount"] < 0]["amount"].sum()) / n_months
    monthly_surplus = avg_revenue - avg_outflow
    est_payment = requested / ASSUMED_TERM_MONTHS if requested > 0 else 0.0
    if monthly_surplus > 0:
        affordability = est_payment / monthly_surplus
    else:
        affordability = 99.0  # no surplus to service any new debt
    score -= min(max(affordability - 0.5, 0) * 40, 30)
    if affordability > 1.0:
        flags.append(make_flag(
            "AFFORDABILITY", "Loan may be unaffordable", "high",
            f"Estimated repayment is {affordability:.0%} of monthly surplus.",
        ))
    elif affordability > 0.6:
        flags.append(make_flag(
            "AFFORDABILITY", "Tight affordability", "medium",
            f"Estimated repayment is {affordability:.0%} of monthly surplus.",
        ))

    score = round(max(min(score, 100.0), 0.0), 1)

    details = {
        "avg_monthly_revenue": round(avg_revenue, 2),
        "revenue_cov": round(cov, 3),
        "negative_balance_days": neg_days,
        "monthly_debt_service": round(monthly_debt, 2),
        "debt_to_revenue": round(debt_ratio, 3),
        "monthly_surplus": round(monthly_surplus, 2),
        "estimated_payment": round(est_payment, 2),
        "affordability_ratio": round(affordability, 3),
    }
    return {"sub_score": score, "flags": flags, "details": details}
