"""
Helper for the Case A validation tests (T1 event study, T3 shuffle test).

Wraps `validation/_features.run_full_pipeline` so the validation scripts can
ask for filtered flip dates / filtered labels directly without rebuilding the
feature pipeline themselves.

Caching: the result is memoized per (market, start, end) tuple so T1 + T3 +
the shuffle bootstrap can share one fit. Cache lives only in-process.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import List

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import (
    flip_dates,
    run_full_pipeline,
)


# Per-market source map; extend here when validating a new market.
_SOURCE_MAP = {
    "VNINDEX": ("VNINDEX", "vnstock"),
    "SP500":   ("^GSPC",   "yfinance"),
    "BTC":     ("BTC-USD", "yfinance"),
}


@lru_cache(maxsize=8)
def _cached_pipeline(market: str, start: str, end: str | None):
    if market not in _SOURCE_MAP:
        raise KeyError(
            f"Unknown market {market!r}; known: {sorted(_SOURCE_MAP)}"
        )
    ticker, source = _SOURCE_MAP[market]
    return run_full_pipeline(
        market=market,
        ticker=ticker,
        source=source,
        start=start,
        end=end,
    )


def get_filtered_flip_dates(
    market: str = "VNINDEX",
    start: str = "2020-01-01",
    end: str | None = None,
) -> List[pd.Timestamp]:
    """Sorted list of dates where the post-hysteresis label changes."""
    out = _cached_pipeline(market, start, end)
    return list(flip_dates(out["filtered_labels"]))


def get_filtered_labels(
    market: str = "VNINDEX",
    start: str = "2020-01-01",
    end: str | None = None,
) -> pd.Series:
    """Full post-hysteresis label series indexed by trading date."""
    out = _cached_pipeline(market, start, end)
    return out["filtered_labels"]


def get_raw_labels(
    market: str = "VNINDEX",
    start: str = "2020-01-01",
    end: str | None = None,
) -> pd.Series:
    """Pre-hysteresis (raw GMM argmax) label series — for diagnostics."""
    out = _cached_pipeline(market, start, end)
    return out["raw_labels"]


if __name__ == "__main__":
    flips = get_filtered_flip_dates("VNINDEX", "2020-01-01", "2026-04-17")
    print(f"  {len(flips)} filtered flips on VNINDEX 2020-01-01 -> 2026-04-17")
    for d in flips:
        print(f"    {d.date()}")
