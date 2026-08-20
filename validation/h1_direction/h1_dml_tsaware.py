"""
H1 DML — time-series-aware variant.

Two fixes vs h1_dml.py:

1. Cross-fitting splitter = TimeSeriesSplit (forward-chaining), NOT KFold
   (sklearn KFold splits data into K contiguous chunks; in fold k, train on
   the other K-1 chunks INCLUDING chunks AFTER chunk k => future data leaks
   into past predictions. TimeSeriesSplit only uses past data.)

2. Inference = BootstrapInference (resample-based CIs), NOT asymptotic
   (asymptotic CI assumes IID residuals; forward 20-day RV creates 19-bar
   overlap => CIs too narrow under asymptotic. Bootstrap is more robust
   to misspecification, even though econml's IID bootstrap still does not
   model block autocorrelation perfectly.)

Note on remaining limitation: econml's BootstrapInference does IID
resampling at the row level; for full time-series correctness, a
circular block bootstrap at the index level would be ideal but requires
a custom implementation outside econml. This script trades off some
correctness for tractability — the IID bootstrap is still meaningfully
better than asymptotic SE because it does not assume any parametric
form for the residual distribution.

Output: validation/results_v2/h1_dml_tsaware.json
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

from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from econml.dml import LinearDML, CausalForestDML
from econml.inference import BootstrapInference

from validation._features import run_full_pipeline, SPE_Z_WIN
from validation.h1_direction.h1_dml import (
    MARKETS, START, END, PRIMARY_HORIZON, RNG_SEED, OUTPUT_DIR,
    build_dml_dataset,
)

N_TS_SPLITS = 5            # forward-chaining folds
N_BOOTSTRAP = 100          # bootstrap resamples for CI
RNG_BASE = RNG_SEED


def fit_linear_dml_tsaware(df: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    """LinearDML with TimeSeriesSplit + bootstrap inference."""
    feature_cols = [c for c in df.columns if c not in ("fwd_vol", "T", "regime")]
    Y = df["fwd_vol"].values
    T = df["T"].values
    X = df[feature_cols].values

    seed = int(rng.integers(0, 2**31 - 1))
    ts_splitter = TimeSeriesSplit(n_splits=N_TS_SPLITS)

    model = LinearDML(
        model_y=RandomForestRegressor(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        model_t=RandomForestClassifier(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        discrete_treatment=True,
        cv=ts_splitter,
        random_state=seed,
    )
    try:
        model.fit(Y, T, X=X, W=None,
                  inference=BootstrapInference(n_bootstrap_samples=N_BOOTSTRAP, n_jobs=-1))
        ate = float(model.ate(X))
        ate_lo, ate_hi = model.ate_interval(X, alpha=0.05)
        ate_lo, ate_hi = float(ate_lo), float(ate_hi)
        se = float((ate_hi - ate_lo) / (2 * 1.959963984540054))
        if ate_lo > 0:
            verdict = "Paradox"
        elif ate_hi < 0:
            verdict = "Inverted"
        else:
            verdict = "n.s."
        return {
            "spec": "LinearDML+TSSplit+Bootstrap",
            "ate": ate, "se": se, "ci_lo": ate_lo, "ci_hi": ate_hi,
            "direction_verdict": verdict,
            "n_obs": int(len(df)),
            "n_det": int(df["T"].sum()),
            "n_sto": int((1 - df["T"]).sum()),
            "fit_status": "ok",
        }
    except Exception as e:
        return {
            "spec": "LinearDML+TSSplit+Bootstrap",
            "fit_status": f"error: {type(e).__name__}: {e}",
            "ate": float("nan"), "se": float("nan"),
            "ci_lo": float("nan"), "ci_hi": float("nan"),
            "direction_verdict": "SKIP", "n_obs": int(len(df)),
        }


def fit_causal_forest_dml_tsaware(df: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    """CausalForestDML with TimeSeriesSplit (bootstrap not supported in built-in inference)."""
    feature_cols = [c for c in df.columns if c not in ("fwd_vol", "T", "regime")]
    Y = df["fwd_vol"].values
    T = df["T"].values
    X = df[feature_cols].values

    seed = int(rng.integers(0, 2**31 - 1))
    ts_splitter = TimeSeriesSplit(n_splits=N_TS_SPLITS)

    model = CausalForestDML(
        model_y=RandomForestRegressor(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        model_t=RandomForestClassifier(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        n_estimators=300, max_depth=6,
        discrete_treatment=True, cv=ts_splitter,
        random_state=seed, n_jobs=-1,
    )
    try:
        model.fit(Y, T, X=X, W=None)
        ate = float(model.ate(X))
        ate_lo, ate_hi = model.ate_interval(X, alpha=0.05)
        ate_lo, ate_hi = float(ate_lo), float(ate_hi)
        se = float((ate_hi - ate_lo) / (2 * 1.959963984540054))
        if ate_lo > 0:
            verdict = "Paradox"
        elif ate_hi < 0:
            verdict = "Inverted"
        else:
            verdict = "n.s."
        return {
            "spec": "CausalForestDML+TSSplit",
            "ate": ate, "se": se, "ci_lo": ate_lo, "ci_hi": ate_hi,
            "direction_verdict": verdict,
            "n_obs": int(len(df)),
            "fit_status": "ok",
        }
    except Exception as e:
        return {
            "spec": "CausalForestDML+TSSplit",
            "fit_status": f"error: {type(e).__name__}: {e}",
            "ate": float("nan"), "se": float("nan"),
            "ci_lo": float("nan"), "ci_hi": float("nan"),
            "direction_verdict": "SKIP", "n_obs": int(len(df)),
        }


def analyze_market(cfg: dict[str, Any]) -> dict[str, Any] | None:
    name = cfg["name"]
    print(f"\n[{name}] {cfg['ticker']} via {cfg['source']}")
    rng = np.random.default_rng(RNG_BASE + zlib.crc32((name).encode()) % 1000)

    t0 = time.time()
    try:
        out = run_full_pipeline(market=name, ticker=cfg["ticker"], source=cfg["source"], start=START, end=END)
    except Exception as e:
        print(f"  [SKIP] {type(e).__name__}: {e}")
        return None

    raw_labels: pd.Series = out["raw_labels"]
    if len(raw_labels) < SPE_Z_WIN:
        print(f"  [SKIP] insufficient bars")
        return None

    df = build_dml_dataset(out["ohlcv"], raw_labels, horizon=PRIMARY_HORIZON)
    if int(df["T"].sum()) < 30 or int((1 - df["T"]).sum()) < 30:
        print(f"  [SKIP] insufficient T or control obs")
        return None

    print(f"  obs: {len(df)} (Det={int(df['T'].sum())}, Sto={int((1-df['T']).sum())})")
    print("  fitting LinearDML + TSSplit + Bootstrap...")
    lin_res = fit_linear_dml_tsaware(df, rng)
    print(f"    ATE = {lin_res['ate']:+.4f} ({lin_res['ci_lo']:+.4f}, {lin_res['ci_hi']:+.4f}) -> {lin_res['direction_verdict']}")

    print("  fitting CausalForestDML + TSSplit...")
    cf_res = fit_causal_forest_dml_tsaware(df, rng)
    print(f"    ATE = {cf_res['ate']:+.4f} ({cf_res['ci_lo']:+.4f}, {cf_res['ci_hi']:+.4f}) -> {cf_res['direction_verdict']}")

    elapsed = time.time() - t0
    print(f"  elapsed: {elapsed:.1f}s")
    return {
        "market": name,
        "n_dml_obs": int(len(df)),
        "n_det": int(df["T"].sum()),
        "n_sto": int((1 - df["T"]).sum()),
        "horizon": PRIMARY_HORIZON,
        "linear_dml_tsaware": lin_res,
        "causal_forest_dml_tsaware": cf_res,
        "elapsed_seconds": float(elapsed),
    }


def main() -> int:
    print("=" * 70)
    print("  H1 DML TIME-SERIES-AWARE (TimeSeriesSplit + BootstrapInference)")
    print("=" * 70)
    print(f"  Splits: {N_TS_SPLITS} (forward-chaining)")
    print(f"  Bootstrap samples: {N_BOOTSTRAP} (LinearDML only; CausalForest uses default)")

    results = {}
    t_start = time.time()
    for cfg in MARKETS:
        res = analyze_market(cfg)
        if res is not None:
            results[cfg["name"]] = res
    total_elapsed = time.time() - t_start

    payload = {
        "spec": "H1 DML time-series-aware: TimeSeriesSplit + BootstrapInference",
        "n_markets": len(results),
        "n_ts_splits": N_TS_SPLITS,
        "n_bootstrap": N_BOOTSTRAP,
        "horizon": PRIMARY_HORIZON,
        "seed": RNG_BASE,
        "total_elapsed_seconds": float(total_elapsed),
        "results": results,
    }
    out_path = os.path.join(OUTPUT_DIR, "h1_dml_tsaware.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    print("\n" + "=" * 70)
    print("  SUMMARY (TS-AWARE)")
    print("=" * 70)
    print(f"  {'market':<10}  {'LinearDML+Bootstrap':<28}  {'CausalForest+TSSplit':<28}")
    for m, r in results.items():
        lin = r["linear_dml_tsaware"]
        cf = r["causal_forest_dml_tsaware"]
        lin_str = f"{lin['ate']:+.3f} [{lin['ci_lo']:+.2f},{lin['ci_hi']:+.2f}] {lin['direction_verdict']:<7}" if lin["fit_status"] == "ok" else "[FAIL]"
        cf_str  = f"{cf['ate']:+.3f} [{cf['ci_lo']:+.2f},{cf['ci_hi']:+.2f}] {cf['direction_verdict']:<7}" if cf["fit_status"] == "ok" else "[FAIL]"
        print(f"  {m:<10}  {lin_str:<28}  {cf_str:<28}")

    print(f"\n  Total elapsed: {total_elapsed:.1f}s")
    print(f"  JSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
