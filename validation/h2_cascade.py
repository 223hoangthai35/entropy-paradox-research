"""
H2 CASCADE TEST - 3-phase per-market data quality cascade for RPS.

Replaces previous parallel multi-method (uniform bounds + Bayesian) with a
single composite Monte Carlo test that applies per-market RPS treatment
according to data quality:

  P1 (authoritative single primary source): point estimate, no sampling
  P2 (no single authoritative source, bounded by competing sources): uniform
      sampling within plausible bounds
  P3 (source conflict or no aggregator): Bayesian posterior sampling

Per-market classification:
  P1: VNINDEX, KOSPI, NIFTY, NIKKEI
  P2: SPX, FTSE
  P3: PSEI (Beta mixture), BTC (Beta wide)

Output: results_v2/h2_cascade.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
PRIMARY_CSV = os.path.join(OUTPUT_DIR, "cross_market_summary_v2.csv")

# Per-market cascade specifications (filter: each market at ONE phase based on
# whether authoritative source is available; downgraded only if filter fails)
CASCADE: dict[str, dict] = {
    "VNINDEX": {"tier": "P1", "type": "point", "value": 0.90,
                "source": "Vietnam SSC + VinaCapital (authoritative source available)"},
    "PSEI": {"tier": "P1", "type": "point", "value": 0.68,
             "source": "PSE 2023 Annual Report (authoritative exchange document)"},
    "KOSPI": {"tier": "P1", "type": "point", "value": 0.45,
              "source": "KRX 2026 direct turnover-by-investor-type marketplace"},
    "NIFTY": {"tier": "P1", "type": "point", "value": 0.40,
              "source": "NSE India Ownership Report (authoritative)"},
    "SPX": {"tier": "P2", "type": "uniform", "low": 0.18, "high": 0.37,
            "source": "P1 fails: SIFMA ownership (0.18) vs MEMX order flow (0.30-0.37) metric disagreement; P2 bounds applied"},
    "FTSE": {"tier": "P2", "type": "uniform", "low": 0.15, "high": 0.25,
             "source": "P1 fails: UK FCA limited public data; P2 bounds applied"},
    "NIKKEI": {"tier": "P1", "type": "point", "value": 0.18,
               "source": "JPX Trading-by-Investor-Type direct (authoritative)"},
    "BTC": {"tier": "P3", "type": "beta", "mean": 0.55, "kappa": 20,
            "source": "P1+P2 fail: no central exchange, no authoritative aggregator; P3 Bayesian centered on pre-reg 0.55"},
}

N_MC = 10_000
SEED = 42


def load_h_stats() -> pd.DataFrame:
    df = pd.read_csv(PRIMARY_CSV)
    cols = ["market", "H_stat"]
    if "H_stat_filtered" in df.columns:
        cols.append("H_stat_filtered")
    return df[cols].copy()


def sample_rps_cascade(market: str, rng: np.random.Generator) -> float:
    """Sample one RPS value per market according to its cascade tier."""
    spec = CASCADE[market]
    t = spec["type"]
    if t == "point":
        return float(spec["value"])
    if t == "uniform":
        return float(rng.uniform(spec["low"], spec["high"]))
    if t == "beta":
        alpha = spec["kappa"] * spec["mean"]
        beta = spec["kappa"] * (1 - spec["mean"])
        return float(rng.beta(alpha, beta))
    if t == "mixture":
        weights = np.array([c["weight"] for c in spec["components"]])
        idx = rng.choice(len(weights), p=weights)
        c = spec["components"][idx]
        alpha = c["kappa"] * c["mean"]
        beta = c["kappa"] * (1 - c["mean"])
        return float(rng.beta(alpha, beta))
    raise ValueError(f"Unknown cascade type: {t}")


def cascade_mc(H_dict: dict[str, float], n_mc: int = N_MC, seed: int = SEED) -> dict:
    """Composite cascade Monte Carlo: per-market RPS sampling per tier, integrated."""
    rng = np.random.default_rng(seed)
    markets = list(H_dict.keys())
    H_arr = np.array([H_dict[m] for m in markets])
    rhos = np.empty(n_mc)
    p_values = np.empty(n_mc)
    for i in range(n_mc):
        rps_sample = np.array([sample_rps_cascade(m, rng) for m in markets])
        rho, p = stats.spearmanr(H_arr, rps_sample)
        rhos[i] = rho
        p_values[i] = p

    return {
        "n_trials": n_mc,
        "mean": float(np.mean(rhos)),
        "median": float(np.median(rhos)),
        "sd": float(np.std(rhos, ddof=1)),
        "p025": float(np.percentile(rhos, 2.5)),
        "p05": float(np.percentile(rhos, 5)),
        "p25": float(np.percentile(rhos, 25)),
        "p75": float(np.percentile(rhos, 75)),
        "p95": float(np.percentile(rhos, 95)),
        "p975": float(np.percentile(rhos, 97.5)),
        "min": float(np.min(rhos)),
        "max": float(np.max(rhos)),
        "P_rho_gt_0p5": float(np.mean(rhos > 0.5)),
        "P_rho_gt_0p7": float(np.mean(rhos > 0.7)),
        "P_p_lt_0p05": float(np.mean(p_values < 0.05)),
        "P_p_lt_0p10": float(np.mean(p_values < 0.10)),
    }


def main() -> int:
    df_h = load_h_stats()
    H_raw = {row["market"]: float(row["H_stat"]) for _, row in df_h.iterrows()}
    H_filt = ({row["market"]: float(row["H_stat_filtered"]) for _, row in df_h.iterrows()}
              if "H_stat_filtered" in df_h.columns else None)

    print("=" * 70)
    print("  H2 CASCADE TEST (P1 -> P2 -> P3 per-market data quality)")
    print("=" * 70)

    # Print cascade classification
    print("\n  Per-market cascade classification:")
    print(f"  {'market':<10}  {'tier':<4}  {'type':<8}  {'parameter(s)':<35}")
    for m in H_raw.keys():
        spec = CASCADE[m]
        if spec["type"] == "point":
            param = f"point = {spec['value']:.3f}"
        elif spec["type"] == "uniform":
            param = f"U[{spec['low']:.3f}, {spec['high']:.3f}]"
        elif spec["type"] == "beta":
            param = f"Beta(mean={spec['mean']:.3f}, kappa={spec['kappa']})"
        elif spec["type"] == "mixture":
            param = "Beta mixture (bimodal)"
        else:
            param = "?"
        print(f"  {m:<10}  {spec['tier']:<4}  {spec['type']:<8}  {param:<35}")

    raw = cascade_mc(H_raw)
    filt = cascade_mc(H_filt) if H_filt else None

    print(f"\n  RAW specification (10,000 cascade MC trials):")
    print(f"    rho mean = {raw['mean']:+.4f}   median = {raw['median']:+.4f}   sd = {raw['sd']:.3f}")
    print(f"    95% CI   = [{raw['p025']:+.4f}, {raw['p975']:+.4f}]")
    print(f"    50% CI   = [{raw['p25']:+.4f}, {raw['p75']:+.4f}]")
    print(f"    range    = [{raw['min']:+.4f}, {raw['max']:+.4f}]")
    print(f"    P(rho > 0.5)   = {raw['P_rho_gt_0p5']*100:.1f}%")
    print(f"    P(rho > 0.7)   = {raw['P_rho_gt_0p7']*100:.1f}%")
    print(f"    P(p < 0.05)    = {raw['P_p_lt_0p05']*100:.1f}%")
    print(f"    P(p < 0.10)    = {raw['P_p_lt_0p10']*100:.1f}%")

    if filt:
        print(f"\n  FILTERED specification:")
        print(f"    rho mean = {filt['mean']:+.4f}   median = {filt['median']:+.4f}   sd = {filt['sd']:.3f}")
        print(f"    95% CI   = [{filt['p025']:+.4f}, {filt['p975']:+.4f}]")
        print(f"    50% CI   = [{filt['p25']:+.4f}, {filt['p75']:+.4f}]")
        print(f"    range    = [{filt['min']:+.4f}, {filt['max']:+.4f}]")
        print(f"    P(rho > 0.5)   = {filt['P_rho_gt_0p5']*100:.1f}%")
        print(f"    P(rho > 0.7)   = {filt['P_rho_gt_0p7']*100:.1f}%")
        print(f"    P(p < 0.05)    = {filt['P_p_lt_0p05']*100:.1f}%")
        print(f"    P(p < 0.10)    = {filt['P_p_lt_0p10']*100:.1f}%")

    # Phase distribution counts
    n_p1 = sum(1 for s in CASCADE.values() if s["tier"] == "P1")
    n_p2 = sum(1 for s in CASCADE.values() if s["tier"] == "P2")
    n_p3 = sum(1 for s in CASCADE.values() if s["tier"] == "P3")
    print(f"\n  Phase distribution: P1 = {n_p1}, P2 = {n_p2}, P3 = {n_p3}")

    payload = {
        "spec": "H2 CASCADE TEST - per-market 3-phase data quality cascade (P1 point / P2 uniform / P3 Bayesian)",
        "cascade_specification": CASCADE,
        "phase_distribution": {"P1": n_p1, "P2": n_p2, "P3": n_p3},
        "n_mc_trials": N_MC,
        "seed": SEED,
        "raw_cascade": raw,
        "filtered_cascade": filt,
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_cascade.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
