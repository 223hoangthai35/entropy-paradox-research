"""
H1 DML on FILTERED labels with Purged K-Fold cross-validation
(López de Prado, 2018, Chapter 7.3).

This is the canonical methodologically defensible variant for financial
regime classification with overlapping forward-looking targets:

  - Cross-fitting splitter = PurgedKFold (López de Prado, 2018, §7.3)
    n_splits = 5 contiguous blocks
    embargo = 20 bars (matches forward-vol overlap window; eliminates
                       autocorrelation contamination between train/test)
  - Treatment = filtered (Schmitt-trigger) regime labels (deployment-relevant)
  - Inference = BootstrapInference (n_bootstrap=100) for LinearDML
  - Asymptotic CI for CausalForestDML (no bootstrap support)

Why PurgedKFold and not KFold or TimeSeriesSplit:
  - KFold (sklearn default) leaks future blocks into past predictions
  - TimeSeriesSplit infeasible when treatment distribution is non-stationary
    (rare classes only emerging late => early training folds lack them)
  - PurgedKFold uses contiguous blocks WITHOUT shuffle (preserves
    autocorrelation structure within blocks), then PURGES embargo zone
    around each test fold from training (removes the autocorrelation
    contamination that creates leakage)
  - Disjoint test folds preserve standard cross-fitting property required
    by DML estimators
  - Reference: López de Prado (2018), "Advances in Financial Machine
    Learning", Ch. 7.3 (Purged K-Fold), Ch. 7.4 (Embargo)

Note on Combinatorial Purged CV (CPCV, Ch. 7.5): CPCV produces overlapping
test sets across combinations, useful for backtest path aggregation but NOT
compatible with DML cross-fitting which requires disjoint test folds.
PurgedKFold (Ch. 7.3) is the correct choice for DML.

Output: validation/results_v2/h1_dml_cpcv.json
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
from econml.dml import LinearDML, CausalForestDML
from econml.inference import BootstrapInference

from validation._features import run_full_pipeline, SPE_Z_WIN
from validation.h1_direction.h1_dml import (
    MARKETS, START, END, PRIMARY_HORIZON, RNG_SEED, OUTPUT_DIR,
    build_dml_dataset,
)
from validation._cpcv_splitter import PurgedKFold

# Purged K-Fold configuration (López de Prado §7.3)
PKF_N_SPLITS = 5
PKF_EMBARGO = 20  # matches forward 20-day RV overlap window
N_BOOTSTRAP = 100


def fit_linear_dml_cpcv(df: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    feature_cols = [c for c in df.columns if c not in ("fwd_vol", "T", "regime")]
    Y = df["fwd_vol"].values
    T = df["T"].values
    X = df[feature_cols].values
    seed = int(rng.integers(0, 2**31 - 1))

    cpcv = PurgedKFold(n_splits=PKF_N_SPLITS, embargo=PKF_EMBARGO)
    model = LinearDML(
        model_y=RandomForestRegressor(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        model_t=RandomForestClassifier(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        discrete_treatment=True,
        cv=cpcv,
        random_state=seed,
    )
    try:
        model.fit(Y, T, X=X, W=None,
                  inference=BootstrapInference(n_bootstrap_samples=N_BOOTSTRAP, n_jobs=-1))
        ate = float(model.ate(X))
        ate_lo, ate_hi = model.ate_interval(X, alpha=0.05)
        ate_lo, ate_hi = float(ate_lo), float(ate_hi)
        se = float((ate_hi - ate_lo) / (2 * 1.959963984540054))
        verdict = ("Paradox" if ate_lo > 0 else
                   "Inverted" if ate_hi < 0 else "n.s.")
        return {
            "spec": "LinearDML+PurgedKFold+Bootstrap",
            "ate": ate, "se": se, "ci_lo": ate_lo, "ci_hi": ate_hi,
            "direction_verdict": verdict,
            "n_obs": int(len(df)),
            "n_det": int(df["T"].sum()),
            "n_sto": int((1 - df["T"]).sum()),
            "fit_status": "ok",
        }
    except Exception as e:
        return {
            "spec": "LinearDML+PurgedKFold+Bootstrap",
            "fit_status": f"error: {type(e).__name__}: {e}",
            "ate": float("nan"), "se": float("nan"),
            "ci_lo": float("nan"), "ci_hi": float("nan"),
            "direction_verdict": "SKIP", "n_obs": int(len(df)),
        }


def fit_causal_forest_dml_cpcv(df: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    feature_cols = [c for c in df.columns if c not in ("fwd_vol", "T", "regime")]
    Y = df["fwd_vol"].values
    T = df["T"].values
    X = df[feature_cols].values
    seed = int(rng.integers(0, 2**31 - 1))

    cpcv = PurgedKFold(n_splits=PKF_N_SPLITS, embargo=PKF_EMBARGO)
    model = CausalForestDML(
        model_y=RandomForestRegressor(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        model_t=RandomForestClassifier(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        n_estimators=300, max_depth=6,
        discrete_treatment=True, cv=cpcv,
        random_state=seed, n_jobs=-1,
    )
    try:
        model.fit(Y, T, X=X, W=None)
        ate = float(model.ate(X))
        ate_lo, ate_hi = model.ate_interval(X, alpha=0.05)
        ate_lo, ate_hi = float(ate_lo), float(ate_hi)
        se = float((ate_hi - ate_lo) / (2 * 1.959963984540054))
        verdict = ("Paradox" if ate_lo > 0 else
                   "Inverted" if ate_hi < 0 else "n.s.")
        return {
            "spec": "CausalForestDML+PurgedKFold",
            "ate": ate, "se": se, "ci_lo": ate_lo, "ci_hi": ate_hi,
            "direction_verdict": verdict,
            "n_obs": int(len(df)),
            "fit_status": "ok",
        }
    except Exception as e:
        return {
            "spec": "CausalForestDML+PurgedKFold",
            "fit_status": f"error: {type(e).__name__}: {e}",
            "ate": float("nan"), "se": float("nan"),
            "ci_lo": float("nan"), "ci_hi": float("nan"),
            "direction_verdict": "SKIP", "n_obs": int(len(df)),
        }


def analyze_market(cfg: dict[str, Any]) -> dict[str, Any] | None:
    name = cfg["name"]
    print(f"\n[{name}] {cfg['ticker']} via {cfg['source']}")
    rng = np.random.default_rng(RNG_SEED + zlib.crc32((name).encode()) % 1000)

    t0 = time.time()
    try:
        out = run_full_pipeline(market=name, ticker=cfg["ticker"], source=cfg["source"], start=START, end=END)
    except Exception as e:
        print(f"  [SKIP] {type(e).__name__}: {e}")
        return None

    filt_labels = out["filtered_labels"]
    if len(filt_labels) < SPE_Z_WIN:
        print(f"  [SKIP] insufficient bars")
        return None

    df = build_dml_dataset(out["ohlcv"], filt_labels, horizon=PRIMARY_HORIZON)
    if int(df["T"].sum()) < 30 or int((1 - df["T"]).sum()) < 30:
        print(f"  [SKIP] insufficient T or control obs")
        return None

    print(f"  obs: {len(df)} (Det={int(df['T'].sum())}, Sto={int((1-df['T']).sum())})")
    print(f"  PurgedKFold: K={PKF_N_SPLITS}, embargo={PKF_EMBARGO}")
    print("  fitting LinearDML + PurgedKFold + Bootstrap...")
    lin_res = fit_linear_dml_cpcv(df, rng)
    print(f"    ATE = {lin_res['ate']:+.4f} ({lin_res['ci_lo']:+.4f}, {lin_res['ci_hi']:+.4f}) -> {lin_res['direction_verdict']}")
    print("  fitting CausalForestDML + PurgedKFold...")
    cf_res = fit_causal_forest_dml_cpcv(df, rng)
    print(f"    ATE = {cf_res['ate']:+.4f} ({cf_res['ci_lo']:+.4f}, {cf_res['ci_hi']:+.4f}) -> {cf_res['direction_verdict']}")

    elapsed = time.time() - t0
    print(f"  elapsed: {elapsed:.1f}s")
    return {
        "market": name,
        "label_source": "filtered_schmitt_trigger",
        "n_dml_obs": int(len(df)),
        "n_det": int(df["T"].sum()),
        "n_sto": int((1 - df["T"]).sum()),
        "horizon": PRIMARY_HORIZON,
        "purged_kfold_config": {"n_splits": PKF_N_SPLITS, "embargo": PKF_EMBARGO},
        "linear_dml": lin_res,
        "causal_forest_dml": cf_res,
        "elapsed_seconds": float(elapsed),
    }


def main() -> int:
    print("=" * 70)
    print("  H1 DML + FILTERED LABELS + PURGED K-FOLD (CANONICAL SPEC)")
    print("=" * 70)
    print(f"  Cross-fitting: PurgedKFold (K={PKF_N_SPLITS}, embargo={PKF_EMBARGO})")
    print(f"  LinearDML inference: BootstrapInference (n_boot={N_BOOTSTRAP})")
    print(f"  CausalForestDML inference: asymptotic (default)")
    print(f"  Reference: López de Prado (2018), 'Advances in Financial Machine Learning', Ch. 7.3")

    results = {}
    t_start = time.time()
    for cfg in MARKETS:
        res = analyze_market(cfg)
        if res is not None:
            results[cfg["name"]] = res
    total_elapsed = time.time() - t_start

    payload = {
        "spec": "H1 DML on filtered Schmitt-trigger labels with Purged K-Fold cross-fitting (López de Prado 2018, §7.3)",
        "n_markets": len(results),
        "horizon": PRIMARY_HORIZON,
        "purged_kfold": {"n_splits": PKF_N_SPLITS, "embargo": PKF_EMBARGO,
                         "reference": "López de Prado (2018) AFML Ch. 7.3"},
        "n_bootstrap": N_BOOTSTRAP,
        "seed": RNG_SEED,
        "total_elapsed_seconds": float(total_elapsed),
        "results": results,
    }
    out_path = os.path.join(OUTPUT_DIR, "h1_direction/h1_dml_cpcv.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    print("\n" + "=" * 70)
    print("  SUMMARY (FILTERED + PURGED K-FOLD - CANONICAL SPEC)")
    print("=" * 70)
    print(f"  {'market':<10}  {'LinDML+PurgedKF':<28}  {'CF-DML+PurgedKF':<28}")
    for m, r in results.items():
        lin = r["linear_dml"]
        cf = r["causal_forest_dml"]
        lin_str = f"{lin['ate']:+.3f} [{lin['ci_lo']:+.2f},{lin['ci_hi']:+.2f}] {lin['direction_verdict']:<7}" if lin["fit_status"] == "ok" else "[FAIL]"
        cf_str  = f"{cf['ate']:+.3f} [{cf['ci_lo']:+.2f},{cf['ci_hi']:+.2f}] {cf['direction_verdict']:<7}" if cf["fit_status"] == "ok" else "[FAIL]"
        print(f"  {m:<10}  {lin_str:<28}  {cf_str:<28}")

    print(f"\n  Total elapsed: {total_elapsed:.1f}s")
    print(f"  JSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
