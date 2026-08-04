"""
H2 with η² (eta-squared) effect size and per-market N_obs (Plan v9 §A.3, Critical C-5).

KW H statistic depends on N (sample size); cross-market comparison of H magnitude
without normalization conflates 'discrimination strength' with 'sample size effect'.
η² = (H − k + 1) / (N − k) where k=3 is the number of regime groups, N is total
observations. Range [0, 1], sample-size-corrected.

Per market: report N_obs (post-504-day floor), per-regime cell counts, η² for
both raw and filtered labels.

Cross-market: re-run Spearman ρ(η², tier_rank) and ρ(η², RPS) — confirm
ordering survives effect-size normalization.

Output: validation/results_v2/h2_eta_squared.json + console summary
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import run_full_pipeline, SPE_Z_WIN
from skills.ds_skill import REGIME_NAMES

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

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def kw_eta_squared(H: float, N: int, k: int = 3) -> float:
    """ε²/η² for KW: (H − k + 1) / (N − k); range [0,1]."""
    if N <= k or np.isnan(H):
        return float("nan")
    return float(max((H - k + 1.0) / (N - k), 0.0))


def compute_kw_h_and_eta(df_ohlcv: pd.DataFrame, labels: pd.Series, horizon: int = PRIMARY_HORIZON) -> dict:
    """KW H + η² + per-regime cell counts for given label series."""
    close = df_ohlcv["Close"].astype(float)
    log_ret = np.log(close / close.shift(1))
    fwd_vol = (log_ret.shift(-1).rolling(horizon).std()
                       .shift(-(horizon - 1)) * np.sqrt(252) * 100.0)

    label_str = labels.astype(int).map(REGIME_NAMES)
    df = pd.DataFrame({"label": label_str, "fwd_vol": fwd_vol.reindex(labels.index)}).dropna()
    groups = {r: df.loc[df["label"] == r, "fwd_vol"].values
              for r in ["Deterministic", "Transitional", "Stochastic"]}
    usable = {r: v for r, v in groups.items() if len(v) >= 5}
    if len(usable) < 2:
        return {"H_stat": float("nan"), "eta_sq": float("nan"), "N_obs": int(len(df)),
                "n_per_regime": {r: int(len(v)) for r, v in groups.items()}, "fit_status": "insufficient regime obs"}
    H, p = kruskal(*usable.values())
    N = sum(len(v) for v in groups.values())
    eta = kw_eta_squared(H, N, k=3)
    return {
        "H_stat": float(H), "p_value": float(p),
        "eta_sq": eta,
        "N_obs": int(N),
        "n_per_regime": {r: int(len(v)) for r, v in groups.items()},
        "fit_status": "ok",
    }


def main() -> int:
    print("=" * 70)
    print("  H2 + η² EFFECT SIZE + N_obs PER MARKET")
    print("=" * 70)

    results = {}
    t_start = time.time()
    for cfg in MARKETS:
        name = cfg["name"]
        print(f"\n[{name}] loading + GMM + KW H + η² ...")
        try:
            out = run_full_pipeline(market=name, ticker=cfg["ticker"], source=cfg["source"], start=START, end=END)
        except Exception as e:
            print(f"  [SKIP] {type(e).__name__}: {e}")
            continue

        raw_kw = compute_kw_h_and_eta(out["ohlcv"], out["raw_labels"])
        filt_kw = compute_kw_h_and_eta(out["ohlcv"], out["filtered_labels"])

        results[name] = {
            "tier_rank": cfg["tier_rank"], "RPS": RPS[name],
            "raw": raw_kw, "filtered": filt_kw,
        }
        print(f"  RAW : H={raw_kw['H_stat']:.2f}  η²={raw_kw['eta_sq']:.4f}  N={raw_kw['N_obs']}")
        print(f"  FILT: H={filt_kw['H_stat']:.2f}  η²={filt_kw['eta_sq']:.4f}  N={filt_kw['N_obs']}")

    print("\n" + "=" * 70)
    print("  CROSS-MARKET ρ(H,tier), ρ(η²,tier), ρ(H,RPS), ρ(η²,RPS)")
    print("=" * 70)

    # Build arrays
    markets = list(results.keys())
    h_raw = np.array([results[m]["raw"]["H_stat"] for m in markets])
    h_filt = np.array([results[m]["filtered"]["H_stat"] for m in markets])
    eta_raw = np.array([results[m]["raw"]["eta_sq"] for m in markets])
    eta_filt = np.array([results[m]["filtered"]["eta_sq"] for m in markets])
    tier_arr = np.array([results[m]["tier_rank"] for m in markets])
    rps_arr = np.array([results[m]["RPS"] for m in markets])

    cross = {}
    for label_name, h_v, eta_v in [("raw", h_raw, eta_raw), ("filtered", h_filt, eta_filt)]:
        rho_h_tier, p_h_tier = spearmanr(h_v, tier_arr)
        rho_eta_tier, p_eta_tier = spearmanr(eta_v, tier_arr)
        rho_h_rps, p_h_rps = spearmanr(h_v, rps_arr)
        rho_eta_rps, p_eta_rps = spearmanr(eta_v, rps_arr)
        cross[label_name] = {
            "rho_H_tier": float(rho_h_tier), "p_H_tier": float(p_h_tier),
            "rho_eta_tier": float(rho_eta_tier), "p_eta_tier": float(p_eta_tier),
            "rho_H_rps": float(rho_h_rps), "p_H_rps": float(p_h_rps),
            "rho_eta_rps": float(rho_eta_rps), "p_eta_rps": float(p_eta_rps),
        }
        print(f"\n  {label_name.upper()} labels:")
        print(f"    ρ(H,tier)  = {rho_h_tier:+.4f}  p={p_h_tier:.4f}")
        print(f"    ρ(η²,tier) = {rho_eta_tier:+.4f}  p={p_eta_tier:.4f}")
        print(f"    ρ(H,RPS)   = {rho_h_rps:+.4f}  p={p_h_rps:.4f}")
        print(f"    ρ(η²,RPS)  = {rho_eta_rps:+.4f}  p={p_eta_rps:.4f}")

    print("\n" + "=" * 70)
    print("  N_obs RANGE CHECK (sample-size confound diagnosis)")
    print("=" * 70)
    n_obs_arr = np.array([results[m]["raw"]["N_obs"] for m in markets])
    print(f"  Per-market N_obs (raw): min={n_obs_arr.min()}, max={n_obs_arr.max()}, range={n_obs_arr.max()-n_obs_arr.min()}")
    print(f"  Ratio max/min: {n_obs_arr.max()/n_obs_arr.min():.2f}x")
    rho_h_n, p_h_n = spearmanr(h_raw, n_obs_arr)
    rho_eta_n, p_eta_n = spearmanr(eta_raw, n_obs_arr)
    print(f"  ρ(H_raw, N_obs)  = {rho_h_n:+.4f}  p={p_h_n:.4f}")
    print(f"  ρ(η²_raw, N_obs) = {rho_eta_n:+.4f}  p={p_eta_n:.4f}")
    print(f"  → If H is sample-size-confounded, ρ(H,N) >> ρ(η²,N)")

    payload = {
        "spec": "H2 with η² effect size + N_obs per market (sample-size correction)",
        "n_markets": len(results),
        "horizon": PRIMARY_HORIZON,
        "seed": RNG_SEED,
        "elapsed_seconds": float(time.time() - t_start),
        "per_market": results,
        "cross_market": cross,
        "n_obs_diagnostics": {
            "min_N": int(n_obs_arr.min()), "max_N": int(n_obs_arr.max()),
            "range": int(n_obs_arr.max() - n_obs_arr.min()),
            "ratio_max_min": float(n_obs_arr.max() / n_obs_arr.min()),
            "rho_H_N": float(rho_h_n), "p_H_N": float(p_h_n),
            "rho_eta_N": float(rho_eta_n), "p_eta_N": float(p_eta_n),
        },
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_eta_squared.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
