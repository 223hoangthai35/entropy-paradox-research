"""H2 cascade re-run on n=27 panel with CORRECTED P1/P2/P3 classification.

Key correction: BVB Romania reclassified from P3 (Beta posterior heuristic, mean 0.40)
→ P2 Uniform[0.20, 0.25] with BVB IR + ASF Romania authoritative trading-value-weighted
retail share source (per round-18 panel correction).

Phase distribution:
  Old (frozen): 5 P1 + 2 P2 + 20 P3
  New (corrected): 5 P1 + 3 P2 + 19 P3

Reads H_stat values from h2_eta_squared_n27.json (price-data-derived, independent of RPS).
Applies corrected cascade classification + Monte Carlo + outputs deterministic + cascade
+ within-tier Spearman analysis.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.stats import spearmanr

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

N_MC = 10000
SEED = 42
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results_v2", "n27_experiment")
INPUT_H2 = os.path.join(RESULTS_DIR, "h2_eta_squared_n27.json")
OUTPUT_CASCADE = os.path.join(RESULTS_DIR, "h2_cascade_n27_corrected.json")

# ==============================================================================
# Cascade classification (CORRECTED post round-18)
# ==============================================================================
# P1: deterministic point estimate (authoritative source)
# P2: Uniform[lo, hi] (competing-source bounds)
# P3: Beta(alpha, beta) (Bayesian posterior, kappa=alpha+beta=20 default)

P1_MARKETS = {
    "VNINDEX": 0.90,   # Vietnam SSC + VinaCapital
    "PSEI":    0.68,   # PSE 2023 Annual Report
    "KOSPI":   0.45,   # KRX 2026 direct (cascade-corrected)
    "NIFTY":   0.40,   # NSE Ownership Report
    "NIKKEI":  0.18,   # JPX Trading-by-Investor-Type direct
}

P2_MARKETS = {
    "BVB":  (0.20, 0.25),  # CORRECTED: BVB IR + ASF Romania (round-18)
    "SPX":  (0.18, 0.37),  # SIFMA ownership + MEMX order flow
    "FTSE": (0.15, 0.25),  # UK FCA + LSE estimates
}

# P3: Beta(α, β) parameterised by mean μ and concentration κ = α+β
# α = μ·κ, β = (1−μ)·κ
def beta_params(mean: float, kappa: float = 20.0) -> tuple[float, float]:
    alpha = mean * kappa
    beta = (1 - mean) * kappa
    return alpha, beta

# All P3 markets use Beta posterior with the deterministic point as MEAN
P3_MARKETS = {
    # Frontier Beta heuristic
    "KSE100":  beta_params(0.60, 20),
    "DSEX":    beta_params(0.55, 20),
    "SBITOP":  beta_params(0.30, 20),
    "OMXVGI":  beta_params(0.30, 20),
    "OMXRGI":  beta_params(0.35, 20),
    "MERV":    beta_params(0.55, 20),
    # Asian Emerging Beta heuristic
    "JKSE":    beta_params(0.40, 20),
    "SET":     beta_params(0.35, 20),
    "SHANGHAI": beta_params(0.65, 20),
    "TWII":    beta_params(0.40, 20),
    # Crypto Beta posterior
    "BTC":     beta_params(0.55, 20),
    "ETH":     beta_params(0.55, 20),
    "BNB":     beta_params(0.60, 20),
    # Asian Developed Beta heuristic
    "DAX":     beta_params(0.20, 20),
    "CAC":     beta_params(0.20, 20),
    "SSMI":    beta_params(0.15, 20),
    "ASX":     beta_params(0.30, 20),
    "HSI":     beta_params(0.35, 20),
    "STI":     beta_params(0.25, 20),
}

# All-P1 deterministic reference values (point estimates for each market)
ALL_P1_REF = {**P1_MARKETS}
for m, (lo, hi) in P2_MARKETS.items():
    ALL_P1_REF[m] = (lo + hi) / 2.0  # midpoint
for m, (alpha, beta) in P3_MARKETS.items():
    ALL_P1_REF[m] = alpha / (alpha + beta)  # Beta mean


def main() -> int:
    with open(INPUT_H2, 'r', encoding='utf-8') as f:
        h2 = json.load(f)

    market_names = list(h2['per_market'].keys())
    H_raw = np.array([h2['per_market'][m]['raw']['H_stat'] for m in market_names])
    H_filt = np.array([h2['per_market'][m]['filtered']['H_stat'] for m in market_names])

    n_markets = len(market_names)
    assert n_markets == 27, f"Expected 27 markets, got {n_markets}"

    # Phase distribution
    n_p1 = sum(1 for m in market_names if m in P1_MARKETS)
    n_p2 = sum(1 for m in market_names if m in P2_MARKETS)
    n_p3 = sum(1 for m in market_names if m in P3_MARKETS)

    print("=" * 90)
    print("H2 CASCADE RE-RUN ON n=27 PANEL — CORRECTED P1/P2/P3 CLASSIFICATION")
    print("=" * 90)
    print(f"\nPhase distribution: {n_p1} P1 + {n_p2} P2 + {n_p3} P3 = {n_markets}")
    print(f"  P1 markets: {sorted(P1_MARKETS.keys())}")
    print(f"  P2 markets: {sorted(P2_MARKETS.keys())} (BVB CORRECTED)")
    print(f"  P3 markets: {sorted(P3_MARKETS.keys())} ({len(P3_MARKETS)} markets)")

    # === Deterministic all-P1 reference ===
    rps_p1ref = np.array([ALL_P1_REF[m] for m in market_names])
    rho_raw_p1, p_raw_p1 = spearmanr(H_raw, rps_p1ref)
    rho_filt_p1, p_filt_p1 = spearmanr(H_filt, rps_p1ref)

    print(f"\n--- All-P1 deterministic reference (point estimates) ---")
    print(f"  rho(H_raw, RPS_p1ref)  = {rho_raw_p1:+.4f}, p = {p_raw_p1:.4f}")
    print(f"  rho(H_filt, RPS_p1ref) = {rho_filt_p1:+.4f}, p = {p_filt_p1:.4f}")

    # === Cascade Monte Carlo (10000 trials) ===
    rng = np.random.default_rng(SEED)
    rho_raw_trials = np.zeros(N_MC)
    rho_filt_trials = np.zeros(N_MC)

    for t in range(N_MC):
        rps_trial = np.zeros(n_markets)
        for i, m in enumerate(market_names):
            if m in P1_MARKETS:
                rps_trial[i] = P1_MARKETS[m]
            elif m in P2_MARKETS:
                lo, hi = P2_MARKETS[m]
                rps_trial[i] = rng.uniform(lo, hi)
            elif m in P3_MARKETS:
                alpha, beta = P3_MARKETS[m]
                rps_trial[i] = rng.beta(alpha, beta)
        rho_raw_trials[t], _ = spearmanr(H_raw, rps_trial)
        rho_filt_trials[t], _ = spearmanr(H_filt, rps_trial)

    print(f"\n--- Cascade Monte Carlo ({N_MC} trials, seed = {SEED}) ---")
    print(f"\nRaw labels:")
    print(f"  Mean rho     = {rho_raw_trials.mean():+.4f}")
    print(f"  Median       = {np.median(rho_raw_trials):+.4f}")
    print(f"  95% CI       = [{np.percentile(rho_raw_trials, 2.5):+.4f}, {np.percentile(rho_raw_trials, 97.5):+.4f}]")
    print(f"  P(rho > 0.5) = {(rho_raw_trials > 0.5).mean()*100:.1f}%")
    print(f"  P(rho > 0.7) = {(rho_raw_trials > 0.7).mean()*100:.1f}%")

    print(f"\nFiltered labels:")
    print(f"  Mean rho     = {rho_filt_trials.mean():+.4f}")
    print(f"  Median       = {np.median(rho_filt_trials):+.4f}")
    print(f"  95% CI       = [{np.percentile(rho_filt_trials, 2.5):+.4f}, {np.percentile(rho_filt_trials, 97.5):+.4f}]")
    print(f"  P(rho > 0.5) = {(rho_filt_trials > 0.5).mean()*100:.1f}%")
    print(f"  P(rho > 0.7) = {(rho_filt_trials > 0.7).mean()*100:.1f}%")

    # === Within-tier breakdown (using ALL_P1_REF point estimates) ===
    # Tier from h1 file
    with open(os.path.join(RESULTS_DIR, "h1_dml_cpcv_n27.json"), 'r', encoding='utf-8') as f:
        h1 = json.load(f)
    tier = np.array([h1['results'][m]['tier_rank'] for m in market_names])

    print(f"\n--- Cross-market with corrected BVB ---")
    rho_raw_all, p_raw_all = spearmanr(H_raw, rps_p1ref)
    rho_filt_all, p_filt_all = spearmanr(H_filt, rps_p1ref)
    rho_raw_tier, p_raw_tier = spearmanr(H_raw, tier)
    rho_filt_tier, p_filt_tier = spearmanr(H_filt, tier)
    print(f"  rho(H_raw, RPS, all-P1)  = {rho_raw_all:+.4f}, p = {p_raw_all:.4f}")
    print(f"  rho(H_filt, RPS, all-P1) = {rho_filt_all:+.4f}, p = {p_filt_all:.4f}")
    print(f"  rho(H_raw, tier)         = {rho_raw_tier:+.4f}, p = {p_raw_tier:.4f}")
    print(f"  rho(H_filt, tier)        = {rho_filt_tier:+.4f}, p = {p_filt_tier:.4f}")

    # Within-tier
    print(f"\n--- Within-tier rho(H, RPS) with CORRECTED BVB ---")
    for t in [4, 3, 2, 1]:
        cat = {4: 'Frontier', 3: 'Asian Emerging', 2: 'Crypto', 1: 'Developed'}[t]
        idx = np.where(tier == t)[0]
        if len(idx) >= 4:
            r1, p1 = spearmanr(H_raw[idx], rps_p1ref[idx])
            r2, p2 = spearmanr(H_filt[idx], rps_p1ref[idx])
            print(f"  {cat:<18} (n={len(idx)}): rho_raw = {r1:+.4f} (p={p1:.4f}), rho_filt = {r2:+.4f} (p={p2:.4f})")
        else:
            print(f"  {cat:<18} (n={len(idx)}): too small for Spearman")

    # === Save corrected output ===
    output = {
        "spec": "H2 cascade re-run n=27 with BVB P2 corrected (round-18 consistency)",
        "panel_n": n_markets,
        "cascade_phases": {
            "P1": {"count": n_p1, "markets": sorted(P1_MARKETS.keys())},
            "P2": {"count": n_p2, "markets": sorted(P2_MARKETS.keys()),
                   "BVB_correction": "P3 Beta(0.40, 20) → P2 Uniform[0.20, 0.25] per round-18 BVB IR + ASF Romania authoritative source"},
            "P3": {"count": n_p3, "markets": sorted(P3_MARKETS.keys())},
        },
        "n_mc": N_MC,
        "seed": SEED,
        "all_p1_reference": {
            "rps_values": {m: float(ALL_P1_REF[m]) for m in market_names},
            "rho_H_raw": float(rho_raw_all),
            "p_H_raw": float(p_raw_all),
            "rho_H_filt": float(rho_filt_all),
            "p_H_filt": float(p_filt_all),
        },
        "cascade_composite": {
            "raw": {
                "mean": float(rho_raw_trials.mean()),
                "median": float(np.median(rho_raw_trials)),
                "p025": float(np.percentile(rho_raw_trials, 2.5)),
                "p975": float(np.percentile(rho_raw_trials, 97.5)),
                "P_rho_gt_0p5": float((rho_raw_trials > 0.5).mean()),
                "P_rho_gt_0p7": float((rho_raw_trials > 0.7).mean()),
            },
            "filtered": {
                "mean": float(rho_filt_trials.mean()),
                "median": float(np.median(rho_filt_trials)),
                "p025": float(np.percentile(rho_filt_trials, 2.5)),
                "p975": float(np.percentile(rho_filt_trials, 97.5)),
                "P_rho_gt_0p5": float((rho_filt_trials > 0.5).mean()),
                "P_rho_gt_0p7": float((rho_filt_trials > 0.7).mean()),
            },
        },
        "tier_spearman": {
            "rho_H_raw_tier": float(rho_raw_tier),
            "p_H_raw_tier": float(p_raw_tier),
            "rho_H_filt_tier": float(rho_filt_tier),
            "p_H_filt_tier": float(p_filt_tier),
        },
    }

    with open(OUTPUT_CASCADE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nWrote corrected cascade output: {OUTPUT_CASCADE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
