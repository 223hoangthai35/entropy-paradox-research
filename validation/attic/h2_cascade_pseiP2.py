"""
H2 cascade with PSEI reclassified P1 → P2 (Plan v9 §A.8, Major M-6).

Original cascade (h2_cascade.py): PSEI = P1 point 0.68 (PSE Annual Report).
M-6 reclassification: PSEI = P2 Uniform[0.21, 0.68] reflecting metric
disagreement between PSE Annual Report (0.68) and PSE Stock Market Investor
Profile (0.21).

This script reuses h2_cascade machinery but with PSEI swapped to P2; reports
new cascade composite ρ distribution and compares to baseline.

Output: validation/results_v2/h2_cascade_pseiP2.json
"""
from __future__ import annotations

import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation.h2_cascade import (
    CASCADE as CASCADE_BASELINE,
    cascade_mc, load_h_stats, OUTPUT_DIR, N_MC, SEED,
)
import validation.h2_cascade as cascade_module

# Reclassify PSEI: P1 point 0.68 → P2 Uniform[0.21, 0.68]
CASCADE_PSEI_P2 = {**CASCADE_BASELINE}
CASCADE_PSEI_P2["PSEI"] = {
    "tier": "P2", "type": "uniform", "low": 0.21, "high": 0.68,
    "source": "P1 metric disagreement: PSE 2023 Annual Report (0.68) vs PSE Stock Market Investor Profile (0.21); P2 bounds applied",
}


def main() -> int:
    print("=" * 70)
    print("  H2 CASCADE WITH PSEI RECLASSIFIED P1 → P2")
    print("=" * 70)

    df_h = load_h_stats()
    H_raw = {row["market"]: float(row["H_stat"]) for _, row in df_h.iterrows()}
    H_filt = ({row["market"]: float(row["H_stat_filtered"]) for _, row in df_h.iterrows()}
              if "H_stat_filtered" in df_h.columns else None)

    # Print modified cascade spec
    print("\n  Modified cascade specification:")
    for m, spec in CASCADE_PSEI_P2.items():
        print(f"    {m:<10}: {spec['tier']:<3} {spec['type']:<8} {spec.get('value', spec.get('low', spec.get('mean', '?')))}")

    # Inject modified cascade into module namespace
    cascade_module.CASCADE = CASCADE_PSEI_P2

    print("\n  Running cascade MC with PSEI=P2...")
    t_start = time.time()
    raw_cascade = cascade_mc(H_raw, n_mc=N_MC, seed=SEED)
    filt_cascade = cascade_mc(H_filt, n_mc=N_MC, seed=SEED) if H_filt else None
    elapsed = time.time() - t_start

    print(f"\n  RAW labels (PSEI=P2):")
    print(f"    rho mean = {raw_cascade['mean']:+.4f}   median = {raw_cascade['median']:+.4f}   sd = {raw_cascade['sd']:.3f}")
    print(f"    95% CI   = [{raw_cascade['p025']:+.4f}, {raw_cascade['p975']:+.4f}]")
    print(f"    P(rho > 0.5) = {raw_cascade['P_rho_gt_0p5']*100:.1f}%   P(rho > 0.7) = {raw_cascade['P_rho_gt_0p7']*100:.1f}%")

    if filt_cascade:
        print(f"\n  FILTERED labels (PSEI=P2):")
        print(f"    rho mean = {filt_cascade['mean']:+.4f}   median = {filt_cascade['median']:+.4f}   sd = {filt_cascade['sd']:.3f}")
        print(f"    95% CI   = [{filt_cascade['p025']:+.4f}, {filt_cascade['p975']:+.4f}]")
        print(f"    P(rho > 0.5) = {filt_cascade['P_rho_gt_0p5']*100:.1f}%   P(rho > 0.7) = {filt_cascade['P_rho_gt_0p7']*100:.1f}%")

    # Compare to baseline cascade (PSEI=P1) — reload baseline JSON
    baseline_path = os.path.join(OUTPUT_DIR, "h2_magnitude/h2_cascade.json")
    print("\n  COMPARISON TO BASELINE (PSEI=P1):")
    if os.path.exists(baseline_path):
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline = json.load(f)
        b_raw = baseline["raw_cascade"]
        b_filt = baseline.get("filtered_cascade", {})
        print(f"    RAW : baseline ρ_mean = {b_raw['mean']:+.4f}, modified = {raw_cascade['mean']:+.4f}, Δ = {raw_cascade['mean']-b_raw['mean']:+.4f}")
        if b_filt and filt_cascade:
            print(f"    FILT: baseline ρ_mean = {b_filt['mean']:+.4f}, modified = {filt_cascade['mean']:+.4f}, Δ = {filt_cascade['mean']-b_filt['mean']:+.4f}")
    else:
        print(f"  baseline JSON not found at {baseline_path}")

    payload = {
        "spec": "H2 cascade with PSEI reclassified P1 → P2 (Uniform[0.21, 0.68])",
        "cascade_modified": CASCADE_PSEI_P2,
        "n_mc_trials": N_MC,
        "seed": SEED,
        "elapsed_seconds": float(elapsed),
        "raw_cascade": raw_cascade,
        "filtered_cascade": filt_cascade,
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_magnitude/h2_cascade_pseiP2.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
