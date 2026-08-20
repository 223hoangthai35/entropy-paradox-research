"""
Aleatoric/epistemic SD sensitivity (Plan v9 §A.5, Major M-5).

Rerun the variance decomposition (h2_bayesian_uq.py) at multiple H Normal-noise
SD fractions ∈ {0.05, 0.10, 0.20, 0.30} to show robustness of the
~97-99% epistemic / 1-3% aleatoric claim.

Output: validation/results_v2/h2_decomposition_sensitivity.json
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

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from validation.h2_magnitude.h2_bayesian_uq import (
    load_h_stats, joint_uq_nested, OUTPUT_DIR
)

SD_FRACTIONS = [0.05, 0.10, 0.20, 0.30]
N_OUTER = 1000
N_INNER = 50
SEED = 42


def main() -> int:
    print("=" * 70)
    print("  ALEATORIC/EPISTEMIC SD SENSITIVITY")
    print("=" * 70)
    print(f"  SD fractions tested: {SD_FRACTIONS}")
    print(f"  N outer = {N_OUTER}, N inner = {N_INNER}")

    df_h = load_h_stats()
    H_raw = {row["market"]: float(row["H_stat"]) for _, row in df_h.iterrows()}
    H_filt = ({row["market"]: float(row["H_stat_filtered"]) for _, row in df_h.iterrows()}
              if "H_stat_filtered" in df_h.columns else None)

    results = {"raw": {}, "filtered": {}}
    t_start = time.time()

    for sd_frac in SD_FRACTIONS:
        print(f"\n--- SD fraction = {sd_frac} ---")
        print("  RAW labels...")
        raw_res = joint_uq_nested(H_raw, n_outer=N_OUTER, n_inner=N_INNER, h_noise_sd_frac=sd_frac, seed=SEED)
        decomp = raw_res["variance_decomposition"]
        results["raw"][f"sd_{sd_frac}"] = {
            "h_noise_sd_frac": sd_frac,
            "aleatoric_share_pct": decomp["aleatoric_share_pct"],
            "epistemic_share_pct": decomp["epistemic_share_pct"],
            "total_variance": decomp["total_variance"],
            "joint_rho_mean": raw_res["joint_rho_distribution"]["mean"],
            "joint_rho_p025": raw_res["joint_rho_distribution"]["p025"],
            "joint_rho_p975": raw_res["joint_rho_distribution"]["p975"],
        }
        print(f"    aleatoric = {decomp['aleatoric_share_pct']:.2f}%, epistemic = {decomp['epistemic_share_pct']:.2f}%")

        if H_filt is not None:
            print("  FILTERED labels...")
            filt_res = joint_uq_nested(H_filt, n_outer=N_OUTER, n_inner=N_INNER, h_noise_sd_frac=sd_frac, seed=SEED)
            decomp_f = filt_res["variance_decomposition"]
            results["filtered"][f"sd_{sd_frac}"] = {
                "h_noise_sd_frac": sd_frac,
                "aleatoric_share_pct": decomp_f["aleatoric_share_pct"],
                "epistemic_share_pct": decomp_f["epistemic_share_pct"],
                "total_variance": decomp_f["total_variance"],
                "joint_rho_mean": filt_res["joint_rho_distribution"]["mean"],
                "joint_rho_p025": filt_res["joint_rho_distribution"]["p025"],
                "joint_rho_p975": filt_res["joint_rho_distribution"]["p975"],
            }
            print(f"    aleatoric = {decomp_f['aleatoric_share_pct']:.2f}%, epistemic = {decomp_f['epistemic_share_pct']:.2f}%")

    print("\n" + "=" * 70)
    print("  SUMMARY TABLE")
    print("=" * 70)
    print(f"  {'SD':<6}  {'RAW alea%':<12}  {'RAW epi%':<12}  {'FILT alea%':<12}  {'FILT epi%':<12}")
    for sd_frac in SD_FRACTIONS:
        raw = results["raw"][f"sd_{sd_frac}"]
        filt = results["filtered"].get(f"sd_{sd_frac}", {})
        print(f"  {sd_frac:<6}  {raw['aleatoric_share_pct']:<12.2f}  {raw['epistemic_share_pct']:<12.2f}"
              f"  {filt.get('aleatoric_share_pct', 0):<12.2f}  {filt.get('epistemic_share_pct', 0):<12.2f}")

    payload = {
        "spec": "Aleatoric/epistemic decomposition sensitivity to H Normal-noise SD fraction",
        "sd_fractions_tested": SD_FRACTIONS,
        "n_outer": N_OUTER,
        "n_inner": N_INNER,
        "seed": SEED,
        "elapsed_seconds": float(time.time() - t_start),
        "results": results,
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_magnitude/h2_decomposition_sensitivity.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
