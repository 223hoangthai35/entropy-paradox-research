"""
Link B empirical tests — direct test of entropy-LEVEL ↔ RPS relationship
on the 8-market panel.

Plan v9 §A.1. Link B in v3_4 §6.1 asserts: "Lower-information retail flow
exhibits behavioral correlation that reduces ordinal-pattern complexity
in the price-generating process." This script tests Link B empirically
in TWO ways:

  Test B.3.1: per-market mean(WPE) and mean(SPE_Z) → Spearman ρ across
              the 8 markets vs RPS. Predicted under herding mechanism:
              negative ρ (high RPS → low entropy).

  Test B.3.2: per-market per-regime spread = max − min across {Det, Trans,
              Sto} of mean entropy → Spearman ρ vs RPS. Predicted under
              Link B: positive ρ (high-RPS markets exhibit larger entropy
              gap between coordinated and random regimes).

Output: validation/results_v2/link_b_tests.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import run_full_pipeline, SPE_Z_WIN
from skills.ds_skill import REGIME_NAMES

MARKETS: list[dict[str, Any]] = [
    {"name": "VNINDEX", "ticker": "VNINDEX", "source": "vnstock"},
    {"name": "PSEI",    "ticker": "PSEI.PS", "source": "yfinance"},
    {"name": "KOSPI",   "ticker": "^KS11",   "source": "yfinance"},
    {"name": "NIFTY",   "ticker": "^NSEI",   "source": "yfinance"},
    {"name": "SPX",     "ticker": "^GSPC",   "source": "yfinance"},
    {"name": "FTSE",    "ticker": "^FTSE",   "source": "yfinance"},
    {"name": "NIKKEI",  "ticker": "^N225",   "source": "yfinance"},
    {"name": "BTC",     "ticker": "BTC-USD", "source": "yfinance"},
]

# Cascade-spec RPS values (matches h2_cascade.py CASCADE point estimates;
# for P2/P3 markets we use the central / mean of their distribution)
RPS = {
    "VNINDEX": 0.90, "PSEI": 0.68, "KOSPI": 0.45, "NIFTY": 0.40,
    "SPX": 0.275, "FTSE": 0.20, "NIKKEI": 0.18, "BTC": 0.55,
}

START = "2018-01-01"
END = "2026-04-17"
RNG_SEED = 42
N_PERM = 10_000  # permutation iterations for cross-market Spearman CI

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def per_market_entropy_stats(out: dict[str, Any]) -> dict[str, Any]:
    """Compute mean(WPE), mean(SPE_Z) per market + per-regime breakdown."""
    feat: pd.DataFrame = out["features"]
    raw_labels: pd.Series = out["raw_labels"]
    filt_labels: pd.Series = out["filtered_labels"]

    # Overall means (Test B.3.1 inputs)
    overall = {
        "n_obs": int(len(feat)),
        "mean_WPE": float(feat["WPE"].mean()),
        "mean_SPE_Z": float(feat["SPE_Z"].mean()),
        "median_WPE": float(feat["WPE"].median()),
        "median_SPE_Z": float(feat["SPE_Z"].median()),
    }

    # Per-regime breakdown (Test B.3.2 inputs)
    raw_arr = raw_labels.astype(int).map(REGIME_NAMES).values
    filt_arr = filt_labels.astype(int).map(REGIME_NAMES).values

    def regime_means(label_arr, label_name):
        out_dict = {}
        for r in ["Deterministic", "Transitional", "Stochastic"]:
            mask = label_arr == r
            n_r = int(mask.sum())
            if n_r > 5:
                out_dict[f"{label_name}_WPE_{r}"] = float(feat["WPE"].values[mask].mean())
                out_dict[f"{label_name}_SPE_Z_{r}"] = float(feat["SPE_Z"].values[mask].mean())
                out_dict[f"{label_name}_n_{r}"] = n_r
            else:
                out_dict[f"{label_name}_WPE_{r}"] = float("nan")
                out_dict[f"{label_name}_SPE_Z_{r}"] = float("nan")
                out_dict[f"{label_name}_n_{r}"] = n_r
        return out_dict

    overall.update(regime_means(raw_arr, "raw"))
    overall.update(regime_means(filt_arr, "filt"))

    # Per-regime spreads (max − min of mean entropy across regimes)
    for label_name in ["raw", "filt"]:
        for feat_name in ["WPE", "SPE_Z"]:
            vals = [overall[f"{label_name}_{feat_name}_{r}"] for r in ["Deterministic", "Transitional", "Stochastic"]]
            vals = [v for v in vals if not np.isnan(v)]
            if len(vals) >= 2:
                overall[f"{label_name}_{feat_name}_spread"] = float(max(vals) - min(vals))
            else:
                overall[f"{label_name}_{feat_name}_spread"] = float("nan")

    return overall


def permutation_spearman_ci(x: np.ndarray, y: np.ndarray, n_perm: int = N_PERM,
                             alpha: float = 0.05, seed: int = 42) -> tuple[float, float, float, float]:
    """Compute observed Spearman rho + permutation-based 2-sided p-value
    + percentile CI from bootstrap (paired resampling at n=8 is degenerate;
    use rank-permutation CI by perturbing x and computing rho distribution
    under H0 of no association — gives null distribution for p-value.

    For CI on observed rho: at n=8 bootstrap is unreliable; report
    permutation-based 2-sided p-value as primary inference."""
    rho_obs, _ = spearmanr(x, y)
    rng = np.random.default_rng(seed)
    null_rhos = np.empty(n_perm)
    for i in range(n_perm):
        perm = rng.permutation(y)
        r, _ = spearmanr(x, perm)
        null_rhos[i] = r
    # 2-sided permutation p
    p = float(np.mean(np.abs(null_rhos) >= abs(rho_obs)))
    # Empirical "CI" from null distribution centered at 0; for actual CI
    # at n=8 use Fisher transform approximation
    if abs(rho_obs) < 0.999:
        z = 0.5 * np.log((1 + rho_obs) / (1 - rho_obs))
        se_z = 1.0 / np.sqrt(len(x) - 3)
        z_lo = z - 1.96 * se_z
        z_hi = z + 1.96 * se_z
        ci_lo = (np.exp(2 * z_lo) - 1) / (np.exp(2 * z_lo) + 1)
        ci_hi = (np.exp(2 * z_hi) - 1) / (np.exp(2 * z_hi) + 1)
    else:
        ci_lo, ci_hi = float("nan"), float("nan")
    return float(rho_obs), float(p), float(ci_lo), float(ci_hi)


def main() -> int:
    print("=" * 70)
    print("  LINK B EMPIRICAL TESTS")
    print("=" * 70)
    print(f"  Test B.3.1: ρ(mean entropy LEVEL, RPS) cross-market")
    print(f"  Test B.3.2: ρ(per-regime entropy SPREAD, RPS) cross-market")
    print(f"  N markets: {len(MARKETS)}; permutation iters: {N_PERM}")
    print()

    per_market = {}
    for cfg in MARKETS:
        name = cfg["name"]
        print(f"[{name}] loading + computing entropy stats...")
        try:
            out = run_full_pipeline(market=name, ticker=cfg["ticker"],
                                     source=cfg["source"], start=START, end=END)
        except Exception as e:
            print(f"  [SKIP] {type(e).__name__}: {e}")
            continue
        if len(out["raw_labels"]) < SPE_Z_WIN:
            print(f"  [SKIP] insufficient bars")
            continue
        stats = per_market_entropy_stats(out)
        stats["RPS"] = RPS[name]
        per_market[name] = stats
        print(f"  mean WPE={stats['mean_WPE']:.4f}, mean SPE_Z={stats['mean_SPE_Z']:.4f}, RPS={stats['RPS']:.2f}")

    print("\n" + "=" * 70)
    print("  CROSS-MARKET SPEARMAN TESTS")
    print("=" * 70)

    rps_arr = np.array([per_market[m]["RPS"] for m in per_market.keys()])

    # Test B.3.1: mean entropy LEVEL vs RPS
    results = {"per_market": per_market, "tests": {}}
    print("\n--- Test B.3.1: ρ(mean entropy LEVEL, RPS) ---")
    for feat_name in ["mean_WPE", "mean_SPE_Z", "median_WPE", "median_SPE_Z"]:
        x = np.array([per_market[m][feat_name] for m in per_market.keys()])
        rho, p, lo, hi = permutation_spearman_ci(x, rps_arr)
        results["tests"][f"B.3.1_{feat_name}"] = {
            "feature": feat_name, "rho": rho, "p_perm_2sided": p,
            "ci_lo_fisher": lo, "ci_hi_fisher": hi,
        }
        print(f"  ρ({feat_name}, RPS) = {rho:+.4f}  p={p:.4f}  Fisher 95% CI [{lo:+.3f}, {hi:+.3f}]")

    # Test B.3.2: per-regime SPREAD of entropy vs RPS
    print("\n--- Test B.3.2: ρ(per-regime entropy SPREAD, RPS) ---")
    for label in ["raw", "filt"]:
        for feat_name in ["WPE", "SPE_Z"]:
            spread_col = f"{label}_{feat_name}_spread"
            x = np.array([per_market[m][spread_col] for m in per_market.keys()])
            mask = ~np.isnan(x)
            if mask.sum() < 4:
                print(f"  [SKIP] {spread_col}: too many NaN")
                continue
            rho, p, lo, hi = permutation_spearman_ci(x[mask], rps_arr[mask])
            results["tests"][f"B.3.2_{spread_col}"] = {
                "spread_metric": spread_col, "n_markets": int(mask.sum()),
                "rho": rho, "p_perm_2sided": p,
                "ci_lo_fisher": lo, "ci_hi_fisher": hi,
            }
            print(f"  ρ({spread_col}, RPS) = {rho:+.4f}  p={p:.4f}  Fisher 95% CI [{lo:+.3f}, {hi:+.3f}]  n={mask.sum()}")

    print("\n" + "=" * 70)
    print("  INTERPRETATION GUIDE")
    print("=" * 70)
    print("Test B.3.1 (entropy LEVEL):")
    print("  Negative ρ → herding mechanism supported (high RPS → low entropy)")
    print("  Positive ρ → noise-decorrelation mechanism (high RPS → high entropy)")
    print("  Null ρ → Link B not visible at the entropy LEVEL aggregate")
    print()
    print("Test B.3.2 (per-regime SPREAD):")
    print("  Positive ρ → high-RPS markets have larger entropy gap between regimes")
    print("              (consistent with Link B: more discrimination on retail-dominated markets)")
    print("  Null/negative ρ → spread doesn't track RPS systematically")

    payload = {
        "spec": "Link B empirical tests on 8-market panel",
        "n_markets": len(per_market),
        "rps_panel": {m: per_market[m]["RPS"] for m in per_market.keys()},
        "n_perm": N_PERM,
        "seed": RNG_SEED,
        **results,
    }

    out_path = os.path.join(OUTPUT_DIR, "link_b_tests.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
