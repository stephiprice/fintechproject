"""Validation and cleaning for uploaded bank-transaction data.

Untrusted CSV uploads are the main attack and failure surface of the app, so
every file passes through validate_transactions() before any scoring runs. On
bad input it raises a clear ValueError that the UI turns into a friendly
message, rather than letting a raw stack trace reach the user.

Expected columns (case-sensitive):
    date, description, amount, balance
where amount is positive for money in and negative for money out.
"""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["date", "description", "amount", "balance"]
MAX_ROWS = 100_000


def validate_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned, typed copy of the transactions, or raise ValueError."""
    if df is None or len(df) == 0:
        raise ValueError("the file contains no transactions.")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "missing required column(s): " + ", ".join(missing)
            + ". Expected columns: " + ", ".join(REQUIRED_COLUMNS) + "."
        )

    if len(df) > MAX_ROWS:
        raise ValueError(f"too many rows ({len(df):,}); the limit is {MAX_ROWS:,}.")

    clean = df[REQUIRED_COLUMNS].copy()
    clean["date"] = pd.to_datetime(clean["date"], errors="coerce")
    clean["amount"] = pd.to_numeric(clean["amount"], errors="coerce")
    clean["balance"] = pd.to_numeric(clean["balance"], errors="coerce")
    clean["description"] = clean["description"].astype(str)

    bad_dates = int(clean["date"].isna().sum())
    if bad_dates:
        raise ValueError(f"{bad_dates} row(s) have an unreadable date.")

    bad_amounts = int(clean["amount"].isna().sum())
    if bad_amounts:
        raise ValueError(f"{bad_amounts} row(s) have a non-numeric amount.")

    # A missing balance is recoverable: carry the last known balance forward.
    clean["balance"] = clean["balance"].ffill().fillna(0.0)

    return clean.sort_values("date").reset_index(drop=True)
