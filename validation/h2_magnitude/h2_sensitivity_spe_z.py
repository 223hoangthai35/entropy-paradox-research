"""
H2 sensitivity to SPE_Z standardization choice (Plan v9 §A.2, Critical C-3).

Tests whether the cross-market H ↔ tier/RPS coupling survives 3 alternative
specifications of the SPE_Z feature:

  Variant 1: WPE-only (drop SPE_Z entirely, GMM on 1D feature)
  Variant 2: Raw SampEn (no Z-score normalization)
  Variant 3: Global Z-score (full-sample mean/std instead of rolling 504-day)

Each variant: refit GMM K=3 per market → compute KW H statistic on raw labels
on forward 20-day RV → cross-market Spearman ρ vs (a) tier rank, (b) RPS.

Goal: demonstrate cross-market H ordering is not an artifact of the
specific SPE_Z standardization choice.

Output: validation/results_v2/h2_sensitivity_spe_z.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import kruskal, spearmanr

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from validation._features import load_ohlcv, SPE_Z_WIN, WPE_M, WPE_TAU, WPE_WINDOW, SAMPEN_WIN
from skills.quant_skill import (
    calc_rolling_wpe,
    calc_rolling_price_sample_entropy,
    cal_spe_z_global,
    cal_spe_z_rolling,
)
from skills.ds_skill import EntropyPhaseSpaceClassifier, REGIME_NAMES

# Markets and tier ranks per Hybrid C
MARKETS = [
    {"name": "VNINDEX", "ticker": "VNINDEX", "source": "vnstock",  "tier_rank": 4},
    {"name": "BVB",     "ticker": "BVB:BET",  "source": "tvdatafeed", "tier_rank": 4},
    {"name": "KOSPI",   "ticker": "^KS11",   "source": "yfinance", "tier_rank": 3},
    {"name": "NIFTY",   "ticker": "^NSEI",   "source": "yfinance", "tier_rank": 3},
    {"name": "SPX",     "ticker": "^GSPC",   "source": "yfinance", "tier_rank": 1},
    {"name": "FTSE",    "ticker": "^FTSE",   "source": "yfinance", "tier_rank": 1},
    {"name": "NIKKEI",  "ticker": "^N225",   "source": "yfinance", "tier_rank": 1},
    {"name": "BTC",     "ticker": "BTC-USD", "source": "yfinance", "tier_rank": 2},
]

RPS = {"VNINDEX": 0.90, "BVB": 0.225, "KOSPI": 0.45, "NIFTY": 0.40,
       "SPX": 0.275, "FTSE": 0.20, "NIKKEI": 0.18, "BTC": 0.55}

START = "2018-01-01"
END = "2026-06-30"
PRIMARY_HORIZON = 20
RNG_SEED = 42

OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_features(df: pd.DataFrame, variant: str) -> pd.DataFrame:
    """Build feature matrix for the given variant."""
    log_returns = np.log(df["Close"] / df["Close"].shift(1)).values
    wpe, _ = calc_rolling_wpe(log_returns, m=WPE_M, tau=WPE_TAU, window=WPE_WINDOW)
    sampen = calc_rolling_price_sample_entropy(df["Close"].values, window=SAMPEN_WIN)

    if variant == "wpe_only":
        return pd.DataFrame({"WPE": wpe}, index=df.index).dropna()
    elif variant == "raw_sampen":
        return pd.DataFrame({"WPE": wpe, "SampEn": sampen}, index=df.index).dropna()
    elif variant == "global_z":
        spe_z_g = cal_spe_z_global(sampen)
        return pd.DataFrame({"WPE": wpe, "SPE_Z_global": spe_z_g}, index=df.index).dropna()
    elif variant == "rolling_z":  # baseline (current production)
        spe_z = cal_spe_z_rolling(sampen, window=SPE_Z_WIN)
        return pd.DataFrame({"WPE": wpe, "SPE_Z": spe_z}, index=df.index).dropna()
    else:
        raise ValueError(f"Unknown variant: {variant}")


def compute_kw_h(df_ohlcv: pd.DataFrame, feat: pd.DataFrame, horizon: int = PRIMARY_HORIZON) -> dict:
    """Fit GMM K=3 on feat, compute KW H on forward RV across regimes."""
    if len(feat) < 100:
        return {"H_stat": float("nan"), "p_value": float("nan"),
                "n_obs": int(len(feat)), "fit_status": "insufficient bars"}

    n_components_required = feat.shape[1]
    # Need at least 2 dimensions for GMM K=3 to make sense; for 1D fall back gracefully
    try:
        clf = EntropyPhaseSpaceClassifier(n_components=3, random_state=RNG_SEED)
        labels = clf.fit_predict(feat.values)
    except Exception as e:
        return {"H_stat": float("nan"), "p_value": float("nan"),
                "n_obs": int(len(feat)), "fit_status": f"gmm fail: {e}"}

    # Compute forward 20d realized vol
    close = df_ohlcv["Close"].astype(float)
    log_ret = np.log(close / close.shift(1))
    fwd_vol = (log_ret.shift(-1).rolling(horizon).std()
                       .shift(-(horizon - 1)) * np.sqrt(252) * 100.0)

    # Align labels with fwd_vol
    label_series = pd.Series(labels, index=feat.index, name="label").map(REGIME_NAMES)
    df_combined = pd.DataFrame({"label": label_series, "fwd_vol": fwd_vol.reindex(feat.index)}).dropna()

    groups = {r: df_combined.loc[df_combined["label"] == r, "fwd_vol"].values
              for r in ["Deterministic", "Transitional", "Stochastic"]}
    usable = {r: v for r, v in groups.items() if len(v) >= 5}
    if len(usable) < 2:
        return {"H_stat": float("nan"), "p_value": float("nan"),
                "n_obs": int(len(df_combined)), "fit_status": "insufficient regime obs"}
    H, p = kruskal(*usable.values())
    return {
        "H_stat": float(H),
        "p_value": float(p),
        "n_obs": int(len(df_combined)),
        "n_per_regime": {r: int(len(v)) for r, v in groups.items()},
        "fit_status": "ok",
    }


def main() -> int:
    print("=" * 70)
    print("  H2 SENSITIVITY TO SPE_Z STANDARDIZATION")
    print("=" * 70)
    variants = ["rolling_z", "wpe_only", "raw_sampen", "global_z"]

    results = {v: {} for v in variants}
    t_start = time.time()

    for cfg in MARKETS:
        name = cfg["name"]
        print(f"\n[{name}] loading data...")
        try:
            df = load_ohlcv(name, cfg["ticker"], cfg["source"], START, END)
        except Exception as e:
            print(f"  [SKIP] load failed: {e}")
            continue

        for variant in variants:
            try:
                feat = build_features(df, variant)
                kw = compute_kw_h(df, feat, horizon=PRIMARY_HORIZON)
                results[variant][name] = kw
                print(f"  {variant:<14}: H={kw['H_stat']:.2f}  p={kw['p_value']:.4f}  n={kw['n_obs']}  status={kw['fit_status']}")
            except Exception as e:
                print(f"  {variant:<14}: FAIL {type(e).__name__}: {e}")
                results[variant][name] = {"fit_status": f"error: {type(e).__name__}: {e}"}

    print("\n" + "=" * 70)
    print("  CROSS-MARKET SPEARMAN ρ(H, tier_rank) AND ρ(H, RPS) PER VARIANT")
    print("=" * 70)

    tier_arr = np.array([cfg["tier_rank"] for cfg in MARKETS])
    rps_arr = np.array([RPS[cfg["name"]] for cfg in MARKETS])

    cross_market = {}
    for variant in variants:
        h_arr = []
        valid_idx = []
        for i, cfg in enumerate(MARKETS):
            r = results[variant].get(cfg["name"], {})
            if r.get("fit_status") == "ok":
                h_arr.append(r["H_stat"])
                valid_idx.append(i)
        h_arr = np.array(h_arr)
        if len(h_arr) >= 4:
            tiers = tier_arr[valid_idx]
            rps_v = rps_arr[valid_idx]
            rho_tier, p_tier = spearmanr(h_arr, tiers)
            rho_rps, p_rps = spearmanr(h_arr, rps_v)
            cross_market[variant] = {
                "n_markets": len(h_arr),
                "rho_H_tier": float(rho_tier), "p_H_tier": float(p_tier),
                "rho_H_rps": float(rho_rps), "p_H_rps": float(p_rps),
            }
            print(f"  {variant:<14}: n={len(h_arr)}  ρ(H,tier)={rho_tier:+.3f} (p={p_tier:.3f})  ρ(H,RPS)={rho_rps:+.3f} (p={p_rps:.3f})")
        else:
            cross_market[variant] = {"n_markets": len(h_arr), "status": "insufficient markets"}
            print(f"  {variant:<14}: insufficient successful markets")

    print("\n" + "=" * 70)
    print("  ROBUSTNESS VERDICT")
    print("=" * 70)
    print("  Compare ρ(H, tier_rank) and ρ(H, RPS) across variants:")
    print("  If baseline (rolling_z) headline holds across alternatives → SPE_Z choice not an artifact")

    payload = {
        "spec": "H2 sensitivity to SPE_Z standardization (4 variants: rolling_z baseline, wpe_only, raw_sampen, global_z)",
        "n_markets": len(MARKETS),
        "horizon": PRIMARY_HORIZON,
        "seed": RNG_SEED,
        "elapsed_seconds": float(time.time() - t_start),
        "per_market_per_variant": results,
        "cross_market_per_variant": cross_market,
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_magnitude/h2_sensitivity_spe_z.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
