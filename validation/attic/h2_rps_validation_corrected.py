"""
H2 RE-TEST với KOSPI RPS correction (Scenario C from multi-scenario analysis).

This script replicates the EXACT methodology of h2_rps_validation.py but with
KOSPI's RPS corrected from the pre-registered ASIFMA 2022 reading (0.70) to
the KRX-direct contemporary reading (0.45). All other markets retain their
pre-registered RPS values.

Rationale: KOSPI 0.70 (ASIFMA 2022) is a 2021-period reading that does not
reflect the post-2022 institutional re-entry, Korean Value-up program (2024),
and foreign-investor net buying patterns of 2025-2026. The KRX Data Marketplace
March 2026 reading (45% retail) is the most authoritative contemporary measure
and is the harmonised window-average best-estimate.

Other markets keep pre-registered values because:
- VNINDEX 0.90: VinaCapital 2024 + Vietnam SSC consistent across window
- BVB 0.68: PSE 2023 Annual Report (kept; alternative reading from PSE Stock
  Market Investor Profile differs and may reflect different metric definition)
- NIFTY 0.40: NSE India FY data ~0.39 close enough
- SPX 0.22: SIFMA + MEMX midpoint defensible (both metrics within range)
- FTSE 0.18, NIKKEI 0.18, BTC 0.55: best-available, no clear correction
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
PRIMARY_CSV = os.path.join(OUTPUT_DIR, "h2_magnitude/cross_market_summary_v2.csv")

# CORRECTED RPS (Scenario C — KOSPI only correction)
RPS_VALUE: dict[str, float] = {
    "VNINDEX": 0.90,
    "BVB": 0.225,
    "KOSPI":   0.45,   # ← CORRECTED from 0.70 (KRX March 2026 official reading)
    "NIFTY":   0.40,
    "SPX":     0.22,
    "FTSE":    0.18,
    "NIKKEI":  0.18,
    "BTC":     0.55,
}

# Pre-registered for comparison
RPS_OLD: dict[str, float] = {
    "VNINDEX": 0.90, "BVB": 0.225, "KOSPI": 0.70, "NIFTY": 0.40,
    "SPX": 0.22, "FTSE": 0.18, "NIKKEI": 0.18, "BTC": 0.55,
}

HAS_CB: dict[str, bool] = {
    "VNINDEX": True, "BVB": True, "KOSPI": True, "NIFTY": True,
    "SPX": True, "FTSE": False, "NIKKEI": True, "BTC": False,
}
CLASSIFICATION: dict[str, str] = {
    "VNINDEX": "Frontier", "BVB": "Frontier",
    "KOSPI": "Emerging", "NIFTY": "Emerging",
    "SPX": "Developed", "FTSE": "Developed", "NIKKEI": "Developed",
    "BTC": "Crypto",
}

RHO_THRESHOLD = 0.5
P_THRESHOLD = 0.10
N_BOOTSTRAP = 10_000
N_MC = 10_000
RPS_NOISE_SD = 0.05
RNG_SEED = 42


def load_h_stats() -> pd.DataFrame:
    df = pd.read_csv(PRIMARY_CSV)
    cols = ["market", "H_stat", "p_value"]
    if "H_stat_filtered" in df.columns:
        cols.append("H_stat_filtered")
    if "p_value_filtered" in df.columns:
        cols.append("p_value_filtered")
    return df[cols].copy()


def _safe_spearman(x, y):
    rho, p = spearmanr(x, y)
    return float(rho), float(p)


def _rank(arr):
    return pd.Series(arr).rank(ascending=False, method="min").astype(int).values


def h2_spearman(df: pd.DataFrame) -> dict:
    rho, p = _safe_spearman(df["H_stat"].values, df["RPS"].values)
    return {
        "n": int(len(df)),
        "rho": round(rho, 4),
        "p_value": float(p),
        "verdict": "PASS" if (rho > RHO_THRESHOLD and p < P_THRESHOLD) else "FAIL",
    }


def bootstrap_ci(df, n_boot=N_BOOTSTRAP, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    H = df["H_stat"].values
    R = df["RPS"].values
    n = len(df)
    rhos = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(set(H[idx])) < 2 or len(set(R[idx])) < 2:
            rhos[i] = np.nan
            continue
        rhos[i] = spearmanr(H[idx], R[idx])[0]
    rhos = rhos[~np.isnan(rhos)]
    return {
        "ci95_low": float(np.percentile(rhos, 2.5)),
        "ci95_high": float(np.percentile(rhos, 97.5)),
        "mean": float(np.mean(rhos)),
        "std": float(np.std(rhos)),
    }


def mc_sensitivity(df, n_mc=N_MC, noise_sd=RPS_NOISE_SD, seed=RNG_SEED + 1):
    rng = np.random.default_rng(seed)
    H = df["H_stat"].values
    R = df["RPS"].values
    n = len(df)
    rhos = np.empty(n_mc, dtype=float)
    for i in range(n_mc):
        perturbed = np.clip(R + rng.normal(0.0, noise_sd, size=n), 0.0, 1.0)
        rhos[i] = spearmanr(H, perturbed)[0]
    rhos = rhos[~np.isnan(rhos)]
    return {
        "rho_mean": float(np.mean(rhos)),
        "rho_p05": float(np.percentile(rhos, 5)),
        "rho_p50": float(np.percentile(rhos, 50)),
        "rho_p95": float(np.percentile(rhos, 95)),
        "frac_rho_gt_threshold": float(np.mean(rhos > RHO_THRESHOLD)),
    }


def stratified_subpanels(df):
    panels = [
        ("full_panel", df["market"].tolist()),
        ("circuit_breaker_yes", [m for m in df["market"] if HAS_CB[m]]),
        ("circuit_breaker_no", [m for m in df["market"] if not HAS_CB[m]]),
        ("frontier_emerging", [m for m in df["market"]
                               if CLASSIFICATION[m] in ("Frontier", "Emerging")]),
        ("developed_only", [m for m in df["market"]
                            if CLASSIFICATION[m] == "Developed"]),
    ]
    out = []
    for name, mkts in panels:
        sub = df[df["market"].isin(mkts)].copy()
        if len(sub) >= 2:
            rho, p = _safe_spearman(sub["H_stat"].values, sub["RPS"].values)
        else:
            rho, p = float("nan"), float("nan")
        out.append({
            "subpanel": name, "n": int(len(sub)),
            "rho": round(rho, 4) if not np.isnan(rho) else None,
            "p": float(p) if not np.isnan(p) else None,
            "note": "descriptive only — n<4" if len(sub) < 4 else "",
        })
    return out


def run_h2(rps_dict: dict, label: str, df_h: pd.DataFrame) -> dict:
    df = df_h.merge(
        pd.DataFrame({"market": list(rps_dict.keys()),
                      "RPS": list(rps_dict.values())}),
        on="market", how="inner",
    )
    df["rank_RPS"] = _rank(df["RPS"].values)
    df["rank_H"] = _rank(df["H_stat"].values)

    primary = h2_spearman(df)
    boot = bootstrap_ci(df)
    mc = mc_sensitivity(df)

    print(f"\n{'='*90}")
    print(f"  {label}")
    print(f"{'='*90}")
    print(f"  market    RPS    H_stat   rank_RPS  rank_H   |d|")
    for _, r in df.sort_values("rank_RPS").iterrows():
        d = abs(r["rank_RPS"] - r["rank_H"])
        print(f"  {r['market']:<8} {r['RPS']:.2f}   {r['H_stat']:6.2f}      "
              f"{r['rank_RPS']:>2}      {r['rank_H']:>2}     {d:>2}")
    print(f"\n  Spearman rho(H, RPS) = {primary['rho']:+.4f}   p = {primary['p_value']:.4f}")
    print(f"  Verdict: {primary['verdict']}")
    print(f"  Bootstrap 95% CI: [{boot['ci95_low']:.3f}, {boot['ci95_high']:.3f}]")
    print(f"  MC P(rho > 0.5) under sd=0.05: {mc['frac_rho_gt_threshold']*100:.1f}%")

    # Filtered
    if "H_stat_filtered" in df.columns:
        df_f = df.rename(columns={"H_stat": "H_stat_raw", "H_stat_filtered": "H_stat"})
        df_f["rank_H"] = _rank(df_f["H_stat"].values)
        prim_f = h2_spearman(df_f)
        boot_f = bootstrap_ci(df_f)
        print(f"\n  FILTERED: rho = {prim_f['rho']:+.4f}   p = {prim_f['p_value']:.4f}   "
              f"95% CI: [{boot_f['ci95_low']:.3f}, {boot_f['ci95_high']:.3f}]")

    # Subpanels
    strata = stratified_subpanels(df)
    print(f"\n  Stratified subpanels:")
    print(f"  {'subpanel':<24}  n   rho        p")
    for s in strata:
        rho_s = f"{s['rho']:+.4f}" if s['rho'] is not None else "n/a"
        p_s = f"{s['p']:.4f}" if s['p'] is not None else "n/a"
        print(f"  {s['subpanel']:<24} {s['n']:>2}   {rho_s:>8}  {p_s:>8}  {s['note']}")

    return {"primary": primary, "bootstrap": boot, "mc": mc, "strata": strata,
            "panel": rps_dict}


def main() -> int:
    df_h = load_h_stats()

    print("=" * 90)
    print("H2 TEST COMPARISON — Pre-registered vs KOSPI-corrected (Scenario C)")
    print("=" * 90)
    print("Methodology: identical to h2_rps_validation.py except KOSPI RPS")
    print("changed from 0.70 (ASIFMA 2022 / 2021 reporting period) to 0.45")
    print("(KRX Data Marketplace, March 2026 reading).")

    old_results = run_h2(RPS_OLD, "OLD (pre-registered)", df_h)
    new_results = run_h2(RPS_VALUE, "NEW (KOSPI corrected to 0.45)", df_h)

    print(f"\n{'='*90}")
    print("  HEADLINE COMPARISON")
    print(f"{'='*90}")
    print(f"  OLD: rho = {old_results['primary']['rho']:+.4f}   "
          f"p = {old_results['primary']['p_value']:.4f}   "
          f"verdict = {old_results['primary']['verdict']}")
    print(f"  NEW: rho = {new_results['primary']['rho']:+.4f}   "
          f"p = {new_results['primary']['p_value']:.4f}   "
          f"verdict = {new_results['primary']['verdict']}")
    print(f"\n  delta_rho = {new_results['primary']['rho'] - old_results['primary']['rho']:+.4f}")
    print(f"  delta_p   = {new_results['primary']['p_value'] - old_results['primary']['p_value']:+.4f}")

    out_path = os.path.join(OUTPUT_DIR, "h2_magnitude/h2_rps_validation_corrected_KOSPI.json")
    payload = {
        "spec": "H2 re-test with KOSPI RPS corrected to 0.45 (Scenario C)",
        "correction_basis": "KRX Data Marketplace, March 2026 reading; supersedes ASIFMA 2022 (2021 reporting period)",
        "rps_panel_old": RPS_OLD,
        "rps_panel_new": RPS_VALUE,
        "results_old": old_results,
        "results_new": new_results,
        "delta_rho_raw": new_results['primary']['rho'] - old_results['primary']['rho'],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
