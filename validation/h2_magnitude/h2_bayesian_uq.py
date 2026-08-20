"""
H2 ENHANCEMENT — Bayesian posterior over RPS + Monte Carlo propagation
                 + aleatoric/epistemic uncertainty decomposition.

Layer 1 (Core): Bayesian Posterior over RPS with Monte Carlo Propagation
  - Per-market Beta posterior parameterized by source-credibility
  - BVB: Beta posterior centred on competing-source bounds (Uniform[0.20, 0.25])
  - Sample RPS from posteriors → propagate through Spearman rho

Layer 2 (Conditional bootstrap on H — partial): use existing per-market H
  point estimates with proxy noise (block-bootstrap of input data is
  prohibitive without full pipeline re-run; for E1+ enhancement we adopt
  Normal noise on H with relative SD = 0.10 as conservative proxy.

Layer 3 (Reframe): variance decomposition
  Var(rho) = E[Var(rho | RPS)] (aleatoric, from finite-n Spearman noise)
           + Var(E[rho | RPS])  (epistemic, from RPS posterior uncertainty)

Output: results_v2/h2_bayesian_uq.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2")
PRIMARY_CSV = os.path.join(OUTPUT_DIR, "cross_market_summary_v2.csv")

# Per-market RPS posterior specifications.
# Beta(α, β) parameterized by mean and concentration κ = α + β.
# Higher κ = tighter posterior (more authoritative source).
# BVB uses a uniform-bound Beta to reflect competing-source bounds
# (BVB Investor Relations + ASF Romania monthly market reports, trading-value-weighted).
RPS_POSTERIOR: dict[str, dict] = {
    # Multi-source convergence on 0.80-0.92; high concentration
    "VNINDEX": {"type": "beta", "mean": 0.86, "kappa": 200,
                "rationale": "Vietnam SSC + VinaCapital multi-year convergent (2020-2024)"},
    # BVB: P2 cascade — Uniform[0.20, 0.25] from competing-source bounds (BVB IR + ASF Romania)
    "BVB":  {"type": "beta", "mean": 0.225, "kappa": 200,
             "rationale": "BVB Investor Relations + ASF Romania monthly market reports (trading-value-weighted retail share)"},
    # KRX Data Marketplace direct = authoritative
    "KOSPI": {"type": "beta", "mean": 0.45, "kappa": 100,
              "rationale": "KRX Data Marketplace 2026 direct + multi-period readings (0.30-0.45)"},
    # NSE FY data clean
    "NIFTY": {"type": "beta", "mean": 0.39, "kappa": 200,
              "rationale": "NSE India FY21-FY25 clean time-series, narrow confidence"},
    # SIFMA ownership (0.18) vs MEMX flow (0.30-0.37) metric disagreement
    "SPX": {"type": "beta", "mean": 0.27, "kappa": 30,
            "rationale": "SIFMA + MEMX metric disagreement (0.18-0.37); wider posterior"},
    # UK FCA / LSE limited public data
    "FTSE": {"type": "beta", "mean": 0.18, "kappa": 50,
             "rationale": "Limited UK public data, conservative bounds"},
    # JPX investor-type weekly stats
    "NIKKEI": {"type": "beta", "mean": 0.20, "kappa": 100,
               "rationale": "JPX Trading-by-Investor-Type 2024 reading"},
    # Crypto no authoritative aggregator; widest posterior
    "BTC": {"type": "beta", "mean": 0.65, "kappa": 20,
            "rationale": "Crypto-aggregator estimates, ETF-era market structure shift; widest posterior"},
}

N_MC = 10_000
N_INNER_BOOTSTRAP = 50  # for H bootstrap nested loop
H_NOISE_SD_FRAC = 0.10  # H bootstrap proxy: Normal noise with sd = 10% of H point
SEED = 42


def load_h_stats() -> pd.DataFrame:
    df = pd.read_csv(PRIMARY_CSV)
    cols = ["market", "H_stat"]
    if "H_stat_filtered" in df.columns:
        cols.append("H_stat_filtered")
    return df[cols].copy()


def sample_rps_posterior(market: str, rng: np.random.Generator) -> float:
    """Sample one RPS value from the market's Bayesian posterior."""
    spec = RPS_POSTERIOR[market]
    if spec["type"] == "beta":
        alpha = spec["kappa"] * spec["mean"]
        beta = spec["kappa"] * (1.0 - spec["mean"])
        return float(rng.beta(alpha, beta))
    elif spec["type"] == "mixture":
        weights = np.array([c["weight"] for c in spec["components"]])
        idx = rng.choice(len(weights), p=weights)
        c = spec["components"][idx]
        alpha = c["kappa"] * c["mean"]
        beta = c["kappa"] * (1.0 - c["mean"])
        return float(rng.beta(alpha, beta))
    raise ValueError(f"Unknown posterior type: {spec['type']}")


def posterior_summary(market: str, n_samples: int = 100_000, seed: int = 42) -> dict:
    """Numerical summary of per-market posterior."""
    rng = np.random.default_rng(seed)
    samples = np.array([sample_rps_posterior(market, rng) for _ in range(n_samples)])
    return {
        "market": market,
        "mean": float(np.mean(samples)),
        "median": float(np.median(samples)),
        "sd": float(np.std(samples)),
        "p025": float(np.percentile(samples, 2.5)),
        "p975": float(np.percentile(samples, 97.5)),
        "rationale": RPS_POSTERIOR[market]["rationale"],
    }


def joint_uq_simple(H_dict: dict[str, float], n_mc: int = N_MC, seed: int = SEED) -> dict:
    """Layer 1 only: sample RPS from posteriors, fix H point estimates, compute rho."""
    rng = np.random.default_rng(seed)
    markets = list(H_dict.keys())
    H_arr = np.array([H_dict[m] for m in markets])
    rhos = np.empty(n_mc)
    for i in range(n_mc):
        rps_sample = np.array([sample_rps_posterior(m, rng) for m in markets])
        rho, _ = stats.spearmanr(H_arr, rps_sample)
        rhos[i] = rho
    return _summarize_rho_distribution(rhos, label="Layer 1 (RPS posterior only, H fixed)")


def joint_uq_nested(H_dict: dict[str, float], n_outer: int = 1000, n_inner: int = N_INNER_BOOTSTRAP,
                    h_noise_sd_frac: float = H_NOISE_SD_FRAC, seed: int = SEED) -> dict:
    """Layer 1+2: nested MC. Outer = RPS posterior samples; inner = H bootstrap proxy.

    Returns inner-conditional and outer-marginal rho statistics for variance decomposition.
    """
    rng = np.random.default_rng(seed)
    markets = list(H_dict.keys())
    H_arr = np.array([H_dict[m] for m in markets])
    inner_means = np.empty(n_outer)  # E[rho | RPS_outer]
    inner_vars = np.empty(n_outer)   # Var[rho | RPS_outer]
    all_rhos = []

    for o in range(n_outer):
        rps_sample = np.array([sample_rps_posterior(m, rng) for m in markets])
        # Inner bootstrap: H ~ Normal(H_point, H_noise_sd_frac * |H_point|)
        inner_rhos = np.empty(n_inner)
        for k in range(n_inner):
            h_perturbed = H_arr + rng.normal(0, h_noise_sd_frac * np.abs(H_arr))
            rho, _ = stats.spearmanr(h_perturbed, rps_sample)
            inner_rhos[k] = rho
        inner_means[o] = float(np.mean(inner_rhos))
        inner_vars[o] = float(np.var(inner_rhos))
        all_rhos.extend(inner_rhos)

    all_rhos = np.array(all_rhos)
    # Variance decomposition (law of total variance):
    # Var(rho) = E[Var(rho | RPS_outer)]    + Var(E[rho | RPS_outer])
    #         = mean of inner_vars         + variance of inner_means
    aleatoric = float(np.mean(inner_vars))    # expected inner variance: H sampling noise
    epistemic = float(np.var(inner_means))    # variance of E[rho|RPS]: RPS posterior uncertainty
    total = aleatoric + epistemic

    return {
        "label": "Layer 1+2 (RPS posterior x H bootstrap proxy)",
        "n_outer": n_outer,
        "n_inner": n_inner,
        "h_noise_sd_frac": h_noise_sd_frac,
        "joint_rho_distribution": _summarize_rho_distribution(all_rhos, label="joint"),
        "outer_marginal_inner_means": _summarize_rho_distribution(inner_means, label="outer_marginal"),
        "variance_decomposition": {
            "aleatoric_E_Var_rho_given_RPS": aleatoric,
            "epistemic_Var_E_rho_given_RPS": epistemic,
            "total_variance": total,
            "aleatoric_share_pct": float(100 * aleatoric / total) if total > 0 else float("nan"),
            "epistemic_share_pct": float(100 * epistemic / total) if total > 0 else float("nan"),
        },
    }


def _summarize_rho_distribution(rhos, label: str = "") -> dict:
    rhos = np.asarray(rhos)
    return {
        "label": label,
        "n": int(rhos.size),
        "mean": float(np.mean(rhos)),
        "median": float(np.median(rhos)),
        "sd": float(np.std(rhos, ddof=1)),
        "p025": float(np.percentile(rhos, 2.5)),
        "p05": float(np.percentile(rhos, 5)),
        "p25": float(np.percentile(rhos, 25)),
        "p75": float(np.percentile(rhos, 75)),
        "p95": float(np.percentile(rhos, 95)),
        "p975": float(np.percentile(rhos, 97.5)),
        "P_rho_gt_0p5": float(np.mean(rhos > 0.5)),
        "P_rho_gt_0p7": float(np.mean(rhos > 0.7)),
    }


def main() -> int:
    df_h = load_h_stats()
    H_raw = {row["market"]: float(row["H_stat"]) for _, row in df_h.iterrows()}
    H_filt = ({row["market"]: float(row["H_stat_filtered"]) for _, row in df_h.iterrows()}
              if "H_stat_filtered" in df_h.columns else None)

    print("=" * 80)
    print("  H2 BAYESIAN UQ (2.5-layer)")
    print("=" * 80)

    # Per-market posterior summaries
    print("\n  Per-market RPS posterior summary:")
    print(f"  {'market':<10}  {'mean':>6}  {'median':>7}  {'sd':>5}  {'95% CI':>20}")
    posterior_summaries = {}
    for m in H_raw.keys():
        s = posterior_summary(m)
        posterior_summaries[m] = s
        print(f"  {m:<10}  {s['mean']:>6.3f}  {s['median']:>7.3f}  {s['sd']:>5.3f}  "
              f"[{s['p025']:.3f}, {s['p975']:.3f}]")

    # Layer 1 only (RPS posterior, H fixed)
    print("\n  --- Layer 1 (RPS Bayesian posterior, H point estimate) ---")
    raw_l1 = joint_uq_simple(H_raw)
    print(f"  RAW:      mean rho = {raw_l1['mean']:+.4f}   95% CI = [{raw_l1['p025']:+.4f}, {raw_l1['p975']:+.4f}]   P(rho>0.5)={raw_l1['P_rho_gt_0p5']*100:.1f}%")
    if H_filt:
        filt_l1 = joint_uq_simple(H_filt)
        print(f"  FILTERED: mean rho = {filt_l1['mean']:+.4f}   95% CI = [{filt_l1['p025']:+.4f}, {filt_l1['p975']:+.4f}]   P(rho>0.5)={filt_l1['P_rho_gt_0p5']*100:.1f}%")

    # Layer 1+2 nested with H bootstrap proxy + variance decomposition
    print("\n  --- Layer 1+2 (Joint UQ: RPS posterior x H bootstrap proxy) ---")
    raw_l12 = joint_uq_nested(H_raw)
    j = raw_l12["joint_rho_distribution"]
    v = raw_l12["variance_decomposition"]
    print(f"  RAW:      mean = {j['mean']:+.4f}   95% CI = [{j['p025']:+.4f}, {j['p975']:+.4f}]")
    print(f"            Aleatoric (H sample noise)    = {v['aleatoric_share_pct']:.1f}% of total variance")
    print(f"            Epistemic (RPS posterior unc) = {v['epistemic_share_pct']:.1f}% of total variance")
    if H_filt:
        filt_l12 = joint_uq_nested(H_filt)
        j = filt_l12["joint_rho_distribution"]
        v = filt_l12["variance_decomposition"]
        print(f"  FILTERED: mean = {j['mean']:+.4f}   95% CI = [{j['p025']:+.4f}, {j['p975']:+.4f}]")
        print(f"            Aleatoric (H sample noise)    = {v['aleatoric_share_pct']:.1f}% of total variance")
        print(f"            Epistemic (RPS posterior unc) = {v['epistemic_share_pct']:.1f}% of total variance")

    payload = {
        "spec": "H2 Bayesian UQ — Layer 1 (RPS posterior MC) + Layer 2 (joint with H bootstrap proxy) + Layer 3 conceptual (aleatoric/epistemic decomposition)",
        "rps_posterior_specifications": RPS_POSTERIOR,
        "rps_posterior_summaries": posterior_summaries,
        "raw_layer1": raw_l1,
        "raw_layer12": raw_l12,
        "filtered_layer1": filt_l1 if H_filt else None,
        "filtered_layer12": filt_l12 if H_filt else None,
        "n_mc_layer1": N_MC,
        "n_outer_layer12": 1000,
        "n_inner_layer12": N_INNER_BOOTSTRAP,
        "h_noise_sd_frac": H_NOISE_SD_FRAC,
        "seed": SEED,
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_bayesian_uq.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
