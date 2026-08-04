"""Cross-market RAW SampEn (un-Z-normed) test — Check 4 follow-up.

The Z-normalised SPE_Z measures within-market deviations from each market's
own 504-day rolling baseline. To complement this with cross-market absolute
comparison, this script re-extracts RAW SampEn (before Z-norm) per market
and tests ρ(raw SampEn level / dispersion, RPS).

Output: validation/results_v2/n27_experiment/link_b_raw_sampen_test.json
"""
from __future__ import annotations

import json
import os
import sys
import time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import (
    load_ohlcv, build_plane1_features, SPE_Z_WIN, SAMPEN_WIN,
)
from validation.markets_n27 import MARKETS_N27, CASCADE_N27
from skills.quant_skill import calc_rolling_price_sample_entropy

START = "2018-01-01"
END = "2026-04-17"
RNG_SEED = 42
N_PERM = 10_000

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2", "n27_experiment")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# n=8 panel
MARKETS_N8 = [
    {"name": "VNINDEX", "ticker": "VNINDEX", "source": "vnstock"},
    {"name": "BVB",     "ticker": "BVB:BET",  "source": "tvdatafeed"},
    {"name": "KOSPI",   "ticker": "^KS11",   "source": "yfinance"},
    {"name": "NIFTY",   "ticker": "^NSEI",   "source": "yfinance"},
    {"name": "SPX",     "ticker": "^GSPC",   "source": "yfinance"},
    {"name": "FTSE",    "ticker": "^FTSE",   "source": "yfinance"},
    {"name": "NIKKEI",  "ticker": "^N225",   "source": "yfinance"},
    {"name": "BTC",     "ticker": "BTC-USD", "source": "yfinance"},
]
RPS_N8 = {
    "VNINDEX": 0.90, "BVB": 0.225, "KOSPI": 0.45, "NIFTY": 0.40,
    "SPX": 0.275, "FTSE": 0.20, "NIKKEI": 0.18, "BTC": 0.55,
}


def cascade_point(spec):
    t = spec["type"]
    if t == "point": return float(spec["value"])
    if t == "uniform": return float(0.5*(spec["low"]+spec["high"]))
    if t == "beta": return float(spec["mean"])
    raise ValueError


def extract_raw_sampen_stats(market_def: dict) -> dict:
    """Extract per-market RAW SampEn statistics (un-Z-normed)."""
    df = load_ohlcv(market_def['name'], market_def['ticker'], market_def['source'], START, END)
    sampen = calc_rolling_price_sample_entropy(df['Close'].values, window=SAMPEN_WIN)
    sampen = sampen[~np.isnan(sampen)]
    if len(sampen) < SPE_Z_WIN:
        return {"n_obs": int(len(sampen)), "error": "too few observations"}
    # Restrict to the same labelable window (post 504-day floor for cross-comparison)
    sampen_label = sampen[SPE_Z_WIN:]
    return {
        "n_obs": int(len(sampen_label)),
        "n_total_sampen": int(len(sampen)),
        "mean_raw_SampEn": float(np.mean(sampen_label)),
        "std_raw_SampEn": float(np.std(sampen_label)),
        "median_raw_SampEn": float(np.median(sampen_label)),
        "iqr_raw_SampEn": float(np.percentile(sampen_label, 75) - np.percentile(sampen_label, 25)),
        "p95_raw_SampEn": float(np.percentile(sampen_label, 95)),
        "p05_raw_SampEn": float(np.percentile(sampen_label, 5)),
    }


def cross_market_spearman(values, rps, seed=RNG_SEED, n_perm=N_PERM):
    if np.isnan(values).any() or np.isnan(rps).any():
        valid = ~np.isnan(values) & ~np.isnan(rps)
        values = values[valid]
        rps = rps[valid]
    n = len(values)
    if n < 4:
        return {"rho": float("nan"), "p_perm_2sided": float("nan"), "n_used": n}
    rho, _ = spearmanr(values, rps)
    rho = float(rho)
    rng = np.random.default_rng(seed)
    null_rhos = np.empty(n_perm)
    for i in range(n_perm):
        permuted = rng.permutation(rps)
        null_rhos[i], _ = spearmanr(values, permuted)
    p = float(np.mean(np.abs(null_rhos) >= abs(rho)))
    return {"rho": rho, "p_perm_2sided": p, "n_used": n}


def run_panel(label, markets, rps_dict):
    print("="*78)
    print(f"PANEL: {label} (n={len(markets)})")
    print("="*78)
    per_market = {}
    failures = []
    t0 = time.time()
    for i, m in enumerate(markets, 1):
        name = m['name']
        print(f"  [{i}/{len(markets)}] {name} ...", end=" ", flush=True)
        try:
            stats = extract_raw_sampen_stats(m)
            stats['rps'] = rps_dict[name]
            per_market[name] = stats
            print(f"mean_SampEn={stats['mean_raw_SampEn']:.3f}  std={stats['std_raw_SampEn']:.3f}")
        except Exception as e:
            print(f"FAIL: {type(e).__name__}: {str(e)[:80]}")
            failures.append({"market": name, "error": str(e)[:200]})
    print(f"  Elapsed: {time.time()-t0:.1f}s. Successful: {len(per_market)}/{len(markets)}")

    names = list(per_market.keys())
    rps_arr = np.array([per_market[n]['rps'] for n in names])

    metrics = ['mean_raw_SampEn', 'std_raw_SampEn', 'median_raw_SampEn', 'iqr_raw_SampEn',
               'p95_raw_SampEn', 'p05_raw_SampEn']
    tests = {}
    print(f"\n  Cross-market Spearman ρ(<raw metric>, RPS):")
    for k in metrics:
        vals = np.array([per_market[n][k] for n in names])
        result = cross_market_spearman(vals, rps_arr)
        tests[k] = result
        rho = result['rho']
        p = result['p_perm_2sided']
        verdict = "DECISIVE" if (not np.isnan(p) and p < 0.05) else ("BORDERLINE" if (not np.isnan(p) and p < 0.10) else "n.s.")
        print(f"    {k:<22}  ρ = {rho:+.4f}  p = {p:.4f}  [{verdict}]")

    return {"panel": label, "n_markets": len(markets), "per_market": per_market,
            "tests": tests, "failures": failures}


def main():
    print("="*78)
    print("RAW SampEn cross-market test (un-Z-normed)")
    print("="*78)
    print()

    out = {"spec": "RAW SampEn cross-market test (un-Z-normed)", "panels": {}}

    out["panels"]["n8"] = run_panel("n=8 main panel", MARKETS_N8, RPS_N8)
    print()

    rps_n27 = {m['name']: cascade_point(CASCADE_N27[m['name']]) for m in MARKETS_N27}
    out["panels"]["n27"] = run_panel("n=27 expansion panel", MARKETS_N27, rps_n27)

    out_path = os.path.join(OUTPUT_DIR, "link_b_raw_sampen_test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nJSON: {out_path}")

    print("\n" + "="*78)
    print("SUMMARY — RAW SampEn × RPS sign-consistency check")
    print("="*78)
    print(f"  {'Metric':<22}{'n=8 ρ':>10}{'n=8 p':>9}{'n=27 ρ':>10}{'n=27 p':>9}{'consistent?':>14}")
    for k in ['mean_raw_SampEn', 'std_raw_SampEn', 'median_raw_SampEn', 'iqr_raw_SampEn',
              'p95_raw_SampEn', 'p05_raw_SampEn']:
        n8 = out["panels"]["n8"]["tests"][k]
        n27 = out["panels"]["n27"]["tests"][k]
        consistent = "YES" if (np.sign(n8['rho']) == np.sign(n27['rho'])) else "FLIP"
        print(f"  {k:<22}{n8['rho']:>+10.3f}{n8['p_perm_2sided']:>9.3f}{n27['rho']:>+10.3f}{n27['p_perm_2sided']:>9.3f}{consistent:>14}")


if __name__ == "__main__":
    main()
