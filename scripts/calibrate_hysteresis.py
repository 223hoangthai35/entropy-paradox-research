"""
Hysteresis grid-search calibration on VNINDEX (post-2020 sample).

Goal: pick (delta_hard, delta_soft, t_persist) for HysteresisGMMWrapper such
that the post-filter regime label flips ~2-5 times per trading year on the
Plane 1 (Price) classifier — the band considered "operationally legible" for
risk-management consumers (a flip every 2-6 months).

Why post-2020 only: liquidity, retail participation and circuit-breaker
regime on VNINDEX changed substantially before 2020; including pre-2020
bars biases the flip-rate metric toward an obsolete microstructure.

Run:
    python scripts/calibrate_hysteresis.py
    python scripts/calibrate_hysteresis.py --ticker VNINDEX --start 2020-01-01

Output: a ranked table of (params -> flips/year on raw, flips/year on
hysteresis-filtered, agreement rate). The recommended pick is highlighted.
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.data_skill import get_latest_market_data
from skills.quant_skill import (
    calc_rolling_wpe,
    calc_rolling_price_sample_entropy,
    cal_spe_z_rolling,
)
from skills.ds_skill import EntropyPhaseSpaceClassifier, HysteresisGMMWrapper


# Calibration grid — covers the operationally meaningful range.
# delta_hard caps the immediate-flip threshold; delta_soft sets the soft
# margin required to start accumulating persistence; t_persist sets how many
# consecutive bars at >= delta_soft are required before the held label flips.
DELTA_HARD_GRID = [0.30, 0.40, 0.50, 0.60]
DELTA_SOFT_GRID = [0.15, 0.20, 0.25, 0.30, 0.35]
T_PERSIST_GRID  = [3, 5, 8, 13, 21]

# Empirical note: VNINDEX (post-2020) raw GMM emits ~28-30 flips/yr — the
# original 2-5 design target is unreachable on the underlying signal without
# pathologically aggressive hysteresis (effectively freezing the classifier).
# The realistic operational band, given the 5+ macro regimes the index has
# traversed since 2020 (COVID, 2021 mania, 2022 bear, 2023 recovery,
# 2024 sideways, 2025 reflation), is 4-10 flips/yr — roughly one structural
# label change every 1-2 months.
TARGET_FLIPS_LO = 4.0   # flips per trading year (lower acceptable bound)
TARGET_FLIPS_HI = 10.0  # flips per trading year (upper acceptable bound)
TRADING_DAYS_PER_YEAR = 252


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the Plane-1 feature matrix [WPE, SPE_Z] used by the GMM."""
    log_returns = np.log(df["Close"] / df["Close"].shift(1)).values
    wpe, _ = calc_rolling_wpe(log_returns, m=3, tau=1, window=22)
    sampen = calc_rolling_price_sample_entropy(df["Close"].values, window=60)
    spe_z = cal_spe_z_rolling(sampen, window=504)
    feat = pd.DataFrame({"WPE": wpe, "SPE_Z": spe_z}, index=df.index).dropna()
    return feat


def _count_flips(labels: np.ndarray) -> int:
    """Number of label changes between consecutive bars."""
    if len(labels) < 2:
        return 0
    return int((np.diff(labels) != 0).sum())


def _flips_per_year(labels: np.ndarray) -> float:
    n = len(labels)
    if n == 0:
        return 0.0
    return _count_flips(labels) * TRADING_DAYS_PER_YEAR / n


def calibrate(
    ticker: str = "VNINDEX",
    start_date: str = "2020-01-01",
) -> pd.DataFrame:
    """
    Returns a DataFrame ranked by 'fitness' — closest flip-rate to the
    target band, with smaller (delta_hard - delta_soft) preferred as a
    tiebreak (less hysteresis is preferable when both meet the target).
    """
    print(f"  [Calibration] Loading {ticker} from {start_date} ...")
    df = get_latest_market_data(ticker=ticker, start_date=start_date)
    df = df[df.index >= pd.Timestamp(start_date)]

    print(f"  [Calibration] Building Plane-1 features ...")
    feat = _build_features(df)
    if len(feat) < 504:
        raise RuntimeError(
            f"Need >= 504 bars of valid features after rolling SPE_Z; got {len(feat)}."
        )

    print(f"  [Calibration] Fitting EntropyPhaseSpaceClassifier on {len(feat)} bars ...")
    clf = EntropyPhaseSpaceClassifier(n_components=3, random_state=42)
    raw_labels = clf.fit_predict(feat.values)
    raw_flips_per_yr = _flips_per_year(raw_labels)
    print(f"  [Calibration] Raw labels: {raw_flips_per_yr:.2f} flips/yr "
          f"({_count_flips(raw_labels)} flips over {len(raw_labels)} bars).")

    rows = []
    for d_hard, d_soft, tp in itertools.product(
        DELTA_HARD_GRID, DELTA_SOFT_GRID, T_PERSIST_GRID
    ):
        if d_hard < d_soft:
            continue
        wrap = HysteresisGMMWrapper(
            clf, delta_hard=d_hard, delta_soft=d_soft, t_persist=tp
        )
        filtered = wrap.transform(feat.values)
        fpy = _flips_per_year(filtered)
        agree = float(np.mean(filtered == raw_labels))
        # Distance from the centre of the target band.
        target_centre = (TARGET_FLIPS_LO + TARGET_FLIPS_HI) / 2.0
        in_band = TARGET_FLIPS_LO <= fpy <= TARGET_FLIPS_HI
        distance = abs(fpy - target_centre)
        rows.append({
            "delta_hard": d_hard,
            "delta_soft": d_soft,
            "t_persist": tp,
            "raw_flips_per_yr": round(raw_flips_per_yr, 2),
            "filtered_flips_per_yr": round(fpy, 2),
            "agreement_rate": round(agree, 4),
            "in_target_band": in_band,
            "distance_from_centre": round(distance, 3),
        })

    out = pd.DataFrame(rows)
    # Rank: in-band first; then nearest to centre; tiebreak by hysteresis tightness.
    out["hysteresis_width"] = out["delta_hard"] - out["delta_soft"]
    out = out.sort_values(
        by=["in_target_band", "distance_from_centre", "hysteresis_width", "t_persist"],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", default="VNINDEX")
    ap.add_argument("--start", default="2020-01-01",
                    help="Inclusive start date (YYYY-MM-DD). Pre-2020 data is "
                         "intentionally excluded — VNINDEX microstructure "
                         "shifted substantially before then.")
    args = ap.parse_args()

    table = calibrate(ticker=args.ticker, start_date=args.start)

    print()
    print("=" * 78)
    print(f"  HYSTERESIS GRID SEARCH — target {TARGET_FLIPS_LO:.0f}-{TARGET_FLIPS_HI:.0f} flips/yr")
    print("=" * 78)
    pd.set_option("display.width", 120)
    pd.set_option("display.max_columns", None)
    print(table.to_string(index=False))
    print()
    best = table.iloc[0]
    print("=" * 78)
    print("  RECOMMENDED CALIBRATION")
    print("=" * 78)
    print(f"  delta_hard = {best['delta_hard']:.2f}")
    print(f"  delta_soft = {best['delta_soft']:.2f}")
    print(f"  t_persist  = {int(best['t_persist'])}")
    print(f"    -> {best['filtered_flips_per_yr']:.2f} flips/yr "
          f"(raw: {best['raw_flips_per_yr']:.2f}, in-band: {bool(best['in_target_band'])}, "
          f"label agreement {best['agreement_rate']*100:.1f}%)")
    print()
    print("  Update HYSTERESIS_DELTA_HARD/SOFT/T_PERSIST in skills/ds_skill.py "
          "if these differ from the in-code defaults.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
