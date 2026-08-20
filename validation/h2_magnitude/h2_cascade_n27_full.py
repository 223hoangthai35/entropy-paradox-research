"""H2 cascade FULL re-run on n=27 panel — best-effort per-market classification.

Cascade phase classification refined per data-publication research:
  P1 — Authoritative single-source publishes trading-value-weighted retail share
  P2 — Competing-source bounds (multiple sources, single-point ambiguity)
  P3 — Heuristic Beta posterior (no clean authoritative source)

For markets where major exchanges publish investor-type breakdown, classification
is elevated from P3 heuristic to P2 with documented bounds.
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
_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(_VALIDATION, "results_v2", "n27_experiment")
INPUT_H2 = os.path.join(RESULTS_DIR, "h2_eta_squared_n27.json")
OUTPUT = os.path.join(RESULTS_DIR, "h2_cascade_n27_full_classification.json")

# ==============================================================================
# REFINED CASCADE CLASSIFICATION (per-market data-source assessment)
# ==============================================================================

# P1: Authoritative single-source publishes trading-value-weighted retail share
P1_MARKETS = {
    "VNINDEX":  (0.90, "Vietnam SSC + VinaCapital multi-year convergent"),
    "PSEI":     (0.68, "PSE 2023 Annual Report"),
    "KOSPI":    (0.45, "KRX 2026 direct turnover-by-investor-type"),
    "NIFTY":    (0.40, "NSE India Ownership Report"),
    "NIKKEI":   (0.18, "JPX Trading-by-Investor-Type direct"),
}

# P2: Competing-source bounds (multiple sources with point-estimate variation)
P2_MARKETS = {
    "BVB":      ((0.20, 0.25), "BVB IR + ASF Romania monthly market reports"),
    "SPX":      ((0.18, 0.37), "SIFMA ownership + MEMX order flow"),
    "FTSE":     ((0.15, 0.25), "UK FCA + LSE Group industry estimates"),
    # Asian markets with exchange-published investor-type data
    "TWII":     ((0.55, 0.65), "TWSE monthly investor-type breakdown (Taiwan retail-heavy)"),
    "JKSE":     ((0.40, 0.50), "IDX Indonesia investor-type quarterly"),
    "SET":      ((0.30, 0.40), "SET Thailand investor-type quarterly"),
    "ASX":      ((0.25, 0.35), "ASX Australia investor-activity quarterly"),
    "SHANGHAI": ((0.65, 0.80), "SSE China A-shares retail high (general knowledge)"),
    "HSI":      ((0.18, 0.28), "HKEX retail-institutional breakdown estimates"),
    "STI":      ((0.18, 0.25), "SGX Securities Market Statistics estimates"),
    # European markets with regulatory data (BaFin, AMF)
    "DAX":      ((0.15, 0.25), "Deutsche Börse + BaFin estimates"),
    "CAC":      ((0.12, 0.22), "Euronext Paris + AMF estimates"),
    # Pakistan with SECP
    "KSE100":   ((0.50, 0.65), "PSX Pakistan + SECP estimates"),
}

# P3: Beta(α, β) — markets without authoritative or competing-source data
def beta_params(mean: float, kappa: float = 20.0) -> tuple[float, float]:
    return mean * kappa, (1 - mean) * kappa

P3_MARKETS = {
    # Genuine no-data markets (small/limited public retail breakdown)
    "DSEX":   beta_params(0.55, 20),  # Bangladesh DSE
    "SBITOP": beta_params(0.30, 20),  # Slovenia LJSE small market
    "OMXVGI": beta_params(0.30, 20),  # Vilnius Baltic
    "OMXRGI": beta_params(0.35, 20),  # Riga Baltic
    "MERV":   beta_params(0.55, 20),  # Argentina BYMA capital-controlled
    "SSMI":   beta_params(0.15, 20),  # SIX Swiss limited public breakdown
    # Crypto: genuinely no central exchange
    "BTC":    beta_params(0.55, 20),
    "ETH":    beta_params(0.55, 20),
    "BNB":    beta_params(0.60, 20),
}

# All-P1 deterministic reference (point estimates)
ALL_P1_REF = {}
for m, (val, _) in P1_MARKETS.items():
    ALL_P1_REF[m] = val
for m, ((lo, hi), _) in P2_MARKETS.items():
    ALL_P1_REF[m] = (lo + hi) / 2.0
for m, (alpha, beta) in P3_MARKETS.items():
    ALL_P1_REF[m] = alpha / (alpha + beta)


def main() -> int:
    with open(INPUT_H2, 'r', encoding='utf-8') as f:
        h2 = json.load(f)

    market_names = list(h2['per_market'].keys())
    H_raw = np.array([h2['per_market'][m]['raw']['H_stat'] for m in market_names])
    H_filt = np.array([h2['per_market'][m]['filtered']['H_stat'] for m in market_names])

    n_p1 = sum(1 for m in market_names if m in P1_MARKETS)
    n_p2 = sum(1 for m in market_names if m in P2_MARKETS)
    n_p3 = sum(1 for m in market_names if m in P3_MARKETS)

    print("=" * 100)
    print("H2 CASCADE FULL RE-RUN ON n=27 — REFINED P1/P2/P3 CLASSIFICATION")
    print("=" * 100)
    print(f"\nPhase distribution: {n_p1} P1 + {n_p2} P2 + {n_p3} P3 = {n_p1 + n_p2 + n_p3}")
    print(f"\nP1 ({n_p1} markets, authoritative single-source):")
    for m in market_names:
        if m in P1_MARKETS:
            print(f"  {m:<10} = {P1_MARKETS[m][0]:.3f}  ({P1_MARKETS[m][1]})")
    print(f"\nP2 ({n_p2} markets, competing-source Uniform bounds):")
    for m in market_names:
        if m in P2_MARKETS:
            (lo, hi), src = P2_MARKETS[m]
            print(f"  {m:<10} = Uniform[{lo:.2f}, {hi:.2f}]  ({src})")
    print(f"\nP3 ({n_p3} markets, Beta posterior heuristic):")
    for m in market_names:
        if m in P3_MARKETS:
            a, b = P3_MARKETS[m]
            mean = a / (a + b)
            print(f"  {m:<10} = Beta({a:.1f}, {b:.1f}) mean={mean:.3f}")

    # All-P1 reference
    rps_p1ref = np.array([ALL_P1_REF[m] for m in market_names])
    rho_raw_p1, p_raw_p1 = spearmanr(H_raw, rps_p1ref)
    rho_filt_p1, p_filt_p1 = spearmanr(H_filt, rps_p1ref)

    print(f"\n--- All-P1 deterministic reference (point estimates) ---")
    print(f"  rho(H_raw, RPS)  = {rho_raw_p1:+.4f}, p = {p_raw_p1:.4f}")
    print(f"  rho(H_filt, RPS) = {rho_filt_p1:+.4f}, p = {p_filt_p1:.4f}")

    # Cascade Monte Carlo
    rng = np.random.default_rng(SEED)
    rho_raw_trials = np.zeros(N_MC)
    rho_filt_trials = np.zeros(N_MC)

    for t in range(N_MC):
        rps_trial = np.zeros(len(market_names))
        for i, m in enumerate(market_names):
            if m in P1_MARKETS:
                rps_trial[i] = P1_MARKETS[m][0]
            elif m in P2_MARKETS:
                (lo, hi), _ = P2_MARKETS[m]
                rps_trial[i] = rng.uniform(lo, hi)
            elif m in P3_MARKETS:
                a, b = P3_MARKETS[m]
                rps_trial[i] = rng.beta(a, b)
        rho_raw_trials[t], _ = spearmanr(H_raw, rps_trial)
        rho_filt_trials[t], _ = spearmanr(H_filt, rps_trial)

    print(f"\n--- Cascade Monte Carlo ({N_MC} trials, seed = {SEED}) ---")
    for label, arr in [("Raw labels", rho_raw_trials), ("Filtered labels", rho_filt_trials)]:
        print(f"\n{label}:")
        print(f"  Mean rho     = {arr.mean():+.4f}")
        print(f"  Median       = {np.median(arr):+.4f}")
        print(f"  95% CI       = [{np.percentile(arr, 2.5):+.4f}, {np.percentile(arr, 97.5):+.4f}]")
        print(f"  P(rho > 0.5) = {(arr > 0.5).mean()*100:.1f}%")
        print(f"  P(rho > 0.7) = {(arr > 0.7).mean()*100:.1f}%")

    # Tier comparison
    with open(os.path.join(RESULTS_DIR, "h1_dml_cpcv_n27.json"), 'r', encoding='utf-8') as f:
        h1 = json.load(f)
    tier = np.array([h1['results'][m]['tier_rank'] for m in market_names])
    rho_tier_raw, p_tier_raw = spearmanr(H_raw, tier)
    rho_tier_filt, p_tier_filt = spearmanr(H_filt, tier)
    rho_eta_raw, p_eta_raw = spearmanr([h2['per_market'][m]['raw']['eta_sq'] for m in market_names], tier)
    rho_eta_filt, p_eta_filt = spearmanr([h2['per_market'][m]['filtered']['eta_sq'] for m in market_names], rps_p1ref)

    print(f"\n--- Cross-market summary at n=27 (refined cascade + tier comparison) ---")
    print(f"\n{'Predictor':<25} {'rho(H_raw)':>12} {'p':>8} {'rho(H_filt)':>13} {'p':>8}")
    print("-" * 70)
    print(f"{'Tier (composite)':<25} {rho_tier_raw:>+12.4f} {p_tier_raw:>8.4f} {rho_tier_filt:>+13.4f} {p_tier_filt:>8.4f}")
    print(f"{'RPS (all-P1 ref)':<25} {rho_raw_p1:>+12.4f} {p_raw_p1:>8.4f} {rho_filt_p1:>+13.4f} {p_filt_p1:>8.4f}")
    print(f"{'RPS (cascade Mean)':<25} {rho_raw_trials.mean():>+12.4f} {'(MC)':>8} {rho_filt_trials.mean():>+13.4f} {'(MC)':>8}")

    # Per-tier analysis with refined RPS
    print(f"\n--- Per-tier statistics with refined cascade ---")
    print(f"{'Tier':<18} {'n':<3} {'mean RPS':>10} {'mean H_raw':>12} {'mean H_filt':>13}")
    print("-" * 65)
    for t in [4, 3, 2, 1]:
        cat = {4: 'Frontier', 3: 'Asian Emerging', 2: 'Crypto', 1: 'Developed'}[t]
        idx = np.where(tier == t)[0]
        if len(idx) > 0:
            print(f"{cat:<18} {len(idx):<3} {rps_p1ref[idx].mean():>10.3f} {H_raw[idx].mean():>12.2f} {H_filt[idx].mean():>13.2f}")

    # Within-tier Spearman
    print(f"\n--- Within-tier rho(H, RPS) — REFINED RPS ---")
    for t in [4, 3, 1]:
        cat = {4: 'Frontier', 3: 'Asian Emerging', 1: 'Developed'}[t]
        idx = np.where(tier == t)[0]
        if len(idx) >= 4:
            r1, p1 = spearmanr(H_raw[idx], rps_p1ref[idx])
            r2, p2 = spearmanr(H_filt[idx], rps_p1ref[idx])
            print(f"  {cat:<18} (n={len(idx)}): rho_raw = {r1:+.4f} (p={p1:.4f}), rho_filt = {r2:+.4f} (p={p2:.4f})")

    # FULL per-market table (sorted by refined RPS)
    print(f"\n--- FULL n=27 per-market table (sorted by refined RPS) ---")
    print(f"{'RPS':>6} {'Market':<10} {'tier':<5} {'phase':<5} {'H_raw':>8} {'H_filt':>8}")
    table = []
    for i, m in enumerate(market_names):
        if m in P1_MARKETS: phase = "P1"
        elif m in P2_MARKETS: phase = "P2"
        else: phase = "P3"
        table.append((rps_p1ref[i], m, tier[i], phase, H_raw[i], H_filt[i]))
    for row in sorted(table, key=lambda x: x[0]):
        print(f"{row[0]:>6.3f} {row[1]:<10} {row[2]:<5} {row[3]:<5} {row[4]:>8.2f} {row[5]:>8.2f}")

    # Save
    output = {
        "spec": "H2 cascade FULL n=27 with refined P1/P2/P3 classification",
        "panel_n": len(market_names),
        "phase_distribution": f"{n_p1} P1 + {n_p2} P2 + {n_p3} P3",
        "P1_count": n_p1, "P2_count": n_p2, "P3_count": n_p3,
        "n_mc": N_MC,
        "seed": SEED,
        "all_p1_reference": {
            "rho_H_raw":  float(rho_raw_p1),
            "p_H_raw":    float(p_raw_p1),
            "rho_H_filt": float(rho_filt_p1),
            "p_H_filt":   float(p_filt_p1),
            "rps_values": {m: float(ALL_P1_REF[m]) for m in market_names},
        },
        "cascade_composite": {
            "raw": {
                "mean":   float(rho_raw_trials.mean()),
                "median": float(np.median(rho_raw_trials)),
                "p025":   float(np.percentile(rho_raw_trials, 2.5)),
                "p975":   float(np.percentile(rho_raw_trials, 97.5)),
                "P_rho_gt_0p5": float((rho_raw_trials > 0.5).mean()),
                "P_rho_gt_0p7": float((rho_raw_trials > 0.7).mean()),
            },
            "filtered": {
                "mean":   float(rho_filt_trials.mean()),
                "median": float(np.median(rho_filt_trials)),
                "p025":   float(np.percentile(rho_filt_trials, 2.5)),
                "p975":   float(np.percentile(rho_filt_trials, 97.5)),
                "P_rho_gt_0p5": float((rho_filt_trials > 0.5).mean()),
                "P_rho_gt_0p7": float((rho_filt_trials > 0.7).mean()),
            },
        },
        "tier_comparison": {
            "rho_H_raw":  float(rho_tier_raw),
            "p_H_raw":    float(p_tier_raw),
            "rho_H_filt": float(rho_tier_filt),
            "p_H_filt":   float(p_tier_filt),
        },
    }
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nWrote: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
