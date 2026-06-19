"""Generate synthetic SME bank-transaction CSVs for the CreditPass demo.

Run:
    python data/generate_synthetic.py

Creates three sample files in data/samples/ that tell a clear story in the
demo: a healthy applicant (Go), a marginal one (Review), and a risky one
(Decline). Deterministic via a fixed random seed, so the demo is repeatable.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

SEED = 42
START = "2025-09-01"
DAYS = 180
OUT_DIR = os.path.join(os.path.dirname(__file__), "samples")

# Monthly euro figures per profile. Revenue volatility (rev_vol) is the
# month-to-month standard deviation as a fraction of revenue.
PROFILES = {
    "healthy":  dict(base_rev=18000, rev_vol=0.08, rent=2500, payroll=7000,
                     supplier=3500, loan=800,  start_balance=15000),
    "marginal": dict(base_rev=17000, rev_vol=0.30, rent=2600, payroll=6000,
                     supplier=2800, loan=1800, start_balance=6000),
    "risky":    dict(base_rev=11000, rev_vol=0.55, rent=3200, payroll=7500,
                     supplier=4000, loan=3800, start_balance=1500),
}


def build_profile(rng: np.random.Generator, p: dict) -> pd.DataFrame:
    """Build one SME's daily transaction ledger with a running balance."""
    dates = pd.date_range(START, periods=DAYS, freq="D")
    month_keys = sorted({(d.year, d.month) for d in dates})
    # One revenue factor per month gives realistic month-to-month volatility.
    month_factor = {m: max(1 + rng.normal(0, p["rev_vol"]), 0.2) for m in month_keys}

    rows = []
    balance = float(p["start_balance"])
    for d in dates:
        mf = month_factor[(d.year, d.month)]
        # Revenue deposits on Mon/Wed/Fri (~13 per month).
        if d.weekday() in (0, 2, 4):
            amt = round(p["base_rev"] / 13 * mf, 2)
            balance += amt
            rows.append((d.date(), "Customer deposit", amt, round(balance, 2)))
        # Rent + loan repayment on the 1st.
        if d.day == 1:
            balance -= p["rent"]
            rows.append((d.date(), "Rent payment", -float(p["rent"]), round(balance, 2)))
            balance -= p["loan"]
            rows.append((d.date(), "Loan repayment", -float(p["loan"]), round(balance, 2)))
        # Payroll on the 25th.
        if d.day == 25:
            balance -= p["payroll"]
            rows.append((d.date(), "Payroll", -float(p["payroll"]), round(balance, 2)))
        # Supplier payments weekly (Thursday).
        if d.weekday() == 3:
            amt = round(p["supplier"] / 4 * max(1 + rng.normal(0, 0.2), 0.1), 2)
            balance -= amt
            rows.append((d.date(), "Supplier payment", -amt, round(balance, 2)))

    return pd.DataFrame(rows, columns=["date", "description", "amount", "balance"])


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, p in PROFILES.items():
        # Per-profile seed so each file is different but reproducible.
        rng = np.random.default_rng(SEED + sum(ord(c) for c in name))
        df = build_profile(rng, p)
        path = os.path.join(OUT_DIR, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"wrote {path}  ({len(df)} rows)")


if __name__ == "__main__":
    main()
