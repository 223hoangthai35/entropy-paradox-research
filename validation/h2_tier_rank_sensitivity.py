"""
Tier-rank sensitivity: Crypto placement (Plan v9 §A.4, Major M-1).

Tests Spearman ρ(H, tier_rank) for each possible Crypto rank ∈ {1, 2, 3, 4, 5}
holding other tier ranks fixed. Goal: document robustness of cross-market H
ordering to the (somewhat arbitrary) Crypto placement decision.

Reads existing per-market H stats from cross_market_summary_v2.csv to avoid
recomputation.

Output: validation/results_v2/h2_tier_rank_sensitivity.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
SUMMARY_CSV = os.path.join(OUTPUT_DIR, "cross_market_summary_v2.csv")

# Fixed tier ranks per Hybrid C (matches h2_tier_based.py)
FIXED_RANKS = {
    "VNINDEX": 4, "PSEI": 4,        # Frontier
    "KOSPI": 3, "NIFTY": 3,         # Emerging
    "SPX": 1, "FTSE": 1, "NIKKEI": 1,  # Developed
    # BTC = variable (Crypto)
}

CRYPTO_RANKS_TO_TEST = [1, 2, 3, 4, 5]  # range of plausible Crypto placements


def main() -> int:
    print("=" * 70)
    print("  TIER-RANK SENSITIVITY: CRYPTO PLACEMENT")
    print("=" * 70)

    if not os.path.exists(SUMMARY_CSV):
        print(f"  ERROR: summary CSV not found: {SUMMARY_CSV}")
        print(f"  Run cross_market_v2.py first to generate it.")
        return 1

    df = pd.read_csv(SUMMARY_CSV)
    print(f"  Loaded {len(df)} rows from {SUMMARY_CSV}")
    print(f"  Columns: {list(df.columns)}")

    # Find required columns
    market_col = "market" if "market" in df.columns else "Market"
    h_raw_col = "H_stat" if "H_stat" in df.columns else "H_raw"
    h_filt_col = "H_stat_filtered" if "H_stat_filtered" in df.columns else None

    df = df.set_index(market_col)
    print(f"\n  Markets in CSV: {list(df.index)}")

    results = {}
    for label_name, h_col in [("raw", h_raw_col)] + ([("filtered", h_filt_col)] if h_filt_col else []):
        print(f"\n--- {label_name.upper()} labels (H from '{h_col}') ---")
        results[label_name] = {}
        for crypto_rank in CRYPTO_RANKS_TO_TEST:
            tier_ranks = []
            h_vals = []
            for m in df.index:
                if m in FIXED_RANKS:
                    tier_ranks.append(FIXED_RANKS[m])
                elif m == "BTC":
                    tier_ranks.append(crypto_rank)
                else:
                    print(f"    WARNING: {m} not in tier rank dict; skipping")
                    continue
                h_vals.append(df.loc[m, h_col])
            tier_ranks = np.array(tier_ranks)
            h_vals = np.array(h_vals)
            mask = ~np.isnan(h_vals)
            if mask.sum() < 4:
                results[label_name][f"crypto_rank_{crypto_rank}"] = {"status": "insufficient"}
                continue
            rho, p = spearmanr(h_vals[mask], tier_ranks[mask])
            results[label_name][f"crypto_rank_{crypto_rank}"] = {
                "crypto_rank": crypto_rank,
                "n_markets": int(mask.sum()),
                "rho_H_tier": float(rho), "p": float(p),
                "verdict": ("Decisive" if p < 0.05 else "n.s."),
            }
            print(f"  Crypto rank = {crypto_rank}: ρ(H, tier) = {rho:+.4f}  p = {p:.4f}  ({'Decisive' if p<0.05 else 'n.s.'})")

    print("\n" + "=" * 70)
    print("  ROBUSTNESS VERDICT")
    print("=" * 70)
    for label_name in results:
        rhos = [v["rho_H_tier"] for v in results[label_name].values() if "rho_H_tier" in v]
        ps = [v["p"] for v in results[label_name].values() if "p" in v]
        decisive_count = sum(1 for p in ps if p < 0.05)
        print(f"  {label_name.upper()}: ρ range [{min(rhos):+.3f}, {max(rhos):+.3f}], "
              f"{decisive_count}/{len(ps)} configurations decisive at p<0.05")

    payload = {
        "spec": "Tier-rank sensitivity: Crypto placement ∈ {1, 2, 3, 4, 5}",
        "fixed_ranks": FIXED_RANKS,
        "crypto_ranks_tested": CRYPTO_RANKS_TO_TEST,
        "results": results,
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_tier_rank_sensitivity.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
