"""
One-shot augmentation: add ρ(H, RPS) to existing frozen gmm_k_sensitivity.json.

Reads H values per market per K from the frozen JSON (no GMM re-fit),
applies the all-P1 reference RPS vector, computes Spearman ρ(H, RPS) per
fixed K and market-optimal K, and writes the augmented JSON back in place.

This script exists because the frozen JSON predates the §4.2.1 reframe
(RPS-rank primary, tier-rank robustness). After future re-runs of
gmm_k_sensitivity.py (which now includes RPS), this script becomes
redundant — re-running it is idempotent.

RPS vector matches Table 1 / §4.2.1 cascade composite Mean equivalent for
rank-correlation purposes.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.stats import spearmanr

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

RPS = {
    "VNINDEX": 0.90,
    "BVB": 0.225,
    "KOSPI":   0.45,
    "NIFTY":   0.40,
    "BTC":     0.55,
    "SPX":     0.275,
    "FTSE":    0.20,
    "NIKKEI":  0.18,
}

JSON_PATH = os.path.join(os.path.dirname(__file__), "results_v2", "gmm_k_sensitivity.json")


def main() -> int:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    per_market = payload["per_market"]
    market_names = list(per_market.keys())
    rps_arr = np.array([RPS[m] for m in market_names])
    tier_arr = np.array([per_market[m]["tier_rank"] for m in market_names])

    for m in market_names:
        per_market[m]["rps"] = RPS[m]

    cross = payload["cross_market"]
    k_candidates = payload["k_candidates"]

    print("=" * 70)
    print("  AUGMENT: ρ(H, RPS) primary + ρ(H, tier) robustness per K")
    print("=" * 70)

    for K in k_candidates:
        h_arr = np.array([per_market[m]["k_results"][f"K_{K}"]["H_stat"] for m in market_names])
        mask = ~np.isnan(h_arr)
        rho_rps, p_rps = spearmanr(h_arr[mask], rps_arr[mask])
        rho_tier, p_tier = spearmanr(h_arr[mask], tier_arr[mask])
        key = f"fixed_K_{K}"
        cross[key]["rho_H_rps"] = float(rho_rps)
        cross[key]["p_rps"] = float(p_rps)
        cross[key]["rho_H_tier"] = float(rho_tier)
        cross[key]["p_tier"] = float(p_tier)
        if "p" in cross[key]:
            del cross[key]["p"]
        print(f"  K={K}: ρ(H,RPS)={rho_rps:+.4f} p={p_rps:.4f} | ρ(H,tier)={rho_tier:+.4f} p={p_tier:.4f}")

    h_opt = []
    for m in market_names:
        opt_k = per_market[m]["bic_optimal_K"]
        h_opt.append(per_market[m]["k_results"][f"K_{opt_k}"]["H_stat"])
    h_opt = np.array(h_opt)
    mask = ~np.isnan(h_opt)
    rho_opt_rps, p_opt_rps = spearmanr(h_opt[mask], rps_arr[mask])
    rho_opt_tier, p_opt_tier = spearmanr(h_opt[mask], tier_arr[mask])
    cross["market_optimal_K"]["rho_H_rps"] = float(rho_opt_rps)
    cross["market_optimal_K"]["p_rps"] = float(p_opt_rps)
    cross["market_optimal_K"]["rho_H_tier"] = float(rho_opt_tier)
    cross["market_optimal_K"]["p_tier"] = float(p_opt_tier)
    if "p" in cross["market_optimal_K"]:
        del cross["market_optimal_K"]["p"]
    print(f"\n  Market-optimal K_m: ρ(H,RPS)={rho_opt_rps:+.4f} p={p_opt_rps:.4f} | "
          f"ρ(H,tier)={rho_opt_tier:+.4f} p={p_opt_tier:.4f}")

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nWrote: {JSON_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
