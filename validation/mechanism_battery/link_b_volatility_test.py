"""Volatility-driven SPE_Z deviation test (user-specified hypothesis).

User hypothesis: high RPS → stronger fluctuations RELATIVE TO each market's own
historical baseline. This is methodologically distinct from the Link B
coordination hypothesis (which predicts low entropy LEVEL, not high deviation).

Z-normalised SPE_Z is the right framework here because each market's SPE_Z
is scored against its OWN rolling 504-day history. Deviation magnitude
metrics (std, mean|·|, tail frequency) cross-market then directly test
'this market deviates from its norm more often / more strongly'.

Tests run on n=8 main panel + n=27 expansion:
  - ρ(per-market std(SPE_Z), RPS) — dispersion test
  - ρ(per-market mean|SPE_Z|, RPS) — average deviation magnitude test
  - ρ(per-market % bars with |SPE_Z| > 1.5, RPS) — tail frequency test
  - ρ(per-market p95(SPE_Z), RPS) — extreme positive deviation test

All four expected POSITIVE under volatility hypothesis. Multiple metrics
triangulate signal-vs-noise.

Output: validation/results_v2/n27_experiment/link_b_volatility_test.json
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

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from validation._features import run_full_pipeline
from validation.markets_n27 import MARKETS_N27, CASCADE_N27

START = "2018-01-01"
END = "2026-06-30"
RNG_SEED = 42
N_PERM = 10_000

# n=8 panel (canonical)
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

OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2", "n27_experiment")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def cascade_point_value(spec: dict) -> float:
    t = spec["type"]
    if t == "point":
        return float(spec["value"])
    if t == "uniform":
        return float(0.5 * (spec["low"] + spec["high"]))
    if t == "beta":
        return float(spec["mean"])
    raise ValueError(f"Unknown cascade type: {t}")


def compute_dispersion_metrics(out: dict[str, Any]) -> dict[str, float]:
    """Per-market SPE_Z dispersion metrics for volatility hypothesis."""
    feat: pd.DataFrame = out["features"]
    spe = feat["SPE_Z"].values
    spe_clean = spe[~np.isnan(spe)]

    return {
        "n_obs": int(len(spe_clean)),
        "mean_SPE_Z": float(np.mean(spe_clean)),
        "std_SPE_Z": float(np.std(spe_clean)),
        "mean_abs_SPE_Z": float(np.mean(np.abs(spe_clean))),
        "p95_SPE_Z": float(np.percentile(spe_clean, 95)),
        "p99_SPE_Z": float(np.percentile(spe_clean, 99)),
        "frac_extreme_1p5": float(np.mean(np.abs(spe_clean) > 1.5)),
        "frac_extreme_2p0": float(np.mean(np.abs(spe_clean) > 2.0)),
        "iqr_SPE_Z": float(np.percentile(spe_clean, 75) - np.percentile(spe_clean, 25)),
        # Also include WPE for cross-comparison
        "mean_WPE": float(feat["WPE"].mean()),
        "std_WPE": float(feat["WPE"].std()),
    }


def cross_market_spearman(values: np.ndarray, rps: np.ndarray, seed: int = RNG_SEED, n_perm: int = N_PERM) -> dict:
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
    p_perm = float(np.mean(np.abs(null_rhos) >= abs(rho)))
    if abs(rho) >= 1:
        ci_lo = ci_hi = float(rho)
    else:
        z = 0.5 * np.log((1 + rho) / (1 - rho))
        se = 1.0 / np.sqrt(n - 3)
        z_lo = z - 1.96 * se
        z_hi = z + 1.96 * se
        ci_lo = float((np.exp(2 * z_lo) - 1) / (np.exp(2 * z_lo) + 1))
        ci_hi = float((np.exp(2 * z_hi) - 1) / (np.exp(2 * z_hi) + 1))
    return {
        "rho": rho,
        "p_perm_2sided": p_perm,
        "ci_lo_fisher": ci_lo,
        "ci_hi_fisher": ci_hi,
        "n_used": n,
    }


def run_panel(panel_label: str, markets_list: list[dict], rps_dict: dict[str, float]):
    print("=" * 70)
    print(f"PANEL: {panel_label}  (n = {len(markets_list)})")
    print("=" * 70)

    per_market = {}
    failures = []
    t0 = time.time()
    for i, m in enumerate(markets_list, 1):
        name = m["name"]
        print(f"  [{i}/{len(markets_list)}] {name} ...", end=" ", flush=True)
        try:
            out = run_full_pipeline(market=name, ticker=m["ticker"], source=m["source"],
                                    start=START, end=END, random_state=RNG_SEED)
            metrics = compute_dispersion_metrics(out)
            metrics["rps"] = rps_dict[name]
            per_market[name] = metrics
            print(f"std={metrics['std_SPE_Z']:.3f}  mean|·|={metrics['mean_abs_SPE_Z']:.3f}  p95={metrics['p95_SPE_Z']:.2f}")
        except Exception as e:
            print(f"FAIL: {type(e).__name__}: {str(e)[:80]}")
            failures.append({"market": name, "error": f"{type(e).__name__}: {str(e)[:200]}"})
    print(f"  Elapsed: {time.time() - t0:.1f}s. Successful: {len(per_market)}/{len(markets_list)}")

    # Cross-market tests
    names = list(per_market.keys())
    rps_arr = np.array([per_market[n]["rps"] for n in names])

    metrics_to_test = [
        ("std_SPE_Z", "Dispersion (std of SPE_Z)"),
        ("mean_abs_SPE_Z", "Average deviation magnitude (mean |SPE_Z|)"),
        ("p95_SPE_Z", "95th percentile (extreme positive deviation)"),
        ("p99_SPE_Z", "99th percentile (extreme positive deviation)"),
        ("frac_extreme_1p5", "Frequency of |SPE_Z| > 1.5 events"),
        ("frac_extreme_2p0", "Frequency of |SPE_Z| > 2.0 events"),
        ("iqr_SPE_Z", "Interquartile range (robust dispersion)"),
        ("mean_SPE_Z", "(comparison) Mean SPE_Z — wrong metric for volatility"),
        ("mean_WPE", "(comparison) Mean WPE — Link B coordination test"),
    ]

    tests = {}
    for metric_key, description in metrics_to_test:
        vals = np.array([per_market[n][metric_key] for n in names])
        result = cross_market_spearman(vals, rps_arr)
        tests[metric_key] = {"description": description, **result}

    print(f"\n  Cross-market Spearman ρ(<metric>, RPS):")
    print(f"  {'Metric':<22}{'ρ':>9}{'p':>9}{'CI 95%':>22}{'verdict':>14}")
    for k, t in tests.items():
        rho = t["rho"]
        p = t["p_perm_2sided"]
        ci = f"[{t['ci_lo_fisher']:+.3f}, {t['ci_hi_fisher']:+.3f}]"
        verdict = "DECISIVE" if (not np.isnan(p) and p < 0.05) else ("BORDERLINE" if (not np.isnan(p) and p < 0.10) else "n.s.")
        print(f"  {k:<22}{rho:>+9.4f}{p:>9.4f}{ci:>22}{verdict:>14}")

    return {"panel": panel_label, "n_markets": len(markets_list), "n_successful": len(per_market),
            "rps_panel": {n: float(per_market[n]["rps"]) for n in names},
            "per_market": per_market, "tests": tests, "failures": failures,
            "elapsed_seconds": float(time.time() - t0)}


def main():
    print("=" * 78)
    print("VOLATILITY-DRIVEN SPE_Z DEVIATION TEST")
    print("Hypothesis: RPS → stronger deviations from market's own historical baseline")
    print("Expected: ρ(dispersion metric, RPS) > 0 (POSITIVE)")
    print("=" * 78)
    print()

    out = {
        "spec": "Volatility-driven SPE_Z deviation test (user-specified hypothesis)",
        "hypothesis": "high RPS → larger deviations from market's own historical SPE_Z baseline; expected positive cross-market correlation",
        "panels": {},
    }

    # n=8 panel
    out["panels"]["n8"] = run_panel("n=8 main panel", MARKETS_N8, RPS_N8)
    print()

    # n=27 panel
    rps_n27 = {m["name"]: cascade_point_value(CASCADE_N27[m["name"]]) for m in MARKETS_N27}
    out["panels"]["n27"] = run_panel("n=27 expansion panel", MARKETS_N27, rps_n27)

    # Save
    out_path = os.path.join(OUTPUT_DIR, "link_b_volatility_test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nJSON: {out_path}")

    # Summary
    print("\n" + "=" * 78)
    print("SUMMARY (volatility hypothesis: expected ρ > 0)")
    print("=" * 78)
    print(f"  {'Metric':<22}{'n=8 ρ':>9}{'n=8 p':>9}{'n=27 ρ':>9}{'n=27 p':>9}{'consistent?':>14}")
    for metric_key, _ in [("std_SPE_Z", ""), ("mean_abs_SPE_Z", ""), ("p95_SPE_Z", ""),
                          ("frac_extreme_1p5", ""), ("frac_extreme_2p0", ""), ("iqr_SPE_Z", ""),
                          ("mean_SPE_Z", ""), ("mean_WPE", "")]:
        n8_rho = out["panels"]["n8"]["tests"][metric_key]["rho"]
        n8_p = out["panels"]["n8"]["tests"][metric_key]["p_perm_2sided"]
        n27_rho = out["panels"]["n27"]["tests"][metric_key]["rho"]
        n27_p = out["panels"]["n27"]["tests"][metric_key]["p_perm_2sided"]
        consistent = "YES" if (np.sign(n8_rho) == np.sign(n27_rho)) else "FLIP"
        print(f"  {metric_key:<22}{n8_rho:>+9.3f}{n8_p:>9.3f}{n27_rho:>+9.3f}{n27_p:>9.3f}{consistent:>14}")


if __name__ == "__main__":
    main()
