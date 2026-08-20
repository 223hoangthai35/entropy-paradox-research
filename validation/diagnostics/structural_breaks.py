"""
Structural breakpoint detection per market (Plan v9 §A.7, Major M-10).

Tests whether the post-COVID 2020-2026 window contains internal structural
breaks that could confound the regime classification. Uses Bai-Perron-style
multiple breakpoint detection (ruptures library) with Pelt algorithm and
RBF cost function on:
  (a) log returns
  (b) WPE feature series
  (c) SPE_Z feature series

If breaks found within window: report dates; flag if they coincide with
known events (e.g., Fed pivot March 2022, banking crisis March 2023, BTC ETF
Jan 2024, FTSE upgrade Oct 2025).

Output: validation/results_v2/structural_breaks.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

import ruptures as rpt
from validation._features import run_full_pipeline, SPE_Z_WIN

MARKETS = [
    {"name": "VNINDEX", "ticker": "VNINDEX", "source": "vnstock"},
    {"name": "BVB",     "ticker": "BVB:BET",  "source": "tvdatafeed"},
    {"name": "KOSPI",   "ticker": "^KS11",   "source": "yfinance"},
    {"name": "NIFTY",   "ticker": "^NSEI",   "source": "yfinance"},
    {"name": "SPX",     "ticker": "^GSPC",   "source": "yfinance"},
    {"name": "FTSE",    "ticker": "^FTSE",   "source": "yfinance"},
    {"name": "NIKKEI",  "ticker": "^N225",   "source": "yfinance"},
    {"name": "BTC",     "ticker": "BTC-USD", "source": "yfinance"},
]

START = "2018-01-01"
END = "2026-06-30"
ANALYSIS_START = "2020-04-17"  # post-COVID window start (matches paper)
PELT_PENALTY = 10  # higher = fewer breaks; tunable
MIN_SIZE = 60  # minimum segment size = ~3 months trading days

OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2")

# Known macro events for context
KNOWN_EVENTS = {
    "2022-03-16": "Fed first rate hike (post-COVID)",
    "2023-03-13": "Banking stress (SVB collapse)",
    "2024-01-11": "BTC ETF approval",
    "2025-10-07": "FTSE Russell Vietnam reclassification announcement",
}


def detect_breaks_pelt(series: np.ndarray, penalty: int = PELT_PENALTY,
                       min_size: int = MIN_SIZE) -> list[int]:
    """Pelt breakpoint detection with RBF cost; returns indices of break points."""
    valid_mask = ~np.isnan(series)
    if valid_mask.sum() < 2 * min_size:
        return []
    valid_series = series[valid_mask]
    algo = rpt.Pelt(model="rbf", min_size=min_size).fit(valid_series.reshape(-1, 1))
    breaks = algo.predict(pen=penalty)
    # Map back to original indices
    valid_indices = np.where(valid_mask)[0]
    return [int(valid_indices[b - 1]) for b in breaks if b < len(valid_series)]


def break_dates_for_series(series_index: pd.DatetimeIndex, break_idx: list[int]) -> list[str]:
    return [series_index[i].strftime("%Y-%m-%d") for i in break_idx if i < len(series_index)]


def main() -> int:
    print("=" * 70)
    print("  STRUCTURAL BREAKPOINT DETECTION PER MARKET")
    print("=" * 70)
    print(f"  Window: {ANALYSIS_START} to {END}")
    print(f"  Algorithm: PELT (Killick et al. 2012) with RBF cost")
    print(f"  Penalty = {PELT_PENALTY}, min segment size = {MIN_SIZE} bars")
    print()

    results = {}
    t_start = time.time()

    for cfg in MARKETS:
        name = cfg["name"]
        print(f"[{name}] loading + breakpoint detection...")
        try:
            out = run_full_pipeline(market=name, ticker=cfg["ticker"], source=cfg["source"], start=START, end=END)
        except Exception as e:
            print(f"  [SKIP] {type(e).__name__}: {e}")
            continue

        ohlcv = out["ohlcv"]
        feat = out["features"]

        # Restrict to analysis window
        ohlcv_w = ohlcv[ohlcv.index >= ANALYSIS_START]
        feat_w = feat[feat.index >= ANALYSIS_START]
        if len(ohlcv_w) < 2 * MIN_SIZE or len(feat_w) < 2 * MIN_SIZE:
            print(f"  [SKIP] insufficient bars in analysis window")
            continue

        # Log returns
        log_ret = np.log(ohlcv_w["Close"] / ohlcv_w["Close"].shift(1)).dropna().values
        log_ret_idx = ohlcv_w.index[1:1 + len(log_ret)]
        breaks_ret = detect_breaks_pelt(log_ret)
        dates_ret = [log_ret_idx[i].strftime("%Y-%m-%d") for i in breaks_ret if i < len(log_ret_idx)]

        # WPE
        breaks_wpe = detect_breaks_pelt(feat_w["WPE"].values)
        dates_wpe = break_dates_for_series(feat_w.index, breaks_wpe)

        # SPE_Z
        breaks_spe = detect_breaks_pelt(feat_w["SPE_Z"].values)
        dates_spe = break_dates_for_series(feat_w.index, breaks_spe)

        results[name] = {
            "n_bars_window": int(len(ohlcv_w)),
            "n_features_window": int(len(feat_w)),
            "log_returns_breaks": {"n_breaks": len(dates_ret), "dates": dates_ret},
            "WPE_breaks": {"n_breaks": len(dates_wpe), "dates": dates_wpe},
            "SPE_Z_breaks": {"n_breaks": len(dates_spe), "dates": dates_spe},
        }
        print(f"  log_returns: {len(dates_ret)} breaks {dates_ret if dates_ret else ''}")
        print(f"  WPE       : {len(dates_wpe)} breaks {dates_wpe if dates_wpe else ''}")
        print(f"  SPE_Z     : {len(dates_spe)} breaks {dates_spe if dates_spe else ''}")

    print("\n" + "=" * 70)
    print("  CROSS-MARKET BREAK DATE OVERLAP")
    print("=" * 70)
    all_dates = set()
    for r in results.values():
        all_dates.update(r["log_returns_breaks"]["dates"])
        all_dates.update(r["WPE_breaks"]["dates"])
        all_dates.update(r["SPE_Z_breaks"]["dates"])
    print(f"  Total unique break dates across markets + features: {len(all_dates)}")
    if KNOWN_EVENTS:
        print(f"\n  Known macro events for context:")
        for d, label in KNOWN_EVENTS.items():
            print(f"    {d}: {label}")

    payload = {
        "spec": "Bai-Perron-style structural breakpoint detection per market (PELT/RBF)",
        "n_markets": len(results),
        "analysis_start": ANALYSIS_START,
        "analysis_end": END,
        "pelt_penalty": PELT_PENALTY,
        "min_segment_size": MIN_SIZE,
        "elapsed_seconds": float(time.time() - t_start),
        "per_market": results,
        "known_events_for_context": KNOWN_EVENTS,
    }
    out_path = os.path.join(OUTPUT_DIR, "diagnostics/structural_breaks.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
