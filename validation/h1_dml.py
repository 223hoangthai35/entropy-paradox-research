"""
H1 DML — per-market Double/Debiased Machine Learning estimation of regime
direction effect on forward 20-day realized volatility.

PHASE 0 of plan v8: this script is the gating empirical comparison study.
Does DML provide materially new insight versus the current Cliff's delta +
circular-block bootstrap CI + Newey-West HAC framework (cross_market_v2.py)?

Per market:
  Treatment T = binary regime indicator (1 if Deterministic, 0 if Stochastic)
  Outcome Y  = forward 20-day realized volatility (annualised %)
  Controls X = lagged variables to absorb autocorrelation/calendar nuisance
              - lagged log returns at lags 1, 5, 22
              - lagged squared returns at lags 1, 5, 22
              - lagged realized vol (rolling 22d) at lag 1 and lag 22
              - day-of-week one-hot (4 dummies, Monday reference)

Two DML spec variants:
  (1) LinearDML — linear final stage; fast, interpretable
  (2) CausalForestDML — nonparametric final stage; robust to nonlinearity

Cross-fitting: 5 folds, RandomForest nuisance models (regression for Y|X
and classification for T|X). Random seed = 42.

Output: validation/results_v2/h1_dml.json
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import run_full_pipeline, SPE_Z_WIN
from skills.ds_skill import REGIME_NAMES

from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from econml.dml import LinearDML, CausalForestDML

# ==============================================================================
# PRE-REGISTERED MARKET PANEL (matches cross_market_v2.py)
# ==============================================================================
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

START = "2018-01-01"
END   = "2026-04-17"
PRIMARY_HORIZON = 20
RNG_SEED = 42
N_FOLDS = 5

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==============================================================================
# DATA PREPARATION
# ==============================================================================
def build_dml_dataset(
    ohlcv: pd.DataFrame,
    raw_labels: pd.Series,
    horizon: int = PRIMARY_HORIZON,
) -> pd.DataFrame:
    """
    Construct the (Y, T, X) dataset for binary Det vs Sto DML estimation.

    Y = forward `horizon`-day realized vol (annualized %)
    T = 1 if regime label = Deterministic, 0 if Stochastic; Transitional dropped
    X = lagged returns (1, 5, 22), lagged squared returns (1, 5, 22),
        lagged realized vol (1, 22), day-of-week (4 dummies)
    """
    close = ohlcv["Close"].astype(float)
    log_ret = np.log(close / close.shift(1))

    # Forward realized volatility (matches cross_market_v2 convention)
    fwd_vol = (log_ret.shift(-1).rolling(horizon).std()
                       .shift(-(horizon - 1)) * np.sqrt(252) * 100.0)

    # Lagged controls
    df = pd.DataFrame({
        "log_ret_lag1":  log_ret.shift(1),
        "log_ret_lag5":  log_ret.shift(5),
        "log_ret_lag22": log_ret.shift(22),
        "sq_ret_lag1":   (log_ret ** 2).shift(1),
        "sq_ret_lag5":   (log_ret ** 2).shift(5),
        "sq_ret_lag22":  (log_ret ** 2).shift(22),
        "rv22_lag1":     (log_ret.rolling(22).std() * np.sqrt(252) * 100.0).shift(1),
        "rv22_lag22":    (log_ret.rolling(22).std() * np.sqrt(252) * 100.0).shift(22),
    }, index=ohlcv.index)

    # Day-of-week one-hot (Monday=0 reference dropped)
    dow = ohlcv.index.dayofweek
    for d, name in zip([1, 2, 3, 4], ["dow_tue", "dow_wed", "dow_thu", "dow_fri"]):
        df[name] = (dow == d).astype(float)

    df["fwd_vol"] = fwd_vol

    # Map regime labels and restrict to Det / Sto
    label_str = raw_labels.astype(int).map(REGIME_NAMES)
    df = df.join(label_str.rename("regime"))
    df = df[df["regime"].isin(["Deterministic", "Stochastic"])].copy()
    df["T"] = (df["regime"] == "Deterministic").astype(float)

    # Drop rows with any NaN (lagged windows + forward window edge effects)
    df = df.dropna()
    return df


# ==============================================================================
# DML ESTIMATION
# ==============================================================================
def fit_linear_dml(df: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    """LinearDML: linear final stage. Fast, interpretable ATE estimate."""
    feature_cols = [c for c in df.columns if c not in ("fwd_vol", "T", "regime")]
    Y = df["fwd_vol"].values
    T = df["T"].values
    X = df[feature_cols].values

    seed = int(rng.integers(0, 2**31 - 1))

    model = LinearDML(
        model_y=RandomForestRegressor(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        model_t=RandomForestClassifier(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        discrete_treatment=True,
        cv=N_FOLDS,
        random_state=seed,
    )
    try:
        model.fit(Y, T, X=X, W=None)
        ate = float(model.ate(X))
        ate_lo, ate_hi = model.ate_interval(X, alpha=0.05)
        ate_lo, ate_hi = float(ate_lo), float(ate_hi)
        # Heuristic SE from CI half-width / 1.96
        se = float((ate_hi - ate_lo) / (2 * 1.959963984540054))
        # Direction label per H1 convention (Paradox if Det > Sto)
        if ate_lo > 0:
            verdict = "Paradox"
        elif ate_hi < 0:
            verdict = "Inverted"
        else:
            verdict = "n.s."
        return {
            "spec": "LinearDML",
            "ate": ate,
            "se": se,
            "ci_lo": ate_lo,
            "ci_hi": ate_hi,
            "direction_verdict": verdict,
            "n_obs": int(len(df)),
            "n_det": int(df["T"].sum()),
            "n_sto": int((1 - df["T"]).sum()),
            "n_features": len(feature_cols),
            "fit_status": "ok",
        }
    except Exception as e:
        return {
            "spec": "LinearDML",
            "fit_status": f"error: {type(e).__name__}: {e}",
            "ate": float("nan"),
            "se": float("nan"),
            "ci_lo": float("nan"),
            "ci_hi": float("nan"),
            "direction_verdict": "SKIP",
            "n_obs": int(len(df)),
        }


def fit_causal_forest_dml(df: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    """CausalForestDML: nonparametric final stage; robust to nonlinearity."""
    feature_cols = [c for c in df.columns if c not in ("fwd_vol", "T", "regime")]
    Y = df["fwd_vol"].values
    T = df["T"].values
    X = df[feature_cols].values

    seed = int(rng.integers(0, 2**31 - 1))

    model = CausalForestDML(
        model_y=RandomForestRegressor(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        model_t=RandomForestClassifier(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1),
        n_estimators=300,
        max_depth=6,
        discrete_treatment=True,
        cv=N_FOLDS,
        random_state=seed,
        n_jobs=-1,
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
            "spec": "CausalForestDML",
            "ate": ate,
            "se": se,
            "ci_lo": ate_lo,
            "ci_hi": ate_hi,
            "direction_verdict": verdict,
            "n_obs": int(len(df)),
            "n_det": int(df["T"].sum()),
            "n_sto": int((1 - df["T"]).sum()),
            "n_features": len(feature_cols),
            "fit_status": "ok",
        }
    except Exception as e:
        return {
            "spec": "CausalForestDML",
            "fit_status": f"error: {type(e).__name__}: {e}",
            "ate": float("nan"),
            "se": float("nan"),
            "ci_lo": float("nan"),
            "ci_hi": float("nan"),
            "direction_verdict": "SKIP",
            "n_obs": int(len(df)),
        }


# ==============================================================================
# PER-MARKET ANALYSIS
# ==============================================================================
def analyze_market(cfg: dict[str, Any]) -> dict[str, Any] | None:
    name = cfg["name"]
    print(f"\n[{name}] {cfg['ticker']} via {cfg['source']}")
    rng = np.random.default_rng(RNG_SEED + hash(name) % 1000)

    t0 = time.time()
    try:
        out = run_full_pipeline(
            market=name, ticker=cfg["ticker"], source=cfg["source"],
            start=START, end=END,
        )
    except Exception as e:
        print(f"  [SKIP] pipeline failed: {type(e).__name__}: {e}")
        return None

    raw_labels: pd.Series = out["raw_labels"]
    ohlcv = out["ohlcv"]

    if len(raw_labels) < SPE_Z_WIN:
        print(f"  [SKIP] insufficient labelable bars: {len(raw_labels)} < {SPE_Z_WIN}")
        return None

    df = build_dml_dataset(ohlcv, raw_labels, horizon=PRIMARY_HORIZON)
    print(f"  DML dataset: {len(df)} obs (Det={int(df['T'].sum())}, Sto={int((1-df['T']).sum())})")

    if int(df["T"].sum()) < 30 or int((1 - df["T"]).sum()) < 30:
        print(f"  [SKIP] insufficient T or control obs")
        return None

    print("  fitting LinearDML...")
    lin_res = fit_linear_dml(df, rng)
    print(f"    LinearDML: ATE = {lin_res['ate']:+.4f} ({lin_res['ci_lo']:+.4f}, {lin_res['ci_hi']:+.4f}) -> {lin_res['direction_verdict']}")

    print("  fitting CausalForestDML...")
    cf_res = fit_causal_forest_dml(df, rng)
    print(f"    CausalForestDML: ATE = {cf_res['ate']:+.4f} ({cf_res['ci_lo']:+.4f}, {cf_res['ci_hi']:+.4f}) -> {cf_res['direction_verdict']}")

    elapsed = time.time() - t0
    print(f"  elapsed: {elapsed:.1f}s")

    return {
        "market": name,
        "ticker": cfg["ticker"],
        "n_dml_obs": int(len(df)),
        "n_det": int(df["T"].sum()),
        "n_sto": int((1 - df["T"]).sum()),
        "horizon": PRIMARY_HORIZON,
        "controls": [c for c in df.columns if c not in ("fwd_vol", "T", "regime")],
        "linear_dml": lin_res,
        "causal_forest_dml": cf_res,
        "elapsed_seconds": float(elapsed),
    }


# ==============================================================================
# MAIN
# ==============================================================================
def main() -> int:
    print("=" * 70)
    print("  H1 DML PER-MARKET ESTIMATION (PHASE 0 GATE)")
    print("=" * 70)
    print(f"  Markets: {len(MARKETS)}")
    print(f"  Treatment: Det vs Sto (binary)")
    print(f"  Outcome: forward {PRIMARY_HORIZON}d realized vol (ann %)")
    print(f"  Controls: lagged returns + lagged sq returns + lagged RV + DOW")
    print(f"  Cross-fit folds: {N_FOLDS}")
    print(f"  Seed: {RNG_SEED}")

    results = {}
    t_start = time.time()
    for cfg in MARKETS:
        res = analyze_market(cfg)
        if res is not None:
            results[cfg["name"]] = res
    total_elapsed = time.time() - t_start

    payload = {
        "spec": "H1 DML estimation: per-market Det vs Sto effect on forward 20d RV with cross-fitted nuisance + RandomForest controls",
        "markets": list(results.keys()),
        "n_markets": len(results),
        "horizon": PRIMARY_HORIZON,
        "n_folds": N_FOLDS,
        "seed": RNG_SEED,
        "total_elapsed_seconds": float(total_elapsed),
        "results": results,
    }

    out_path = os.path.join(OUTPUT_DIR, "h1_dml.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    print("\n" + "=" * 70)
    print("  SUMMARY")
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
