"""
H1 DML on the n=27 expansion panel (NOT canonical paper analysis).

Same canonical specification as h1_dml_cpcv.py:
  - Filtered Schmitt-trigger labels
  - PurgedKFold (K=5, embargo=20)
  - LinearDML + BootstrapInference + CausalForestDML + asymptotic CI

Difference: uses MARKETS_N27 (27 markets) instead of paper canonical 8.

Markets that fail data fetch (yfinance ticker invalid, insufficient bars after
504-day SPE_Z floor, or treatment-balance failure) are skipped with logging
rather than crashing the whole panel.

Output: validation/results_v2/n27_experiment/h1_dml_cpcv_n27.json

Usage:
    python validation/h1_dml_cpcv_n27.py

Estimated runtime: ~80 minutes (depends on actual market success rate after
data-fetch failures; H1 fitting per market ~3 min on canonical 8 panel).
"""
from __future__ import annotations

import json
import os
import sys
import zlib
import time
import warnings

import numpy as np

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from validation._features import run_full_pipeline, SPE_Z_WIN
from validation.h1_direction.h1_dml import (
    START, END, PRIMARY_HORIZON, RNG_SEED, build_dml_dataset,
)
from validation.h1_direction.h1_dml_cpcv import (
    fit_linear_dml_cpcv, fit_causal_forest_dml_cpcv,
    PKF_N_SPLITS, PKF_EMBARGO, N_BOOTSTRAP,
)
from validation.markets_n27 import MARKETS_N27, panel_summary

OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2", "n27_experiment")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def analyze_market(cfg: dict) -> dict | None:
    name = cfg["name"]
    print(f"\n[{name}] {cfg['ticker']} via {cfg['source']} ({cfg['category']})")
    rng = np.random.default_rng(RNG_SEED + zlib.crc32((name).encode()) % 1000)

    t0 = time.time()
    try:
        out = run_full_pipeline(market=name, ticker=cfg["ticker"], source=cfg["source"], start=START, end=END)
    except Exception as e:
        print(f"  [SKIP-fetch] {type(e).__name__}: {e}")
        return {"market": name, "skip_reason": f"fetch_failed: {type(e).__name__}: {e}"}

    filt_labels = out.get("filtered_labels")
    if filt_labels is None or len(filt_labels) < SPE_Z_WIN:
        print(f"  [SKIP-bars] insufficient bars after SPE_Z floor")
        return {"market": name, "skip_reason": "insufficient_bars"}

    df = build_dml_dataset(out["ohlcv"], filt_labels, horizon=PRIMARY_HORIZON)
    n_det = int(df["T"].sum())
    n_sto = int((1 - df["T"]).sum())
    if n_det < 30 or n_sto < 30:
        print(f"  [SKIP-balance] n_det={n_det}, n_sto={n_sto} (need >=30 each)")
        return {"market": name, "skip_reason": f"insufficient_treatment_balance: det={n_det}, sto={n_sto}"}

    print(f"  obs: {len(df)} (Det={n_det}, Sto={n_sto})")
    print(f"  PurgedKFold: K={PKF_N_SPLITS}, embargo={PKF_EMBARGO}")

    print("  fitting LinearDML + PurgedKFold + Bootstrap...")
    lin_res = fit_linear_dml_cpcv(df, rng)
    print(f"    ATE = {lin_res['ate']:+.4f} ({lin_res.get('ci_lo', 'NaN'):+.4f}, {lin_res.get('ci_hi', 'NaN'):+.4f}) -> {lin_res['direction_verdict']}")

    print("  fitting CausalForestDML + PurgedKFold...")
    cf_res = fit_causal_forest_dml_cpcv(df, rng)
    print(f"    ATE = {cf_res['ate']:+.4f} ({cf_res.get('ci_lo', 'NaN'):+.4f}, {cf_res.get('ci_hi', 'NaN'):+.4f}) -> {cf_res['direction_verdict']}")

    elapsed = time.time() - t0
    print(f"  elapsed: {elapsed:.1f}s")
    return {
        "market": name,
        "category": cfg["category"],
        "tier_rank": cfg["tier_rank"],
        "label_source": "filtered_schmitt_trigger",
        "n_dml_obs": int(len(df)),
        "n_det": n_det,
        "n_sto": n_sto,
        "horizon": PRIMARY_HORIZON,
        "purged_kfold_config": {"n_splits": PKF_N_SPLITS, "embargo": PKF_EMBARGO},
        "linear_dml": lin_res,
        "causal_forest_dml": cf_res,
        "elapsed_seconds": float(elapsed),
    }


def main() -> int:
    print("=" * 70)
    print("  H1 DML CANONICAL SPEC — n=27 EXPANSION PANEL")
    print("=" * 70)
    print(panel_summary())
    print()
    print(f"  Cross-fitting: PurgedKFold (K={PKF_N_SPLITS}, embargo={PKF_EMBARGO})")
    print(f"  LinearDML inference: BootstrapInference (n_boot={N_BOOTSTRAP})")
    print(f"  CausalForestDML inference: asymptotic")

    results: dict[str, dict] = {}
    skipped: list[dict] = []
    t_start = time.time()
    for cfg in MARKETS_N27:
        res = analyze_market(cfg)
        if res is None:
            continue
        if "skip_reason" in res:
            skipped.append(res)
            continue
        results[cfg["name"]] = res
    total_elapsed = time.time() - t_start

    payload = {
        "spec": "H1 DML canonical (filtered + PurgedKFold) on n=27 expansion panel",
        "panel": "n27_experiment (MSCI Frontier 8 + Emerging 8 + Developed 8 + Crypto 3)",
        "n_markets_attempted": len(MARKETS_N27),
        "n_markets_succeeded": len(results),
        "n_markets_skipped": len(skipped),
        "horizon": PRIMARY_HORIZON,
        "purged_kfold": {"n_splits": PKF_N_SPLITS, "embargo": PKF_EMBARGO},
        "n_bootstrap": N_BOOTSTRAP,
        "seed": RNG_SEED,
        "total_elapsed_seconds": float(total_elapsed),
        "skipped_markets": skipped,
        "results": results,
    }
    out_path = os.path.join(OUTPUT_DIR, "h1_dml_cpcv_n27.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    print("\n" + "=" * 70)
    print(f"  SUMMARY (n={len(results)} succeeded, {len(skipped)} skipped)")
    print("=" * 70)
    print(f"  {'market':<10}  {'cat':<10}  {'CF DML ATE [95% CI]':<32}  verdict")
    for m, r in sorted(results.items(), key=lambda kv: (-kv[1]["tier_rank"], kv[0])):
        cf = r["causal_forest_dml"]
        if cf.get("fit_status") == "ok":
            print(f"  {m:<10}  {r['category']:<10}  {cf['ate']:+7.3f} [{cf['ci_lo']:+6.2f}, {cf['ci_hi']:+6.2f}]    {cf['direction_verdict']}")
        else:
            print(f"  {m:<10}  {r['category']:<10}  [FAIL]")
    if skipped:
        print()
        print(f"  Skipped: {[s['market'] + ' (' + s['skip_reason'].split(':')[0] + ')' for s in skipped]}")

    print(f"\n  Total elapsed: {total_elapsed:.1f}s")
    print(f"  JSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
