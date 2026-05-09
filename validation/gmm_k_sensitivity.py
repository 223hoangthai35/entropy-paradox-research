"""
GMM K-selection per market sensitivity (Plan v9 §A.6, Major M-9).

Per market: compute BIC for K ∈ {2, 3, 4, 5}; identify market-optimal K_m.
Then per market at K = K_m: compute KW H statistic on forward 20-day RV.
Cross-market: do Spearman ρ(H, RPS) (primary) and ρ(H, tier) (ordinal robustness)
survive K choice and market-optimal K?

RPS vector follows the all-P1 reference of §4.2.1 (cascade composite Mean
equivalent for rank-correlation purposes; see Table 1 + paper §4.2.2 line 167).

Output: validation/results_v2/gmm_k_sensitivity.json
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
from sklearn.mixture import GaussianMixture

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import run_full_pipeline, SPE_Z_WIN

MARKETS = [
    {"name": "VNINDEX", "ticker": "VNINDEX", "source": "vnstock",  "tier_rank": 4, "rps": 0.90},
    {"name": "PSEI",    "ticker": "PSEI.PS", "source": "yfinance", "tier_rank": 4, "rps": 0.68},
    {"name": "KOSPI",   "ticker": "^KS11",   "source": "yfinance", "tier_rank": 3, "rps": 0.45},
    {"name": "NIFTY",   "ticker": "^NSEI",   "source": "yfinance", "tier_rank": 3, "rps": 0.40},
    {"name": "SPX",     "ticker": "^GSPC",   "source": "yfinance", "tier_rank": 1, "rps": 0.275},
    {"name": "FTSE",    "ticker": "^FTSE",   "source": "yfinance", "tier_rank": 1, "rps": 0.20},
    {"name": "NIKKEI",  "ticker": "^N225",   "source": "yfinance", "tier_rank": 1, "rps": 0.18},
    {"name": "BTC",     "ticker": "BTC-USD", "source": "yfinance", "tier_rank": 2, "rps": 0.55},
]

K_CANDIDATES = [2, 3, 4, 5]
START = "2018-01-01"
END = "2026-04-17"
PRIMARY_HORIZON = 20
RNG_SEED = 42

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")


def fit_gmm_get_h(feat: pd.DataFrame, df_ohlcv: pd.DataFrame, K: int, horizon: int = PRIMARY_HORIZON, seed: int = RNG_SEED) -> dict:
    """Fit GMM with K components, compute KW H on forward RV across regimes."""
    gmm = GaussianMixture(n_components=K, covariance_type="full", random_state=seed, n_init=10, max_iter=500)
    gmm.fit(feat.values)
    bic = float(gmm.bic(feat.values))
    labels = gmm.predict(feat.values)

    close = df_ohlcv["Close"].astype(float)
    log_ret = np.log(close / close.shift(1))
    fwd_vol = (log_ret.shift(-1).rolling(horizon).std()
                       .shift(-(horizon - 1)) * np.sqrt(252) * 100.0).reindex(feat.index)

    df = pd.DataFrame({"label": labels, "fwd_vol": fwd_vol}).dropna()
    groups = [df.loc[df["label"] == k, "fwd_vol"].values for k in range(K)]
    usable = [g for g in groups if len(g) >= 5]
    if len(usable) < 2:
        return {"K": K, "bic": bic, "H_stat": float("nan"), "p_value": float("nan"),
                "n_obs": int(len(df)), "fit_status": "insufficient regime obs"}
    H, p = kruskal(*usable)
    return {"K": K, "bic": bic, "H_stat": float(H), "p_value": float(p),
            "n_obs": int(len(df)), "n_per_regime": [int(len(g)) for g in groups]}


def main() -> int:
    print("=" * 70)
    print("  GMM K-SELECTION PER MARKET SENSITIVITY")
    print("=" * 70)

    results = {}
    t_start = time.time()
    for cfg in MARKETS:
        name = cfg["name"]
        print(f"\n[{name}] loading + GMM K sweep...")
        try:
            out = run_full_pipeline(market=name, ticker=cfg["ticker"], source=cfg["source"], start=START, end=END)
        except Exception as e:
            print(f"  [SKIP] {type(e).__name__}: {e}")
            continue
        feat = out["features"]
        market_results = {}
        for K in K_CANDIDATES:
            try:
                res = fit_gmm_get_h(feat, out["ohlcv"], K)
                market_results[f"K_{K}"] = res
                print(f"  K={K}: BIC={res['bic']:.1f}  H={res['H_stat']:.2f}  p={res['p_value']:.4f}")
            except Exception as e:
                market_results[f"K_{K}"] = {"K": K, "fit_status": f"error: {type(e).__name__}: {e}"}
                print(f"  K={K}: FAIL {type(e).__name__}: {e}")
        # Identify market-optimal K
        valid_ks = [(k, market_results[f"K_{k}"]["bic"]) for k in K_CANDIDATES
                    if "bic" in market_results[f"K_{k}"]]
        if valid_ks:
            opt_k, opt_bic = min(valid_ks, key=lambda x: x[1])
            print(f"  → BIC-optimal K_m = {opt_k} (BIC={opt_bic:.1f})")
        else:
            opt_k = None
        results[name] = {
            "tier_rank": cfg["tier_rank"],
            "rps": cfg["rps"],
            "k_results": market_results,
            "bic_optimal_K": opt_k,
        }

    print("\n" + "=" * 70)
    print("  CROSS-MARKET SPEARMAN ρ(H, RPS) [primary] + ρ(H, tier) [robustness]")
    print("=" * 70)

    tier_arr = np.array([cfg["tier_rank"] for cfg in MARKETS])
    rps_arr = np.array([cfg["rps"] for cfg in MARKETS])
    cross = {}
    for K in K_CANDIDATES:
        h_arr = []
        for cfg in MARKETS:
            r = results.get(cfg["name"], {}).get("k_results", {}).get(f"K_{K}", {})
            h_arr.append(r.get("H_stat", float("nan")))
        h_arr = np.array(h_arr)
        mask = ~np.isnan(h_arr)
        if mask.sum() >= 4:
            rho_rps, p_rps = spearmanr(h_arr[mask], rps_arr[mask])
            rho_tier, p_tier = spearmanr(h_arr[mask], tier_arr[mask])
            cross[f"fixed_K_{K}"] = {"K": K, "n_markets": int(mask.sum()),
                                       "rho_H_rps": float(rho_rps), "p_rps": float(p_rps),
                                       "rho_H_tier": float(rho_tier), "p_tier": float(p_tier)}
            print(f"  Fixed K={K}: ρ(H, RPS) = {rho_rps:+.4f} p={p_rps:.4f} | "
                  f"ρ(H, tier) = {rho_tier:+.4f} p={p_tier:.4f}")
        else:
            cross[f"fixed_K_{K}"] = {"K": K, "n_markets": int(mask.sum()), "status": "insufficient"}

    # Market-optimal K
    h_opt = []
    for cfg in MARKETS:
        opt_k = results.get(cfg["name"], {}).get("bic_optimal_K")
        if opt_k is None:
            h_opt.append(float("nan"))
            continue
        h_opt.append(results[cfg["name"]]["k_results"][f"K_{opt_k}"]["H_stat"])
    h_opt = np.array(h_opt)
    mask = ~np.isnan(h_opt)
    rho_opt_rps, p_opt_rps = spearmanr(h_opt[mask], rps_arr[mask])
    rho_opt_tier, p_opt_tier = spearmanr(h_opt[mask], tier_arr[mask])
    cross["market_optimal_K"] = {"n_markets": int(mask.sum()),
                                   "rho_H_rps": float(rho_opt_rps), "p_rps": float(p_opt_rps),
                                   "rho_H_tier": float(rho_opt_tier), "p_tier": float(p_opt_tier)}
    print(f"\n  Market-optimal K_m: ρ(H, RPS) = {rho_opt_rps:+.4f} p={p_opt_rps:.4f} | "
          f"ρ(H, tier) = {rho_opt_tier:+.4f} p={p_opt_tier:.4f}")

    payload = {
        "spec": "GMM K-selection per market sensitivity",
        "k_candidates": K_CANDIDATES,
        "n_markets": len(MARKETS),
        "horizon": PRIMARY_HORIZON,
        "seed": RNG_SEED,
        "elapsed_seconds": float(time.time() - t_start),
        "per_market": results,
        "cross_market": cross,
    }
    out_path = os.path.join(OUTPUT_DIR, "gmm_k_sensitivity.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
