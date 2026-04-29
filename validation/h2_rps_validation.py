"""
H2 PRIMARY TEST — Retail Participation Share (RPS) as single-variable
microstructure proxy.

==============================================================================
STATUS
==============================================================================
This script is the PRIMARY specification for hypothesis H2 in paper v2.1.
It SUPERSEDES the composite MS_index that was pre-registered in commit
b130b0f (weights 0.4 / 0.3 / 0.3 on circuit-breaker / 1-inst-share /
1-log10(mcap)/15).

The composite was deprecated on 2026-04-19 because:
  (1) the three weights were chosen qualitatively with no first-principles
      derivation and no cross-validation, so the magnitude of rho against
      the composite index carried an uncontrolled author-selected degree
      of freedom;
  (2) the three components are measured in incompatible units (binary,
      share, log-USD), so linear combination produces a scalar whose
      magnitude is not interpretable.

The composite's pre-registered output (rho = 0.952, p = 2.6e-4) is
preserved read-only under validation/results_v2/prereg_b130b0f/ and is
NOT recomputed here. This script computes the H2 test on RPS only.

==============================================================================
TEST
==============================================================================
    H2:  Spearman rho(H_stat, RPS) > 0.5  AND  p < 0.10
    (thresholds copied from pre-reg as a conservative reference bar; not
     re-registered for RPS since any re-registration post-b130b0f would
     itself be HARK-ing on the next round)

    Reported at 2026-04-19 on 8-market panel, 2020-01-01 -> 2026-04-17:
        rho = 0.754,  p = 0.0305,  n = 8  ->  PASS

==============================================================================
SOURCES (RPS = retail share of trading VALUE, all ex-ante, pre-test)
==============================================================================
    VNINDEX  0.90   VinaCapital (2024) "Vietnam's Resilient Stock Market"
    PSEI     0.68   Philippine Stock Exchange, 2023 Annual Report
    KOSPI    0.70   ASIFMA (2022) Korea Capital Markets Report + KRX
    NIFTY    0.40   NSE India Ownership Report, Q1 FY25
    SPX      0.22   SIFMA (2024) ~17.9% + MEMX (2025) 30-37%, midpoint
    FTSE     0.18   LSE/MEMX (2025) retail order-flow estimate
    NIKKEI   0.18   JPX (2024) retail turnover share
    BTC      0.55   Aggregated crypto-exchange data, 2024-2025

Every value is derived from trade-receipt or account-ownership data, not
from the return series used to compute H_stat. There is no leakage from
outcome to regressor.

Run:
    python validation/h2_rps_validation.py
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

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
PRIMARY_CSV = os.path.join(OUTPUT_DIR, "cross_market_summary_v2.csv")

# -----------------------------------------------------------------------------
# RPS inputs (single variable, ex-ante, publicly sourced)
# -----------------------------------------------------------------------------
RPS_VALUE: dict[str, float] = {
    "VNINDEX": 0.90,
    "PSEI":    0.68,
    "KOSPI":   0.70,
    "NIFTY":   0.40,
    "SPX":     0.22,
    "FTSE":    0.18,
    "NIKKEI":  0.18,
    "BTC":     0.55,
}

HAS_CB: dict[str, bool] = {
    "VNINDEX": True, "PSEI": True, "KOSPI": True, "NIFTY": True,
    "SPX": True, "FTSE": False, "NIKKEI": True, "BTC": False,
}

CLASSIFICATION: dict[str, str] = {
    "VNINDEX": "Frontier", "PSEI": "Frontier",
    "KOSPI":   "Emerging", "NIFTY": "Emerging",
    "SPX":     "Developed", "FTSE": "Developed", "NIKKEI": "Developed",
    "BTC":     "Crypto",
}

RHO_THRESHOLD: float = 0.5   # reference bar, from pre-reg — not re-registered
P_THRESHOLD:   float = 0.10

N_BOOTSTRAP = 10_000
N_MC        = 10_000
RPS_NOISE_SD = 0.05     # +/-0.05 absolute on each market's RPS (Monte Carlo)
RNG_SEED    = 42


def load_h_stats() -> pd.DataFrame:
    """Load H_stat and p_value from cross_market_summary_v2.csv."""
    if not os.path.exists(PRIMARY_CSV):
        raise FileNotFoundError(
            f"H1 summary not found: {PRIMARY_CSV}\n"
            f"Run `python validation/cross_market_v2.py` first."
        )
    df = pd.read_csv(PRIMARY_CSV)
    needed = {"market", "H_stat", "p_value"}
    missing = needed - set(df.columns)
    if missing:
        raise RuntimeError(f"H1 summary missing columns: {missing}")
    return df[["market", "H_stat", "p_value"]].copy()


def _safe_spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    if len(x) < 2 or len(y) < 2:
        return float("nan"), float("nan")
    if len(set(x)) < 2 or len(set(y)) < 2:
        return float("nan"), float("nan")
    rho, p = spearmanr(x, y)
    return float(rho), float(p)


def _rank(arr: np.ndarray) -> np.ndarray:
    """Competition ranking, highest value = rank 1."""
    return pd.Series(arr).rank(ascending=False, method="min").astype(int).values


def h2_spearman(df: pd.DataFrame) -> dict[str, Any]:
    rho, p = _safe_spearman(df["H_stat"].values, df["RPS"].values)
    verdict = "PASS" if (rho > RHO_THRESHOLD and p < P_THRESHOLD) else "FAIL"
    return {
        "spec": "H2 PRIMARY — MS_microstructure = RPS (single variable)",
        "n": int(len(df)),
        "rho": round(rho, 4),
        "p_value": float(p),
        "threshold_rho_gt": RHO_THRESHOLD,
        "threshold_p_lt":   P_THRESHOLD,
        "verdict": verdict,
    }


def bootstrap_ci(
    df: pd.DataFrame, n_boot: int = N_BOOTSTRAP, seed: int = RNG_SEED,
) -> dict[str, Any]:
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
        "n_resamples_effective": int(len(rhos)),
        "ci95_low":  float(np.percentile(rhos, 2.5)),
        "ci95_high": float(np.percentile(rhos, 97.5)),
        "mean":      float(np.mean(rhos)),
        "std":       float(np.std(rhos)),
    }


def mc_sensitivity(
    df: pd.DataFrame,
    n_mc: int = N_MC,
    noise_sd: float = RPS_NOISE_SD,
    seed: int = RNG_SEED + 1,
) -> dict[str, Any]:
    """
    Each trial perturbs every market's RPS by N(0, noise_sd) (clamped to
    [0, 1]), then recomputes Spearman rho(H_stat, perturbed_RPS).
    """
    rng = np.random.default_rng(seed)
    H = df["H_stat"].values
    R = df["RPS"].values
    n = len(df)
    rhos = np.empty(n_mc, dtype=float)
    for i in range(n_mc):
        perturbed = np.clip(R + rng.normal(0.0, noise_sd, size=n), 0.0, 1.0)
        if len(set(perturbed)) < 2:
            rhos[i] = np.nan
            continue
        rhos[i] = spearmanr(H, perturbed)[0]
    rhos = rhos[~np.isnan(rhos)]
    frac_pass = float(np.mean(rhos > RHO_THRESHOLD))
    return {
        "n_trials_effective": int(len(rhos)),
        "noise_sd":   noise_sd,
        "rho_mean":   float(np.mean(rhos)),
        "rho_std":    float(np.std(rhos)),
        "rho_p05":    float(np.percentile(rhos,  5)),
        "rho_p50":    float(np.percentile(rhos, 50)),
        "rho_p95":    float(np.percentile(rhos, 95)),
        "rho_min":    float(np.min(rhos)),
        "rho_max":    float(np.max(rhos)),
        "frac_rho_gt_threshold": frac_pass,
    }


def stratified_subpanels(df: pd.DataFrame) -> list[dict[str, Any]]:
    panels = [
        ("full_panel",             df["market"].tolist()),
        ("circuit_breaker_yes",    [m for m in df["market"] if HAS_CB[m]]),
        ("circuit_breaker_no",     [m for m in df["market"] if not HAS_CB[m]]),
        ("frontier_emerging",      [m for m in df["market"]
                                    if CLASSIFICATION[m] in ("Frontier", "Emerging")]),
        ("developed_only",         [m for m in df["market"]
                                    if CLASSIFICATION[m] == "Developed"]),
    ]
    out: list[dict[str, Any]] = []
    for name, mkts in panels:
        sub = df[df["market"].isin(mkts)].copy()
        rho, p = _safe_spearman(sub["H_stat"].values, sub["RPS"].values)
        out.append({
            "subpanel": name,
            "n": int(len(sub)),
            "markets": mkts,
            "rho_RPS": round(rho, 4) if not np.isnan(rho) else None,
            "p_RPS":   float(p) if not np.isnan(p) else None,
            "note": ("descriptive only — n<4" if len(sub) < 4 else ""),
        })
    return out


def main() -> int:
    print("=" * 88)
    print("H2 PRIMARY TEST — Retail Participation Share (RPS) microstructure proxy")
    print("Supersedes composite MS_index pre-registered b130b0f (see docstring).")
    print("=" * 88)

    df_h = load_h_stats()
    df = df_h.merge(
        pd.DataFrame({
            "market": list(RPS_VALUE.keys()),
            "RPS":    list(RPS_VALUE.values()),
        }),
        on="market", how="inner",
    )
    df["has_CB"]         = df["market"].map(HAS_CB)
    df["classification"] = df["market"].map(CLASSIFICATION)
    df["rank_RPS"]       = _rank(df["RPS"].values)
    df["rank_H_stat"]    = _rank(df["H_stat"].values)

    if len(df) != 8:
        print(f"[WARN] merged on {len(df)} markets; RPS table expects 8. Check inputs.")

    # ---- Section A: primary Spearman
    primary = h2_spearman(df)
    print(f"\n[A] H2 Spearman  (rho(H_stat, RPS))")
    print("-" * 88)
    print(f"  rho = {primary['rho']:.4f}   p = {primary['p_value']:.4g}   n = {primary['n']}")
    print(f"  threshold: rho > {RHO_THRESHOLD:.2f} AND p < {P_THRESHOLD:.2f}")
    print(f"  VERDICT: {primary['verdict']}")

    # ---- Section B: bootstrap CI
    boot = bootstrap_ci(df)
    print(f"\n[B] Bootstrap 95% CI for rho  (10,000 resamples, seed={RNG_SEED})")
    print("-" * 88)
    print(f"  95% CI: [{boot['ci95_low']:.3f}, {boot['ci95_high']:.3f}]   "
          f"mean={boot['mean']:.3f}  sd={boot['std']:.3f}")

    # ---- Section C: Monte Carlo sensitivity
    mc = mc_sensitivity(df)
    print(f"\n[C] Measurement-noise sensitivity  (RPS +/- 0.05 Gaussian, 10,000 trials)")
    print("-" * 88)
    print(f"  rho distribution: mean={mc['rho_mean']:.3f}  sd={mc['rho_std']:.3f}")
    print(f"  [p5, p50, p95] = "
          f"[{mc['rho_p05']:.3f}, {mc['rho_p50']:.3f}, {mc['rho_p95']:.3f}]")
    print(f"  min={mc['rho_min']:.3f}  max={mc['rho_max']:.3f}")
    print(f"  P(rho > {RHO_THRESHOLD:.2f}) = {mc['frac_rho_gt_threshold']*100:.2f}% of MC trials")

    # ---- Section D: subpanels
    strata = stratified_subpanels(df)
    print(f"\n[D] Stratified robustness — subpanel Spearman")
    print("-" * 88)
    print(f"  {'subpanel':<22} {'n':>3}  {'rho':>8}  {'p':>9}   note")
    for s in strata:
        rho_s = f"{s['rho_RPS']:>8.3f}" if s['rho_RPS'] is not None else f"{'n/a':>8}"
        p_s   = f"{s['p_RPS']:>9.4f}" if s['p_RPS'] is not None else f"{'n/a':>9}"
        print(f"  {s['subpanel']:<22} {s['n']:>3}  {rho_s}  {p_s}   {s['note']}")

    # ---- Outputs
    cmp_csv = os.path.join(OUTPUT_DIR, "h2_rps_panel.csv")
    cmp = df[[
        "market", "classification", "has_CB",
        "H_stat", "RPS", "rank_H_stat", "rank_RPS",
    ]].sort_values("rank_H_stat").reset_index(drop=True)
    cmp.to_csv(cmp_csv, index=False)
    print(f"\nPanel CSV: {cmp_csv}")

    payload = {
        "status": "PRIMARY H2 test (supersedes composite pre-registered b130b0f)",
        "pre_registration_commit": "b130b0f",
        "pre_registration_specification": "MS_index composite (weights 0.4/0.3/0.3)",
        "active_specification":           "RPS (single variable)",
        "supersession_reason": (
            "Composite weights chosen qualitatively with no derivation; "
            "components measured in incompatible units; rho-magnitude "
            "against composite carried uncontrolled author degree of freedom."
        ),
        "h2_primary": primary,
        "bootstrap_95ci_for_rho": boot,
        "monte_carlo_sensitivity_RPS_noise_sd_0p05": mc,
        "stratified_subpanels": strata,
        "rps_sources_note": (
            "Values sourced from VinaCapital 2024, PSE 2023 Annual Report, "
            "ASIFMA 2022, NSE India FY25, SIFMA 2024, MEMX 2025, SQ Magazine "
            "2026, JPX 2024, and aggregated crypto-exchange data. All ex-ante "
            "microstructure facts; none derived from the return series."
        ),
    }
    json_path = os.path.join(OUTPUT_DIR, "h2_rps_validation.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"JSON: {json_path}")

    print("\n" + "=" * 88)
    print("H2 PRIMARY TEST — SUMMARY")
    print("=" * 88)
    print(f"  rho(H_stat, RPS) = {primary['rho']:.3f}   p = {primary['p_value']:.4g}"
          f"   VERDICT: {primary['verdict']}")
    print(f"  95% CI: [{boot['ci95_low']:.3f}, {boot['ci95_high']:.3f}]")
    print(f"  MC P(rho > 0.5) under RPS +/- 0.05 noise: "
          f"{mc['frac_rho_gt_threshold']*100:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
