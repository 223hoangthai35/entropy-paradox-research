"""
H2 COMPANION (E1 reframing) — RPS plausible-range bounds analysis.

Companion to the tier-based primary test (h2_tier_based.py). Acknowledges
that per-market RPS data quality is heterogeneous (see §3.5.3 paradox)
and reports rho(H, RPS) as a *distribution* over the plausible-range
of each market's RPS rather than a single point estimate.

Methodology:
  - For each market, define a plausible RPS range based on documented
    primary sources covering the analysis window.
  - Sample RPS uniformly from each market's range, recompute Spearman rho.
  - Report rho distribution: mean, median, 95% CI, p(rho > 0.5).

This makes the continuous-RPS test robust to source-heterogeneity
concerns without requiring a single "correct" point estimate per market.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
PRIMARY_CSV = os.path.join(OUTPUT_DIR, "cross_market_summary_v2.csv")

# RPS plausible ranges per market (low, high)
# Source bounds documented per market:
RPS_BOUNDS: dict[str, tuple[float, float]] = {
    # VinaCapital + Vietnam SSC + multiple year-by-year readings (2020-2024)
    "VNINDEX": (0.80, 0.92),
    # PSE 2023 Annual Report (0.68) vs PSE Stock Market Investor Profile (0.165)
    # Two PSE documents differ; use full range as plausible bound
    "BVB": (0.20, 0.25),
    # ASIFMA 2022 (0.70 COVID-peak) → KRX March 2026 (0.45) → mid-2025 (0.30)
    "KOSPI": (0.30, 0.70),
    # NSE India FY21 (0.45) → FY24/25 (0.336)
    "NIFTY": (0.34, 0.45),
    # SIFMA ownership (0.18) vs MEMX retail order flow (0.30-0.37)
    "SPX": (0.18, 0.37),
    # UK FCA / LSE limited public; conservative bounds
    "FTSE": (0.15, 0.25),
    # JPX Trading-by-Investor-Type
    "NIKKEI": (0.18, 0.25),
    # Pre-ETF crypto retail dominance (0.85-0.90) → post-ETF mix (0.55-0.75)
    "BTC": (0.55, 0.85),
}

# Pre-registered point estimates (for comparison)
RPS_POINT: dict[str, float] = {
    "VNINDEX": 0.90, "BVB": 0.225, "KOSPI": 0.70, "NIFTY": 0.40,
    "SPX": 0.22, "FTSE": 0.18, "NIKKEI": 0.18, "BTC": 0.55,
}

N_MC = 10_000
SEED = 42


def load_h_stats() -> pd.DataFrame:
    df = pd.read_csv(PRIMARY_CSV)
    cols = ["market", "H_stat"]
    if "H_stat_filtered" in df.columns:
        cols.append("H_stat_filtered")
    return df[cols].copy()


def bounds_mc(H_values: dict[str, float], n_mc: int = N_MC, seed: int = SEED,
              threshold: float = 0.5) -> dict[str, Any]:
    """MC sample RPS uniform from per-market plausible ranges; recompute rho."""
    rng = np.random.default_rng(seed)
    markets = list(H_values.keys())
    h_arr = np.array([H_values[m] for m in markets])
    lows = np.array([RPS_BOUNDS[m][0] for m in markets])
    highs = np.array([RPS_BOUNDS[m][1] for m in markets])

    rhos = np.empty(n_mc, dtype=float)
    p_values = np.empty(n_mc, dtype=float)
    for i in range(n_mc):
        sampled_rps = rng.uniform(lows, highs)
        rho, p = spearmanr(h_arr, sampled_rps)
        rhos[i] = rho
        p_values[i] = p

    return {
        "n_trials": n_mc,
        "rho_mean": float(np.mean(rhos)),
        "rho_median": float(np.median(rhos)),
        "rho_std": float(np.std(rhos, ddof=1)),
        "rho_p025": float(np.percentile(rhos, 2.5)),
        "rho_p05": float(np.percentile(rhos, 5)),
        "rho_p25": float(np.percentile(rhos, 25)),
        "rho_p75": float(np.percentile(rhos, 75)),
        "rho_p95": float(np.percentile(rhos, 95)),
        "rho_p975": float(np.percentile(rhos, 97.5)),
        "rho_min": float(np.min(rhos)),
        "rho_max": float(np.max(rhos)),
        f"P_rho_gt_{threshold}": float(np.mean(rhos > threshold)),
        "P_p_lt_0.05": float(np.mean(p_values < 0.05)),
        "P_p_lt_0.10": float(np.mean(p_values < 0.10)),
    }


def main() -> int:
    df_h = load_h_stats()
    H_raw = {row["market"]: float(row["H_stat"]) for _, row in df_h.iterrows()}
    H_filt = ({row["market"]: float(row["H_stat_filtered"]) for _, row in df_h.iterrows()}
              if "H_stat_filtered" in df_h.columns else None)

    print("=" * 70)
    print("  H2 COMPANION (E1 reframing) — RPS plausible-range bounds analysis")
    print("=" * 70)
    print("\n  Per-market plausible RPS ranges:")
    print(f"  {'market':<10}  {'low':>6}  {'high':>6}  {'midpoint':>9}  {'pre-reg':>7}")
    for m in H_raw.keys():
        lo, hi = RPS_BOUNDS[m]
        mid = (lo + hi) / 2
        print(f"  {m:<10}  {lo:>6.2f}  {hi:>6.2f}  {mid:>9.3f}  {RPS_POINT[m]:>7.2f}")

    raw = bounds_mc(H_raw)
    filt = bounds_mc(H_filt) if H_filt else None

    print(f"\n  RAW specification (10,000 MC trials, uniform sampling from RPS bounds):")
    print(f"    rho mean = {raw['rho_mean']:+.4f}   median = {raw['rho_median']:+.4f}   sd = {raw['rho_std']:.3f}")
    print(f"    95% CI   = [{raw['rho_p025']:+.4f}, {raw['rho_p975']:+.4f}]")
    print(f"    50% CI   = [{raw['rho_p25']:+.4f}, {raw['rho_p75']:+.4f}]")
    print(f"    range    = [{raw['rho_min']:+.4f}, {raw['rho_max']:+.4f}]")
    print(f"    P(rho > 0.5)   = {raw['P_rho_gt_0.5']*100:.1f}%")
    print(f"    P(p < 0.05)    = {raw['P_p_lt_0.05']*100:.1f}%")
    print(f"    P(p < 0.10)    = {raw['P_p_lt_0.10']*100:.1f}%")

    if filt:
        print(f"\n  FILTERED specification:")
        print(f"    rho mean = {filt['rho_mean']:+.4f}   median = {filt['rho_median']:+.4f}   sd = {filt['rho_std']:.3f}")
        print(f"    95% CI   = [{filt['rho_p025']:+.4f}, {filt['rho_p975']:+.4f}]")
        print(f"    50% CI   = [{filt['rho_p25']:+.4f}, {filt['rho_p75']:+.4f}]")
        print(f"    range    = [{filt['rho_min']:+.4f}, {filt['rho_max']:+.4f}]")
        print(f"    P(rho > 0.5)   = {filt['P_rho_gt_0.5']*100:.1f}%")
        print(f"    P(p < 0.05)    = {filt['P_p_lt_0.05']*100:.1f}%")
        print(f"    P(p < 0.10)    = {filt['P_p_lt_0.10']*100:.1f}%")

    payload = {
        "spec": "H2 COMPANION E1 reframing — RPS plausible-range bounds analysis",
        "rps_bounds": {m: {"low": lo, "high": hi} for m, (lo, hi) in RPS_BOUNDS.items()},
        "rps_point_pre_reg": RPS_POINT,
        "n_mc_trials": N_MC,
        "seed": SEED,
        "raw_results": raw,
        "filtered_results": filt,
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_rps_bounds.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
