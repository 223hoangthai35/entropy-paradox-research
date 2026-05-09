"""
H1 DML on FILTERED (Schmitt-trigger) labels — companion to h1_dml.py (raw labels).

Tests whether DML estimates differ when treatment T uses filtered regime
labels (production-deployment-relevant) versus raw GMM argmax (current
h1_dml.py default).

Filtered labels apply the K-state Schmitt-trigger hysteresis filter
(production parameters delta_hard=0.60, delta_soft=0.35, t_persist=8) to
the raw GMM posterior probability sequence. Per the paper's Hybrid-C
structure, filtered labels are the Principal Contribution 2 deployment
artifact; if DML estimates differ between raw and filtered, this is
methodologically important.

Output: validation/results_v2/h1_dml_filtered.json
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import run_full_pipeline, SPE_Z_WIN
from validation.h1_dml import (
    MARKETS, START, END, PRIMARY_HORIZON, RNG_SEED, OUTPUT_DIR,
    build_dml_dataset, fit_linear_dml, fit_causal_forest_dml,
)


def analyze_market(cfg: dict[str, Any]) -> dict[str, Any] | None:
    name = cfg["name"]
    print(f"\n[{name}] {cfg['ticker']} via {cfg['source']}")
    rng = np.random.default_rng(RNG_SEED + hash(name) % 1000)

    t0 = time.time()
    try:
        out = run_full_pipeline(market=name, ticker=cfg["ticker"], source=cfg["source"], start=START, end=END)
    except Exception as e:
        print(f"  [SKIP] {type(e).__name__}: {e}")
        return None

    # KEY DIFFERENCE: use filtered_labels, not raw_labels
    filt_labels = out["filtered_labels"]
    if len(filt_labels) < SPE_Z_WIN:
        print(f"  [SKIP] insufficient bars")
        return None

    df = build_dml_dataset(out["ohlcv"], filt_labels, horizon=PRIMARY_HORIZON)
    if int(df["T"].sum()) < 30 or int((1 - df["T"]).sum()) < 30:
        print(f"  [SKIP] insufficient T or control obs (Det={int(df['T'].sum())}, Sto={int((1-df['T']).sum())})")
        return None

    print(f"  filtered DML obs: {len(df)} (Det={int(df['T'].sum())}, Sto={int((1-df['T']).sum())})")
    print("  fitting LinearDML on filtered labels...")
    lin_res = fit_linear_dml(df, rng)
    print(f"    LinearDML: ATE = {lin_res['ate']:+.4f} ({lin_res['ci_lo']:+.4f}, {lin_res['ci_hi']:+.4f}) -> {lin_res['direction_verdict']}")
    print("  fitting CausalForestDML on filtered labels...")
    cf_res = fit_causal_forest_dml(df, rng)
    print(f"    CausalForestDML: ATE = {cf_res['ate']:+.4f} ({cf_res['ci_lo']:+.4f}, {cf_res['ci_hi']:+.4f}) -> {cf_res['direction_verdict']}")

    elapsed = time.time() - t0
    print(f"  elapsed: {elapsed:.1f}s")
    return {
        "market": name,
        "label_source": "filtered_schmitt_trigger",
        "n_dml_obs": int(len(df)),
        "n_det": int(df["T"].sum()),
        "n_sto": int((1 - df["T"]).sum()),
        "horizon": PRIMARY_HORIZON,
        "linear_dml": lin_res,
        "causal_forest_dml": cf_res,
        "elapsed_seconds": float(elapsed),
    }


def main() -> int:
    print("=" * 70)
    print("  H1 DML ON FILTERED LABELS (Schmitt-trigger applied)")
    print("=" * 70)

    results = {}
    t_start = time.time()
    for cfg in MARKETS:
        res = analyze_market(cfg)
        if res is not None:
            results[cfg["name"]] = res
    total_elapsed = time.time() - t_start

    payload = {
        "spec": "H1 DML on filtered (Schmitt-trigger) regime labels",
        "n_markets": len(results),
        "horizon": PRIMARY_HORIZON,
        "seed": RNG_SEED,
        "total_elapsed_seconds": float(total_elapsed),
        "results": results,
    }
    out_path = os.path.join(OUTPUT_DIR, "h1_dml_filtered.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    print("\n" + "=" * 70)
    print("  SUMMARY (FILTERED LABELS)")
    print("=" * 70)
    print(f"  {'market':<10}  {'LinearDML ATE':<22}  {'CausalForest ATE':<22}")
    for m, r in results.items():
        lin = r["linear_dml"]
        cf = r["causal_forest_dml"]
        lin_str = f"{lin['ate']:+.3f} -> {lin['direction_verdict']:<8}" if lin["fit_status"] == "ok" else "[FAIL]"
        cf_str  = f"{cf['ate']:+.3f} -> {cf['direction_verdict']:<8}" if cf["fit_status"] == "ok" else "[FAIL]"
        print(f"  {m:<10}  {lin_str:<22}  {cf_str:<22}")

    print(f"\n  Total elapsed: {total_elapsed:.1f}s")
    print(f"  JSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
