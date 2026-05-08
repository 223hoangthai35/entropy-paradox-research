"""
H2 PRIMARY (E1 reframing) — Tier-based H ordering test.

Replaces the continuous-RPS Spearman test as the *primary* H2 specification.
Uses MSCI / FTSE Russell market classification as the ordered grouping
variable, so the headline test does not depend on the per-market RPS
data quality (which is heterogeneous across exchanges — see §3.5.3).

Tests:
  1. Spearman rho(H, retail_dominance_score) where retail_dominance_score
     = 4 (Frontier) > 3 (Emerging) > 2 (Crypto) > 1 (Developed).
  2. Jonckheere-Terpstra trend statistic (ordered alternative).
  3. Kruskal-Wallis H across tier groups.

The retail-dominance ordering of tiers is the prior hypothesis from the
per-participant-type information literature (§2.3); the test asks whether
the entropy-derived discrimination magnitude (KW H) is monotonically
ordered with tier.
"""
from __future__ import annotations

import json
import os
import sys
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import kruskal, spearmanr

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
PRIMARY_CSV = os.path.join(OUTPUT_DIR, "cross_market_summary_v2.csv")

# Tier classification per FTSE Russell + MSCI conventions
# Note: VNINDEX is FTSE Frontier through Sept 2026; KOSPI is MSCI Emerging
#       (FTSE classifies Korea as Developed); we follow MSCI for KOSPI.
TIER: dict[str, str] = {
    "VNINDEX": "Frontier",
    "PSEI": "Frontier",
    "KOSPI": "Emerging",
    "NIFTY": "Emerging",
    "BTC": "Crypto",
    "SPX": "Developed",
    "FTSE": "Developed",
    "NIKKEI": "Developed",
}

# Retail-dominance score: higher = more retail-dominant
# (Frontier > Emerging > Crypto > Developed, per §2.3 literature)
TIER_SCORE: dict[str, int] = {
    "Frontier": 4,
    "Emerging": 3,
    "Crypto": 2,
    "Developed": 1,
}


def load_h_stats() -> pd.DataFrame:
    df = pd.read_csv(PRIMARY_CSV)
    cols = ["market", "H_stat"]
    if "H_stat_filtered" in df.columns:
        cols.append("H_stat_filtered")
    return df[cols].copy()


def jonckheere_terpstra(groups: list[np.ndarray]) -> dict[str, float]:
    """Jonckheere-Terpstra trend test for ordered alternative.

    H0: distributions identical across groups.
    H1: distributions ordered (group 1 stochastically smaller than group 2,
        etc.) — i.e., group means monotonically ordered.

    Statistic JT = sum over all i<j of U_ij (Mann-Whitney U for group i vs j).
    Under H0, JT has known mean and variance (large-sample normal approx).

    Args:
        groups: list of arrays in the order tested for monotonic trend
                (group[0] expected smallest if increasing alternative).

    Returns:
        {'JT': statistic, 'mean_h0': expected JT under H0, 'var_h0': variance,
         'z': standardized z, 'p_one_sided_increasing': p-value for H1: ordered
         increasing}.
    """
    k = len(groups)
    sizes = [len(g) for g in groups]
    n = sum(sizes)

    # JT statistic = sum over i<j of U_ij where U_ij = #{(x,y) : x in g_i, y in g_j, x < y}
    # plus 0.5 * #{ties}
    jt = 0.0
    for i, j in combinations(range(k), 2):
        gi = groups[i]
        gj = groups[j]
        for xi in gi:
            for yj in gj:
                if xi < yj:
                    jt += 1
                elif xi == yj:
                    jt += 0.5

    # Under H0 (large sample approximation):
    mean_h0 = (n ** 2 - sum(s ** 2 for s in sizes)) / 4.0
    var_h0 = (n ** 2 * (2 * n + 3) - sum(s ** 2 * (2 * s + 3) for s in sizes)) / 72.0

    if var_h0 > 0:
        z = (jt - mean_h0) / np.sqrt(var_h0)
        # one-sided p-value for increasing alternative
        from scipy.stats import norm
        p_one_sided = 1.0 - norm.cdf(z)
    else:
        z = float("nan")
        p_one_sided = float("nan")

    return {
        "JT_statistic": float(jt),
        "mean_under_H0": float(mean_h0),
        "variance_under_H0": float(var_h0),
        "z_score": float(z),
        "p_value_one_sided_increasing": float(p_one_sided),
        "n_groups": k,
        "group_sizes": sizes,
        "n_total": n,
    }


def tier_test(H_values: dict[str, float], label: str) -> dict[str, Any]:
    print(f"\n{'='*70}\n  {label}\n{'='*70}")
    markets = list(H_values.keys())
    h_arr = np.array([H_values[m] for m in markets])
    score_arr = np.array([TIER_SCORE[TIER[m]] for m in markets])

    # 1. Spearman correlation
    rho, p_rho = spearmanr(h_arr, score_arr)
    print(f"\n  [1] Spearman rho(H, retail_score):")
    print(f"      rho = {rho:+.4f}   p = {p_rho:.4g}   n = {len(markets)}")

    # 2. Tier-grouped data for Jonckheere-Terpstra (ordered: Developed -> Crypto -> Emerging -> Frontier)
    # Test H1: H values increase with retail dominance (= decrease with TIER_SCORE direction)
    # JT default tests increasing; we order groups as Developed (lowest H expected)
    # then Crypto, Emerging, Frontier (highest H expected)
    tier_order = ["Developed", "Crypto", "Emerging", "Frontier"]
    groups = []
    for tier in tier_order:
        markets_in_tier = [m for m in markets if TIER[m] == tier]
        h_in_tier = [H_values[m] for m in markets_in_tier]
        groups.append(np.array(h_in_tier))
        print(f"      {tier:<10}: n={len(markets_in_tier)}  H values = {h_in_tier}  mean = {np.mean(h_in_tier):.2f}")

    jt = jonckheere_terpstra(groups)
    print(f"\n  [2] Jonckheere-Terpstra trend test (H1: H increases with tier from Developed to Frontier):")
    print(f"      JT = {jt['JT_statistic']:.1f}   E[JT|H0] = {jt['mean_under_H0']:.1f}   z = {jt['z_score']:+.3f}")
    print(f"      p (one-sided) = {jt['p_value_one_sided_increasing']:.4g}")

    # 3. Kruskal-Wallis across tier groups
    kw_stat, kw_p = kruskal(*groups)
    print(f"\n  [3] Kruskal-Wallis H across tier groups:")
    print(f"      H = {kw_stat:.4f}   p = {kw_p:.4g}   df = {len(groups)-1}")

    # Tier means
    tier_means = {tier: float(np.mean([H_values[m] for m in markets if TIER[m] == tier]))
                  for tier in tier_order}
    print(f"\n  Tier-mean H values:")
    for t in tier_order:
        print(f"      {t:<10}: {tier_means[t]:.3f}")

    return {
        "spearman": {"rho": float(rho), "p_value": float(p_rho), "n": int(len(markets))},
        "jonckheere_terpstra": jt,
        "kruskal_wallis": {"H_statistic": float(kw_stat), "p_value": float(kw_p), "df": len(groups) - 1},
        "tier_means": tier_means,
        "tier_classification": {m: TIER[m] for m in markets},
    }


def main() -> int:
    df_h = load_h_stats()
    H_raw = {row["market"]: float(row["H_stat"]) for _, row in df_h.iterrows()}
    H_filt = ({row["market"]: float(row["H_stat_filtered"]) for _, row in df_h.iterrows()}
              if "H_stat_filtered" in df_h.columns else None)

    print("=" * 70)
    print("  H2 TIER-BASED PRIMARY TEST (E1 reframing)")
    print("=" * 70)
    print("  Tier ordering: Frontier > Emerging > Crypto > Developed")
    print("  (retail dominance, per per-participant-type information literature)")

    raw_results = tier_test(H_raw, "RAW GMM LABELS")
    filt_results = tier_test(H_filt, "HYSTERESIS-FILTERED LABELS") if H_filt else None

    # Summary
    print(f"\n{'='*70}\n  HEADLINE SUMMARY\n{'='*70}")
    print(f"  RAW:")
    print(f"    Spearman rho(H, tier_score) = {raw_results['spearman']['rho']:+.4f}  p = {raw_results['spearman']['p_value']:.4g}")
    print(f"    Jonckheere-Terpstra z = {raw_results['jonckheere_terpstra']['z_score']:+.3f}  p = {raw_results['jonckheere_terpstra']['p_value_one_sided_increasing']:.4g}")
    print(f"    Kruskal-Wallis H = {raw_results['kruskal_wallis']['H_statistic']:.3f}  p = {raw_results['kruskal_wallis']['p_value']:.4g}")
    if filt_results:
        print(f"  FILTERED:")
        print(f"    Spearman rho(H, tier_score) = {filt_results['spearman']['rho']:+.4f}  p = {filt_results['spearman']['p_value']:.4g}")
        print(f"    Jonckheere-Terpstra z = {filt_results['jonckheere_terpstra']['z_score']:+.3f}  p = {filt_results['jonckheere_terpstra']['p_value_one_sided_increasing']:.4g}")
        print(f"    Kruskal-Wallis H = {filt_results['kruskal_wallis']['H_statistic']:.3f}  p = {filt_results['kruskal_wallis']['p_value']:.4g}")

    payload = {
        "spec": "H2 PRIMARY E1 reframing — tier-based H ordering test",
        "tier_classification": TIER,
        "tier_ordering_rationale": "Frontier > Emerging > Crypto > Developed (retail dominance, per Boehmer-Kelley 2009, Chang 2024, Kang 2026)",
        "raw_results": raw_results,
        "filtered_results": filt_results,
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_tier_based.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
