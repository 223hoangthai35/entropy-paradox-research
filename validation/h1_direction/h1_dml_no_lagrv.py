"""
H1 DML robustness check — rerun WITHOUT lagged realized volatility controls.

Tests whether the "developed markets flip to Paradox under DML" finding from
h1_dml.py is robust to dropping lagged RV (which may be a 'bad control' if it
mediates the regime-label → forward RV relationship).

Reduced control set: lagged returns (1, 5, 22) + lagged squared returns
(1, 5, 22) + day-of-week. NO rv22_lag1, NO rv22_lag22.

Output: validation/results_v2/h1_dml_no_lagrv.json
"""
from __future__ import annotations

import json
import os
import sys
import zlib
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

from validation._features import run_full_pipeline, SPE_Z_WIN
from validation.h1_direction.h1_dml import (
    MARKETS, START, END, PRIMARY_HORIZON, RNG_SEED, OUTPUT_DIR,
    fit_linear_dml, fit_causal_forest_dml,
)
from skills.ds_skill import REGIME_NAMES


def build_dml_dataset_no_lagrv(
    ohlcv: pd.DataFrame,
    raw_labels: pd.Series,
    horizon: int = PRIMARY_HORIZON,
) -> pd.DataFrame:
    """Same as h1_dml.build_dml_dataset but DROPS rv22 lagged controls."""
    close = ohlcv["Close"].astype(float)
    log_ret = np.log(close / close.shift(1))

    fwd_vol = (log_ret.shift(-1).rolling(horizon).std()
                       .shift(-(horizon - 1)) * np.sqrt(252) * 100.0)

    df = pd.DataFrame({
        "log_ret_lag1":  log_ret.shift(1),
        "log_ret_lag5":  log_ret.shift(5),
        "log_ret_lag22": log_ret.shift(22),
        "sq_ret_lag1":   (log_ret ** 2).shift(1),
        "sq_ret_lag5":   (log_ret ** 2).shift(5),
        "sq_ret_lag22":  (log_ret ** 2).shift(22),
        # rv22_lag1, rv22_lag22 INTENTIONALLY OMITTED
    }, index=ohlcv.index)

    dow = ohlcv.index.dayofweek
    for d, name in zip([1, 2, 3, 4], ["dow_tue", "dow_wed", "dow_thu", "dow_fri"]):
        df[name] = (dow == d).astype(float)

    df["fwd_vol"] = fwd_vol
    label_str = raw_labels.astype(int).map(REGIME_NAMES)
    df = df.join(label_str.rename("regime"))
    df = df[df["regime"].isin(["Deterministic", "Stochastic"])].copy()
    df["T"] = (df["regime"] == "Deterministic").astype(float)
    df = df.dropna()
    return df


def analyze_market(cfg: dict[str, Any]) -> dict[str, Any] | None:
    name = cfg["name"]
    print(f"\n[{name}] {cfg['ticker']} via {cfg['source']}")
    rng = np.random.default_rng(RNG_SEED + zlib.crc32((name).encode()) % 1000)

    t0 = time.time()
    try:
        out = run_full_pipeline(
            market=name, ticker=cfg["ticker"], source=cfg["source"],
            start=START, end=END,
        )
    except Exception as e:
        print(f"  [SKIP] {type(e).__name__}: {e}")
        return None

    raw_labels: pd.Series = out["raw_labels"]
    ohlcv = out["ohlcv"]
    if len(raw_labels) < SPE_Z_WIN:
        print(f"  [SKIP] insufficient bars")
        return None

    df = build_dml_dataset_no_lagrv(ohlcv, raw_labels, horizon=PRIMARY_HORIZON)
    print(f"  Reduced-controls DML obs: {len(df)} (Det={int(df['T'].sum())}, Sto={int((1-df['T']).sum())})")

    if int(df["T"].sum()) < 30 or int((1 - df["T"]).sum()) < 30:
        print(f"  [SKIP] insufficient T or control obs")
        return None

    print("  fitting LinearDML (no lagged RV)...")
    lin_res = fit_linear_dml(df, rng)
    print(f"    LinearDML: ATE = {lin_res['ate']:+.4f} ({lin_res['ci_lo']:+.4f}, {lin_res['ci_hi']:+.4f}) -> {lin_res['direction_verdict']}")

    print("  fitting CausalForestDML (no lagged RV)...")
    cf_res = fit_causal_forest_dml(df, rng)
    print(f"    CausalForestDML: ATE = {cf_res['ate']:+.4f} ({cf_res['ci_lo']:+.4f}, {cf_res['ci_hi']:+.4f}) -> {cf_res['direction_verdict']}")

    elapsed = time.time() - t0
    return {
        "market": name,
        "n_dml_obs": int(len(df)),
        "n_det": int(df["T"].sum()),
        "n_sto": int((1 - df["T"]).sum()),
        "horizon": PRIMARY_HORIZON,
        "controls": [c for c in df.columns if c not in ("fwd_vol", "T", "regime")],
        "linear_dml": lin_res,
        "causal_forest_dml": cf_res,
        "elapsed_seconds": float(elapsed),
    }


def main() -> int:
    print("=" * 70)
    print("  H1 DML ROBUSTNESS — NO LAGGED RV CONTROLS")
    print("=" * 70)
    print(f"  Reduced controls: lagged returns + lagged sq returns + DOW")
    print(f"  (Drops: rv22_lag1, rv22_lag22)")

    results = {}
    t_start = time.time()
    for cfg in MARKETS:
        res = analyze_market(cfg)
        if res is not None:
            results[cfg["name"]] = res
    total_elapsed = time.time() - t_start

    payload = {
        "spec": "H1 DML robustness without lagged RV controls",
        "n_markets": len(results),
        "horizon": PRIMARY_HORIZON,
        "seed": RNG_SEED,
        "total_elapsed_seconds": float(total_elapsed),
        "results": results,
    }
    out_path = os.path.join(OUTPUT_DIR, "h1_direction/h1_dml_no_lagrv.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    print("\n" + "=" * 70)
    print("  SUMMARY (NO LAGGED RV)")
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
