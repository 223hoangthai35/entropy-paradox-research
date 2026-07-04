"""Link B empirical tests on the n=27 expansion panel.

Tests Link B (cross-market entropy LEVEL ↔ RPS) on the expanded panel.
Mirrors `link_b_tests.py` (n=8) but uses the n=27 markets list and
RPS values from `markets_n27.py` cascade specification.

Power note: at n=27, Spearman ρ critical value at α=0.05 (two-sided) is
|ρ| ≈ 0.39 — substantially lower than the |ρ| > 0.71 required at n=8.
A direction-consistent magnitude of |ρ| ≈ 0.4–0.5 (the n=8 estimate)
is expected to clear decisiveness on this expanded panel.

Output: validation/results_v2/n27_experiment/link_b_tests_n27.json
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
from validation.markets_n27 import MARKETS_N27, CASCADE_N27
from skills.ds_skill import REGIME_NAMES

START = "2018-01-01"
END = "2026-04-17"
RNG_SEED = 42
N_PERM = 10_000

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2", "n27_experiment")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def cascade_point_value(cascade_spec: dict) -> float:
    """Convert cascade RPS specification to a single point estimate.

    P1 point: return value
    P2 uniform: return midpoint
    P3 beta: return mean
    """
    t = cascade_spec["type"]
    if t == "point":
        return float(cascade_spec["value"])
    if t == "uniform":
        return float(0.5 * (cascade_spec["low"] + cascade_spec["high"]))
    if t == "beta":
        return float(cascade_spec["mean"])
    raise ValueError(f"Unknown cascade type: {t}")


def per_market_entropy_stats(out: dict[str, Any]) -> dict[str, Any]:
    """Compute mean(WPE), mean(SPE_Z) per market + per-regime breakdown."""
    feat: pd.DataFrame = out["features"]
    raw_labels: pd.Series = out["raw_labels"]
    filt_labels: pd.Series = out["filtered_labels"]

    overall = {
        "n_obs": int(len(feat)),
        "mean_WPE": float(feat["WPE"].mean()),
        "mean_SPE_Z": float(feat["SPE_Z"].mean()),
        "median_WPE": float(feat["WPE"].median()),
        "median_SPE_Z": float(feat["SPE_Z"].median()),
    }

    raw_arr = raw_labels.astype(int).map(REGIME_NAMES).values
    filt_arr = filt_labels.astype(int).map(REGIME_NAMES).values

    def regime_means(label_arr, label_name):
        out_dict = {}
        for regime in ("Deterministic", "Transitional", "Stochastic"):
            mask = (label_arr == regime)
            if mask.sum() < 5:
                out_dict[f"{regime}_mean_WPE"] = float("nan")
                out_dict[f"{regime}_mean_SPE_Z"] = float("nan")
                out_dict[f"{regime}_n"] = int(mask.sum())
                continue
            out_dict[f"{regime}_mean_WPE"] = float(feat["WPE"].values[mask].mean())
            out_dict[f"{regime}_mean_SPE_Z"] = float(feat["SPE_Z"].values[mask].mean())
            out_dict[f"{regime}_n"] = int(mask.sum())
        return out_dict

    overall["raw"] = regime_means(raw_arr, "raw")
    overall["filtered"] = regime_means(filt_arr, "filtered")
    return overall


def cross_market_spearman(values: np.ndarray, rps: np.ndarray, seed: int = RNG_SEED, n_perm: int = N_PERM) -> dict:
    """Spearman ρ + permutation 2-sided p + Fisher z-transform 95% CI."""
    if np.isnan(values).any() or np.isnan(rps).any():
        valid = ~np.isnan(values) & ~np.isnan(rps)
        values = values[valid]
        rps = rps[valid]
    n = len(values)
    if n < 4:
        return {"rho": float("nan"), "p_perm_2sided": float("nan"), "n_used": n}
    rho, _ = spearmanr(values, rps)
    rho = float(rho)

    # Permutation p (2-sided)
    rng = np.random.default_rng(seed)
    null_rhos = np.empty(n_perm)
    for i in range(n_perm):
        permuted = rng.permutation(rps)
        null_rhos[i], _ = spearmanr(values, permuted)
    p_perm = float(np.mean(np.abs(null_rhos) >= abs(rho)))

    # Fisher z-transform 95% CI
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


def main():
    print("=" * 70)
    print("LINK B TEST — n=27 EXPANSION PANEL")
    print("=" * 70)
    print(f"Markets: {len(MARKETS_N27)}")
    print(f"Permutation iterations: {N_PERM}")
    print(f"Random seed: {RNG_SEED}")
    print()

    per_market = {}
    failures = []
    t_start = time.time()

    for i, m in enumerate(MARKETS_N27, 1):
        name = m["name"]
        print(f"[{i}/{len(MARKETS_N27)}] {name} ({m['ticker']}) ...", end=" ", flush=True)
        try:
            out = run_full_pipeline(
                market=name, ticker=m["ticker"], source=m["source"],
                start=START, end=END, random_state=RNG_SEED,
            )
            stats = per_market_entropy_stats(out)
            stats["category"] = m["category"]
            stats["tier_rank"] = m["tier_rank"]
            stats["rps"] = cascade_point_value(CASCADE_N27[name])
            per_market[name] = stats
            print(f"OK ({stats['n_obs']} bars, mean_WPE={stats['mean_WPE']:.4f})")
        except Exception as e:
            print(f"FAIL: {type(e).__name__}: {str(e)[:80]}")
            failures.append({"market": name, "error": f"{type(e).__name__}: {str(e)[:200]}"})

    print(f"\nElapsed: {time.time() - t_start:.1f}s")
    print(f"Successful: {len(per_market)}/{len(MARKETS_N27)}, failures: {len(failures)}")

    # Cross-market Spearman tests
    names = list(per_market.keys())
    rps_arr = np.array([per_market[n]["rps"] for n in names])

    tests = {}

    # Test B.5.1 — entropy LEVEL
    for feature in ["mean_WPE", "median_WPE", "mean_SPE_Z", "median_SPE_Z"]:
        vals = np.array([per_market[n][feature] for n in names])
        result = cross_market_spearman(vals, rps_arr)
        tests[f"B.5.1_{feature}"] = {
            "feature": feature,
            **result,
        }

    # Test B.5.2 — per-regime entropy spread
    for label_src in ["raw", "filtered"]:
        for feature_base in ["mean_WPE", "mean_SPE_Z"]:
            spreads = []
            for n in names:
                regime_data = per_market[n][label_src]
                vals = [regime_data.get(f"{r}_{feature_base}", float("nan"))
                        for r in ("Deterministic", "Transitional", "Stochastic")]
                vals = [v for v in vals if not np.isnan(v)]
                spread = float(max(vals) - min(vals)) if len(vals) >= 2 else float("nan")
                spreads.append(spread)
            spreads = np.array(spreads)
            result = cross_market_spearman(spreads, rps_arr)
            tests[f"B.5.2_{label_src}_{feature_base.replace('mean_', '')}_spread"] = {
                "spread_metric": f"{label_src}_{feature_base}",
                **result,
            }

    # Print summary
    print("\n" + "=" * 70)
    print("LINK B TEST B.5.1 — Entropy LEVEL × RPS (cross-market Spearman)")
    print("=" * 70)
    for k, t in tests.items():
        if not k.startswith("B.5.1"):
            continue
        rho = t.get("rho", float("nan"))
        p = t.get("p_perm_2sided", float("nan"))
        ci_lo = t.get("ci_lo_fisher", float("nan"))
        ci_hi = t.get("ci_hi_fisher", float("nan"))
        n_used = t.get("n_used", 0)
        verdict = "DECISIVE" if (not np.isnan(p) and p < 0.05) else ("BORDERLINE" if (not np.isnan(p) and p < 0.10) else "n.s.")
        print(f"  {t['feature']:<14} ρ = {rho:+.4f}  p = {p:.4f}  CI = [{ci_lo:+.3f}, {ci_hi:+.3f}]  n = {n_used}  [{verdict}]")

    print("\n" + "=" * 70)
    print("LINK B TEST B.5.2 — per-regime entropy spread × RPS")
    print("=" * 70)
    for k, t in tests.items():
        if not k.startswith("B.5.2"):
            continue
        rho = t.get("rho", float("nan"))
        p = t.get("p_perm_2sided", float("nan"))
        n_used = t.get("n_used", 0)
        verdict = "DECISIVE" if (not np.isnan(p) and p < 0.05) else "n.s."
        print(f"  {t['spread_metric']:<32} ρ = {rho:+.4f}  p = {p:.4f}  n = {n_used}  [{verdict}]")

    # Output
    output = {
        "spec": "Link B empirical tests on n=27 panel",
        "n_markets": len(MARKETS_N27),
        "n_successful": len(per_market),
        "rps_panel": {n: float(per_market[n]["rps"]) for n in names},
        "n_perm": N_PERM,
        "seed": RNG_SEED,
        "per_market": per_market,
        "tests": tests,
        "failures": failures,
        "elapsed_seconds": float(time.time() - t_start),
    }

    out_path = os.path.join(OUTPUT_DIR, "link_b_tests_n27.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nJSON: {out_path}")


if __name__ == "__main__":
    main()
