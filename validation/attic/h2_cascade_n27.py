"""
H2 cascade composite Monte Carlo on the n=27 expansion panel.

Reads per-market H stats from h2_eta_squared_n27.json (must run that script
first), then samples per-market RPS by cascade phase and computes Spearman
ρ(H, RPS) across 10,000 trials.

For comparison with paper canonical n=8 results:
  Paper raw  cascade: mean ρ = 0.847, 95% CI [0.786, 0.905], P(ρ>0.5)=100%
  Paper filt cascade: mean ρ = 0.901, 95% CI [0.833, 0.952], P(ρ>0.5)=100%
  Paper all-P1 reference (raw): ρ = 0.850 (p=0.008)
  Paper all-P1 reference (filt): ρ = 0.934 (p=0.0007)

Output: validation/results_v2/n27_experiment/h2_cascade_n27.json

Usage:
    python validation/h2_cascade_n27.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import numpy as np
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation.markets_n27 import MARKETS_N27, CASCADE_N27, panel_summary

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2", "n27_experiment")
os.makedirs(OUTPUT_DIR, exist_ok=True)
INPUT_JSON = os.path.join(OUTPUT_DIR, "h2_eta_squared_n27.json")

N_MC = 10_000
SEED = 42


def sample_rps(name: str, rng: np.random.Generator) -> float:
    spec = CASCADE_N27[name]
    t = spec["type"]
    if t == "point":
        return float(spec["value"])
    if t == "uniform":
        return float(rng.uniform(spec["low"], spec["high"]))
    if t == "beta":
        alpha = spec["kappa"] * spec["mean"]
        beta = spec["kappa"] * (1 - spec["mean"])
        return float(rng.beta(alpha, beta))
    raise ValueError(f"unknown cascade type: {t}")


def cascade_mc(H_per_market: dict[str, float], n_mc: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    markets = sorted(H_per_market.keys())
    H = np.array([H_per_market[m] for m in markets])
    rhos = np.empty(n_mc)
    for b in range(n_mc):
        rps = np.array([sample_rps(m, rng) for m in markets])
        r = spearmanr(H, rps)
        rhos[b] = r.statistic
    finite = rhos[np.isfinite(rhos)]
    return {
        "n_trials": int(len(finite)),
        "n_markets": len(markets),
        "mean": float(np.mean(finite)),
        "median": float(np.median(finite)),
        "sd": float(np.std(finite)),
        "p025": float(np.percentile(finite, 2.5)),
        "p975": float(np.percentile(finite, 97.5)),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "P_rho_gt_0p5": float((finite > 0.5).mean()),
        "P_rho_gt_0p7": float((finite > 0.7).mean()),
    }


def all_p1_reference(H_per_market: dict[str, float]) -> dict:
    """Reference Spearman using each market's RPS point estimate (P1=value,
    P2=midpoint, P3=Beta mean)."""
    markets = sorted(H_per_market.keys())
    H = np.array([H_per_market[m] for m in markets])
    rps = []
    for m in markets:
        spec = CASCADE_N27[m]
        if spec["type"] == "point":
            rps.append(spec["value"])
        elif spec["type"] == "uniform":
            rps.append(0.5 * (spec["low"] + spec["high"]))
        elif spec["type"] == "beta":
            rps.append(spec["mean"])
    rps = np.array(rps)
    r = spearmanr(H, rps)
    return {"rho": float(r.statistic), "p": float(r.pvalue), "n": len(markets)}


def main() -> int:
    if not os.path.exists(INPUT_JSON):
        print(f"ERROR: {INPUT_JSON} not found.")
        print("Run h2_eta_squared_n27.py first to compute per-market H stats.")
        return 1

    print("=" * 70)
    print("  H2 CASCADE COMPOSITE MC — n=27 EXPANSION PANEL")
    print("=" * 70)
    print(panel_summary())
    print()

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        eta_data = json.load(f)

    # Build H_per_market for raw and filtered (skip markets that failed)
    H_raw = {}
    H_filt = {}
    for name, r in eta_data["per_market"].items():
        if "skip_reason" in r:
            continue
        if np.isfinite(r["raw"]["H_stat"]):
            H_raw[name] = r["raw"]["H_stat"]
        if np.isfinite(r["filtered"]["H_stat"]):
            H_filt[name] = r["filtered"]["H_stat"]

    print(f"  H_raw  available for {len(H_raw)} markets")
    print(f"  H_filt available for {len(H_filt)} markets")
    print(f"  Cascade composite MC: n={N_MC} trials, seed={SEED}")
    print()

    raw_cascade = cascade_mc(H_raw, n_mc=N_MC, seed=SEED) if H_raw else None
    filt_cascade = cascade_mc(H_filt, n_mc=N_MC, seed=SEED) if H_filt else None
    raw_p1ref = all_p1_reference(H_raw) if H_raw else None
    filt_p1ref = all_p1_reference(H_filt) if H_filt else None

    print("=" * 70)
    print("  RESULTS")
    print("=" * 70)
    if raw_cascade:
        print(f"  RAW labels (n={raw_cascade['n_markets']}):")
        print(f"    Cascade composite: mean ρ = {raw_cascade['mean']:+.4f}, "
              f"95% CI [{raw_cascade['p025']:+.4f}, {raw_cascade['p975']:+.4f}], "
              f"sd = {raw_cascade['sd']:.4f}")
        print(f"    P(ρ > 0.5) = {raw_cascade['P_rho_gt_0p5']*100:.1f}%, "
              f"P(ρ > 0.7) = {raw_cascade['P_rho_gt_0p7']*100:.1f}%")
        print(f"    All-P1 reference: ρ = {raw_p1ref['rho']:+.4f} (p = {raw_p1ref['p']:.4f})")
    if filt_cascade:
        print(f"  FILTERED labels (n={filt_cascade['n_markets']}):")
        print(f"    Cascade composite: mean ρ = {filt_cascade['mean']:+.4f}, "
              f"95% CI [{filt_cascade['p025']:+.4f}, {filt_cascade['p975']:+.4f}], "
              f"sd = {filt_cascade['sd']:.4f}")
        print(f"    P(ρ > 0.5) = {filt_cascade['P_rho_gt_0p5']*100:.1f}%, "
              f"P(ρ > 0.7) = {filt_cascade['P_rho_gt_0p7']*100:.1f}%")
        print(f"    All-P1 reference: ρ = {filt_p1ref['rho']:+.4f} (p = {filt_p1ref['p']:.4f})")

    print()
    print("  Paper canonical n=8 reference:")
    print("    raw  cascade : mean ρ = 0.847, 95% CI [0.786, 0.905], P(ρ>0.5)=100%")
    print("    filt cascade : mean ρ = 0.901, 95% CI [0.833, 0.952], P(ρ>0.5)=100%")
    print("    raw  all-P1  : ρ = 0.850 (p=0.008)")
    print("    filt all-P1  : ρ = 0.934 (p=0.0007)")

    payload = {
        "spec": "H2 cascade composite MC on n=27 expansion panel",
        "panel": "n27_experiment",
        "n_mc": N_MC,
        "seed": SEED,
        "raw_cascade": raw_cascade,
        "filtered_cascade": filt_cascade,
        "raw_all_p1_reference": raw_p1ref,
        "filtered_all_p1_reference": filt_p1ref,
        "paper_n8_reference": {
            "raw_cascade":  {"mean": 0.847, "ci_95": [0.786, 0.905], "P_rho_gt_0p5": 1.0},
            "filt_cascade": {"mean": 0.901, "ci_95": [0.833, 0.952], "P_rho_gt_0p5": 1.0},
            "raw_all_p1":   {"rho": 0.850, "p": 0.008},
            "filt_all_p1":  {"rho": 0.934, "p": 0.0007},
        },
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_cascade_n27.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\n  JSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
