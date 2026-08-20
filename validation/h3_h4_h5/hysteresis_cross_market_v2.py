"""
Phase 2 — Hysteresis, regime duration, and shuffle test across the 8-market panel.
H3 / H4 SCIENTIFICALLY REFINED (post-hoc, 2026-04-19).

ORIGINAL (pre-registered b130b0f, 2026-04-18). Per-market p(Deterministic / Transitional /
Stochastic) shares and regime durations under production hysteresis
(delta_hard=0.60, delta_soft=0.35, t_persist=8); H4 shuffle test with 10,000
label-level permutations.

REFACTOR (2026-04-19). Adds the missing statistical machinery flagged in §10
of paper_artifacts/paper_v2_1_combined_summary.md. All additions are
backward-compatible: the legacy `p_det`, `p_tra`, `p_sto`, `shuffle_p_value`,
`shuffle_verdict`, `filtered_flips_per_year` columns remain in
`hysteresis_summary_v2.csv` and a regression assertion at end-of-main diffs
them against the archived first-run outputs under
`validation/results_v2/prereg_b130b0f/`. The pre-reg categorical H3 verdict
is reported verbatim first; the axes below are refinements, not replacements.

Axes added:
  H3.#1 PER-MARKET CI: circular block-bootstrap 95% CI on p(Transitional)
    (block=20, n_boot=2000). Tells us whether a market whose p_tra sits on
    the wrong side of the pre-reg threshold (0.45 for frontier, 0.60 for
    developed) is decisively falsified or within sampling noise.
  H3.#2 CONTINUOUS: Spearman rho(p_tra, RPS) with bootstrap 95% CI and
    Monte-Carlo robustness under RPS +/- 0.05 Gaussian noise. Parallels the
    H2 treatment (h2_rps_validation.py) — tests whether the
    Transitional-Dominance gradient tracks microstructure monotonically
    even where the categorical thresholds fail.
  H3.#3 BH-FDR across 8-market bootstrap sign-p values for the distance to
    the nearest pre-reg threshold. Family-wise error rate at n=8.
  H4.#1 BLOCK-PERMUTATION SHUFFLE: re-runs the H4 null with block-shuffle
    (block in {5, 10, 20}) in addition to the label-level permutation.
    Larger blocks preserve more short-range autocorrelation, making the
    null stricter; if observed stays far below the null for all blocks,
    the verdict is robust.
  H4.#2 BH-FDR across 8-market shuffle p-values per block.

Pinned (DO NOT override):
    WPE m=3 tau=1 window=22, SampEn win=60, SPE_Z rolling win=504,
    GMM k=3 full-cov, random_state=42; hysteresis (0.60, 0.35, 8).

Outputs:
  validation/results_v2/<MARKET>_hysteresis.json              (extended)
  validation/results_v2/hysteresis_summary_v2.csv             (legacy cols + refined)
  validation/results_v2/h3_refined.csv                        (H3 bootstrap CI + FDR)
  validation/results_v2/h3_continuous.json                    (Spearman p_tra vs RPS)
  validation/results_v2/h4_block_permutation.csv              (H4 block shuffle)
  validation/results_v2/p_transitional_vs_rps.png             (H3 scatter)

Run:
  python validation/hysteresis_cross_market_v2.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

# Windows stdout fix (cp1252 -> utf-8) before any print containing unicode
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from validation._features import run_full_pipeline, flip_rate_per_year, SPE_Z_WIN
from validation._regression_guard import guard as _reg_guard
from validation.h3_h4_h5.regime_duration import regime_duration_stats, NATIVE_BPY
from validation.h3_h4_h5.shuffle_test import run_shuffle_test
from validation.h2_magnitude.cross_market_v2 import (
    MARKETS, RPS_VALUE, START, END,
    _circular_block_indices, _bh_fdr,
)

OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2")
ARCHIVE_DIR = os.path.join(OUTPUT_DIR, "prereg_b130b0f")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COMMON_START = "2020-01-01"
COMMON_END = END

# ==============================================================================
# REFINEMENT CONSTANTS
# ==============================================================================
BOOT_BLOCK = 20                # circular-block length for p_tra bootstrap
N_BOOT_P_TRA = 2000
N_BOOT_RHO = 10_000
N_MC_RHO = 10_000
RPS_NOISE_SD = 0.05
SHUFFLE_BLOCKS = [5, 10, 20]   # block sizes for H4.#1
N_PERM_BLOCK = 2000            # block permutations (smaller than H4 primary 10k)
RNG_SEED = 42

# Pre-reg H3 thresholds (from hypotheses_v2_combined.md)
H3_FRONTIER_LOWER = 0.55
H3_FRONTIER_FAIL  = 0.45
H3_DEVELOPED_UPPER = 0.50
H3_DEVELOPED_FAIL  = 0.60


# ==============================================================================
# SLICING / LOOKUP
# ==============================================================================
def _slice_common(labels: pd.Series) -> pd.Series:
    s = labels.copy()
    s.index = pd.to_datetime(s.index)
    return s.loc[(s.index >= COMMON_START) & (s.index <= COMMON_END)]


def _rps(market: str) -> float:
    return float(RPS_VALUE[market])


# ==============================================================================
# H3 PER-MARKET BOOTSTRAP CI
# ==============================================================================
def _p_tra_bootstrap_ci(labels: np.ndarray, block: int, n_boot: int,
                        seed: int, alpha: float = 0.05
                        ) -> tuple[float, float, np.ndarray]:
    """95% CI for p(Transitional) under circular block bootstrap.
    Preserves regime-duration autocorrelation (consecutive bars share a
    regime for ~20-100d, so bootstrap blocks must be comparable)."""
    n = len(labels)
    rng = np.random.default_rng(seed)
    idx_mat = _circular_block_indices(n, block, n_boot, rng)
    boot_p = np.mean(labels[idx_mat] == 1, axis=1)    # (n_boot,)
    lo = float(np.percentile(boot_p, 100 * alpha / 2))
    hi = float(np.percentile(boot_p, 100 * (1 - alpha / 2)))
    return lo, hi, boot_p


def _distance_to_nearest_threshold(p_tra: float, category: str
                                   ) -> tuple[float, str]:
    """Signed distance to the nearest pre-reg falsification threshold.
    Positive = on the PASS side; negative = on the FAIL side."""
    if category == "Frontier":
        return (p_tra - H3_FRONTIER_FAIL, "frontier_lower_fail")
    if category == "Developed":
        return (H3_DEVELOPED_FAIL - p_tra, "developed_upper_fail")
    return (float("nan"), "n/a")


def _bootstrap_wrong_side_p(boot_p: np.ndarray, category: str) -> float:
    """One-sided bootstrap p for the bootstrap distribution lying on the
    wrong side of the pre-reg threshold.
      Frontier: p = fraction of boot reps with p_tra < 0.45
      Developed: p = fraction of boot reps with p_tra > 0.60
    NaN for categories without a threshold."""
    if category == "Frontier":
        return float((boot_p < H3_FRONTIER_FAIL).mean())
    if category == "Developed":
        return float((boot_p > H3_DEVELOPED_FAIL).mean())
    return float("nan")


def _h3_categorical_verdict(p_tra: float, category: str) -> str:
    if category == "Frontier" and p_tra < H3_FRONTIER_FAIL:
        return "REJECT"
    if category == "Developed" and p_tra > H3_DEVELOPED_FAIL:
        return "REJECT"
    return "PASS"


def _h3_refined_verdict(p_tra: float, ci_lo: float, ci_hi: float,
                        category: str) -> str:
    """Refined verdict:
      REJECT_DECISIVE  -- CI lies entirely on the fail side
      REJECT_BORDERLINE -- point is on fail side but CI crosses threshold
      PASS_BORDERLINE   -- point is on pass side but CI crosses threshold
      PASS              -- CI lies entirely on pass side
      n/a               -- category without a pre-reg threshold"""
    if category == "Frontier":
        thr = H3_FRONTIER_FAIL
        if ci_hi < thr:
            return "REJECT_DECISIVE"
        if ci_lo < thr and p_tra < thr:
            return "REJECT_BORDERLINE"
        if ci_lo < thr <= p_tra:
            return "PASS_BORDERLINE"
        return "PASS"
    if category == "Developed":
        thr = H3_DEVELOPED_FAIL
        if ci_lo > thr:
            return "REJECT_DECISIVE"
        if ci_hi > thr and p_tra > thr:
            return "REJECT_BORDERLINE"
        if ci_hi > thr >= p_tra:
            return "PASS_BORDERLINE"
        return "PASS"
    return "n/a"


# ==============================================================================
# H4 BLOCK-PERMUTATION SHUFFLE
# ==============================================================================
def _flips_per_year(arr: np.ndarray, n_bars: int, trading_days: int = 252) -> float:
    return float((np.diff(arr) != 0).sum()) * trading_days / n_bars


def _block_shuffle_p(labels: np.ndarray, block: int, n_perm: int,
                     seed: int) -> dict[str, float]:
    """Block-permutation null: slice the label sequence into contiguous
    blocks of length `block`, shuffle BLOCK ORDER, recompute flip rate.
    Preserves within-block autocorrelation; breaks between-block structure."""
    n = len(labels)
    n_blocks = n // block
    if n_blocks < 2:
        return {"observed": float("nan"), "null_mean": float("nan"),
                "null_p05": float("nan"), "null_p95": float("nan"),
                "p_value": float("nan")}
    # core = complete blocks only; trailing bars (remainder) kept appended
    core = labels[: n_blocks * block].reshape(n_blocks, block)
    tail = labels[n_blocks * block:]
    rng = np.random.default_rng(seed)
    observed = _flips_per_year(labels, n)
    null = np.empty(n_perm, dtype=np.float64)
    for i in range(n_perm):
        order = rng.permutation(n_blocks)
        shuffled = np.concatenate([core[order].ravel(), tail])
        null[i] = _flips_per_year(shuffled, n)
    p = float((null <= observed).mean())
    return {
        "observed":  observed,
        "null_mean": float(null.mean()),
        "null_p05":  float(np.percentile(null, 5)),
        "null_p95":  float(np.percentile(null, 95)),
        "p_value":   p,
    }


# ==============================================================================
# H3 CONTINUOUS: Spearman(p_tra, RPS)
# ==============================================================================
def _safe_spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    if len(x) < 2 or len(set(x)) < 2 or len(set(y)) < 2:
        return float("nan"), float("nan")
    rho, p = spearmanr(x, y)
    return float(rho), float(p)


def _bootstrap_rho_ci(p_tra: np.ndarray, rps: np.ndarray,
                      n_boot: int, seed: int) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    n = len(p_tra)
    rhos = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(set(p_tra[idx])) < 2 or len(set(rps[idx])) < 2:
            rhos[i] = np.nan
            continue
        rhos[i] = spearmanr(p_tra[idx], rps[idx])[0]
    rhos = rhos[~np.isnan(rhos)]
    return {
        "n_resamples_effective": int(len(rhos)),
        "ci95_low":  float(np.percentile(rhos,  2.5)),
        "ci95_high": float(np.percentile(rhos, 97.5)),
        "mean":      float(np.mean(rhos)),
        "std":       float(np.std(rhos)),
    }


def _mc_rho_sensitivity(p_tra: np.ndarray, rps: np.ndarray,
                        n_mc: int, noise_sd: float, seed: int
                        ) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    n = len(rps)
    rhos = np.empty(n_mc)
    for i in range(n_mc):
        perturbed = np.clip(rps + rng.normal(0.0, noise_sd, size=n), 0.0, 1.0)
        if len(set(perturbed)) < 2:
            rhos[i] = np.nan
            continue
        rhos[i] = spearmanr(p_tra, perturbed)[0]
    rhos = rhos[~np.isnan(rhos)]
    return {
        "n_trials_effective": int(len(rhos)),
        "noise_sd":   noise_sd,
        "rho_mean":   float(rhos.mean()),
        "rho_std":    float(rhos.std()),
        "rho_p05":    float(np.percentile(rhos,  5)),
        "rho_p50":    float(np.percentile(rhos, 50)),
        "rho_p95":    float(np.percentile(rhos, 95)),
        "frac_rho_gt_0p5": float((rhos > 0.5).mean()),
    }


# ==============================================================================
# PER-MARKET PIPELINE
# ==============================================================================
def analyze_one(cfg: dict[str, Any]) -> dict[str, Any] | None:
    name = cfg["name"]
    print(f"\n[{name}] {cfg['ticker']} via {cfg['source']}")

    t0 = time.time()
    try:
        out = run_full_pipeline(
            market=name,
            ticker=cfg["ticker"],
            source=cfg["source"],
            start=START, end=END,
        )
    except Exception as e:
        print(f"  [SKIP] pipeline failed: {type(e).__name__}: {e}")
        return None

    raw = out["raw_labels"]
    filt = out["filtered_labels"]
    raw_common = _slice_common(raw)
    filt_common = _slice_common(filt)

    if len(filt_common) < SPE_Z_WIN:
        print(f"  [SKIP] filtered common window too short: {len(filt_common)}")
        return None

    raw_fpy = flip_rate_per_year(raw_common)
    filt_fpy = flip_rate_per_year(filt_common)

    bpy = NATIVE_BPY.get(name, 252)
    dur = regime_duration_stats(filt_common, name)

    # H4 primary (pre-reg): label-level shuffle
    shuf = run_shuffle_test(
        filt_common,
        market=name,
        start=str(filt_common.index[0].date()),
        end=str(filt_common.index[-1].date()),
    )

    # H3 #1: bootstrap CI on p_tra (filtered, canonical)
    arr = filt_common.astype(int).values
    ci_lo, ci_hi, boot_p = _p_tra_bootstrap_ci(arr, BOOT_BLOCK, N_BOOT_P_TRA, RNG_SEED)
    wrong_side_p = _bootstrap_wrong_side_p(boot_p, cfg["category"])
    distance, distance_spec = _distance_to_nearest_threshold(
        float(dur.label_share[1]), cfg["category"]
    )

    # H3 raw counterpart (§9.6 hysteresis-impact comparison): p_tra and
    # bootstrap CI on raw_labels, BEFORE hysteresis. Same RNG seed as the
    # filtered run so the only thing that differs is the label series.
    arr_raw = raw_common.astype(int).values
    p_det_raw = float((arr_raw == 0).mean())
    p_tra_raw = float((arr_raw == 1).mean())
    p_sto_raw = float((arr_raw == 2).mean())
    ci_lo_raw, ci_hi_raw, _ = _p_tra_bootstrap_ci(
        arr_raw, BOOT_BLOCK, N_BOOT_P_TRA, RNG_SEED
    )

    # H4 #1: block-permutation shuffle at multiple block sizes
    block_shuffle = {
        b: _block_shuffle_p(arr, b, N_PERM_BLOCK, RNG_SEED + b)
        for b in SHUFFLE_BLOCKS
    }

    verdict_cat = _h3_categorical_verdict(float(dur.label_share[1]), cfg["category"])
    verdict_ref = _h3_refined_verdict(float(dur.label_share[1]), ci_lo, ci_hi,
                                      cfg["category"])

    result = {
        "market": name,
        "ticker": cfg["ticker"],
        "category": cfg["category"],
        "common_window": [COMMON_START, str(filt_common.index[-1].date())],
        "n_bars": int(len(filt_common)),
        "bars_per_year": bpy,
        "raw_flips_per_year": float(raw_fpy),
        "filtered_flips_per_year": float(filt_fpy),
        "reduction_pct": float(100.0 * (1 - filt_fpy / raw_fpy)) if raw_fpy > 0 else float("nan"),
        "p_det": float(dur.label_share[0]),
        "p_tra": float(dur.label_share[1]),
        "p_sto": float(dur.label_share[2]),
        # H3 refinement
        "p_tra_ci_lo": ci_lo,
        "p_tra_ci_hi": ci_hi,
        "distance_to_threshold": distance,
        "distance_spec": distance_spec,
        "threshold_wrong_side_p": wrong_side_p,
        "h3_verdict_categorical": verdict_cat,
        "h3_verdict_refined":     verdict_ref,
        "T_det_days": float(dur.by_regime_mean_days[0]),
        "T_tra_days": float(dur.by_regime_mean_days[1]),
        "T_sto_days": float(dur.by_regime_mean_days[2]),
        "overall_mean_days": float(dur.overall_mean_days),
        "n_segments": int(dur.n_segments),
        # H4 primary (pre-reg)
        "shuffle_observed": float(shuf.observed_flip_rate),
        "shuffle_null_mean": float(shuf.null_mean),
        "shuffle_null_p05": float(shuf.null_p05),
        "shuffle_null_p95": float(shuf.null_p95),
        "shuffle_p_value": float(shuf.p_value),
        "shuffle_verdict": shuf.verdict,
        # H4 refinement: block-permutation p-values
        "shuffle_block_p": {str(b): block_shuffle[b]["p_value"]
                            for b in SHUFFLE_BLOCKS},
        "shuffle_block_null_mean": {str(b): block_shuffle[b]["null_mean"]
                                    for b in SHUFFLE_BLOCKS},
        "rps": _rps(name),
        # §9.6 hysteresis-impact: raw-labels p_tra counterpart
        "p_det_raw":         p_det_raw,
        "p_tra_raw":         p_tra_raw,
        "p_sto_raw":         p_sto_raw,
        "p_tra_raw_ci_lo":   ci_lo_raw,
        "p_tra_raw_ci_hi":   ci_hi_raw,
    }

    elapsed = time.time() - t0
    print(
        f"  raw={raw_fpy:5.2f}/yr  filt={filt_fpy:5.2f}/yr "
        f"({result['reduction_pct']:.0f}% reduction)"
    )
    print(
        f"  p(Det/Tra/Sto) = {result['p_det']:.1%} / {result['p_tra']:.1%} / {result['p_sto']:.1%}"
    )
    print(
        f"  p_tra 95% CI: [{ci_lo:.3f}, {ci_hi:.3f}]  "
        f"H3 cat={verdict_cat}  refined={verdict_ref}"
    )
    print(
        f"  T_det={result['T_det_days']:.1f}d  T_tra={result['T_tra_days']:.1f}d  T_sto={result['T_sto_days']:.1f}d"
    )
    block_p_str = "  ".join(f"b{b}={block_shuffle[b]['p_value']:.4f}" for b in SHUFFLE_BLOCKS)
    print(
        f"  shuffle: p(label)={shuf.p_value:.4f} [{shuf.verdict}]  block: {block_p_str}  ({elapsed:.1f}s)"
    )

    # per-market json
    path = os.path.join(OUTPUT_DIR, f"{name}_hysteresis.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=float)
    return result


# ==============================================================================
# CSV WRITERS
# ==============================================================================
def build_summary_csv(results: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            "market":                   r["market"],
            "category":                 r["category"],
            "raw_flips_per_year":       round(r["raw_flips_per_year"], 2),
            "filtered_flips_per_year":  round(r["filtered_flips_per_year"], 2),
            "reduction_pct":            round(r["reduction_pct"], 1),
            "p_det":                    round(r["p_det"], 3),
            "p_tra":                    round(r["p_tra"], 3),
            "p_sto":                    round(r["p_sto"], 3),
            "p_tra_ci_lo":              round(r["p_tra_ci_lo"], 3),
            "p_tra_ci_hi":              round(r["p_tra_ci_hi"], 3),
            "h3_verdict_categorical":   r["h3_verdict_categorical"],
            "h3_verdict_refined":       r["h3_verdict_refined"],
            "T_det_days":               round(r["T_det_days"], 1),
            "T_tra_days":               round(r["T_tra_days"], 1),
            "T_sto_days":               round(r["T_sto_days"], 1),
            "overall_mean_days":        round(r["overall_mean_days"], 1),
            "shuffle_observed":         round(r["shuffle_observed"], 2),
            "shuffle_null_mean":        round(r["shuffle_null_mean"], 2),
            "shuffle_p_value":          r["shuffle_p_value"],
            "shuffle_verdict":          r["shuffle_verdict"],
            "rps":                      round(r["rps"], 3),
        })
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "h3_h4_h5/hysteresis_summary_v2.csv")
    df.to_csv(path, index=False)
    print(f"\nSummary CSV: {path}")
    return df


def build_h3_refined_csv(results: list[dict[str, Any]]) -> pd.DataFrame:
    wrong_side = np.array([r["threshold_wrong_side_p"] for r in results], dtype=float)
    bh_q = _bh_fdr(wrong_side)
    rows = []
    for r, q in zip(results, bh_q):
        rows.append({
            "market":                    r["market"],
            "category":                  r["category"],
            "p_tra":                     round(r["p_tra"], 3),
            "p_tra_ci_lo":               round(r["p_tra_ci_lo"], 3),
            "p_tra_ci_hi":               round(r["p_tra_ci_hi"], 3),
            "distance_to_threshold":     round(r["distance_to_threshold"], 4) if not np.isnan(r["distance_to_threshold"]) else None,
            "distance_spec":             r["distance_spec"],
            "threshold_wrong_side_p":    round(r["threshold_wrong_side_p"], 4) if not np.isnan(r["threshold_wrong_side_p"]) else None,
            "bh_fdr_q":                  round(float(q), 4) if not np.isnan(q) else None,
            "h3_verdict_categorical":    r["h3_verdict_categorical"],
            "h3_verdict_refined":        r["h3_verdict_refined"],
            "rps":                       round(r["rps"], 3),
            # §9.6 hysteresis-impact: raw counterpart of p_tra
            "p_tra_raw":                 round(r["p_tra_raw"], 3),
            "p_tra_raw_ci_lo":           round(r["p_tra_raw_ci_lo"], 3),
            "p_tra_raw_ci_hi":           round(r["p_tra_raw_ci_hi"], 3),
            "delta_p_tra_filt_minus_raw": round(r["p_tra"] - r["p_tra_raw"], 3),
        })
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "h3_h4_h5/h3_refined.csv")
    df.to_csv(path, index=False)
    print(f"H3 refined CSV: {path}")
    return df


def build_h4_block_permutation_csv(results: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    # collect per-block p across markets for BH-FDR
    per_block_p = {b: [] for b in SHUFFLE_BLOCKS}
    for r in results:
        for b in SHUFFLE_BLOCKS:
            per_block_p[b].append(r["shuffle_block_p"][str(b)])
    per_block_q = {b: _bh_fdr(np.array(per_block_p[b], dtype=float))
                   for b in SHUFFLE_BLOCKS}
    for i, r in enumerate(results):
        row = {
            "market":   r["market"],
            "category": r["category"],
            "shuffle_observed":   round(r["shuffle_observed"], 2),
            "shuffle_p_label":    r["shuffle_p_value"],       # pre-reg primary
        }
        for b in SHUFFLE_BLOCKS:
            row[f"shuffle_p_block{b}"] = r["shuffle_block_p"][str(b)]
            row[f"shuffle_null_mean_block{b}"] = round(
                r["shuffle_block_null_mean"][str(b)], 2
            )
            row[f"bh_fdr_q_block{b}"] = round(float(per_block_q[b][i]), 4) \
                if not np.isnan(per_block_q[b][i]) else None
        rows.append(row)
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "h3_h4_h5/h4_block_permutation.csv")
    df.to_csv(path, index=False)
    print(f"H4 block-permutation CSV: {path}")
    return df


def build_h3_continuous_json(results: list[dict[str, Any]]) -> dict[str, Any]:
    markets = [r["market"] for r in results]
    p_tra = np.array([r["p_tra"] for r in results], dtype=float)
    rps = np.array([r["rps"] for r in results], dtype=float)

    rho, p = _safe_spearman(p_tra, rps)
    boot = _bootstrap_rho_ci(p_tra, rps, N_BOOT_RHO, RNG_SEED)
    mc = _mc_rho_sensitivity(p_tra, rps, N_MC_RHO, RPS_NOISE_SD, RNG_SEED + 1)

    # Subpanels
    cb_yes = {"VNINDEX", "BVB", "KOSPI", "NIFTY", "SPX", "NIKKEI"}  # see h2_rps_validation.HAS_CB
    cb_no  = {"FTSE", "BTC"}
    fe     = {"VNINDEX", "BVB", "KOSPI", "NIFTY"}
    dev    = {"SPX", "FTSE", "NIKKEI"}
    subpanels = []
    for name, mset in [
        ("full_panel",            set(markets)),
        ("circuit_breaker_yes",   cb_yes),
        ("circuit_breaker_no",    cb_no),
        ("frontier_emerging",     fe),
        ("developed_only",        dev),
    ]:
        mask = np.array([m in mset for m in markets])
        if mask.sum() < 2:
            subpanels.append({"subpanel": name, "n": int(mask.sum()),
                              "rho": None, "p_value": None,
                              "note": "n<2, skipped"})
            continue
        rho_s, p_s = _safe_spearman(p_tra[mask], rps[mask])
        subpanels.append({
            "subpanel": name,
            "n": int(mask.sum()),
            "markets": [m for m, keep in zip(markets, mask) if keep],
            "rho": round(rho_s, 4) if not np.isnan(rho_s) else None,
            "p_value": float(p_s) if not np.isnan(p_s) else None,
            "note": "descriptive only — n<4" if mask.sum() < 4 else "",
        })

    payload = {
        "spec": "H3 CONTINUOUS — Spearman rho(p_tra, RPS) on 8-market panel",
        "n": len(markets),
        "rho": round(rho, 4),
        "p_value": float(p),
        "bootstrap_95ci_for_rho": boot,
        "monte_carlo_sensitivity_RPS_noise_sd_0p05": mc,
        "stratified_subpanels": subpanels,
        "expected_sign": "positive (higher RPS -> higher p_tra, per pre-reg logic)",
        "note": (
            "Continuous companion to the pre-reg categorical H3 verdict. "
            "Does NOT replace the frontier>0.55 / developed<0.50 / diff>10pp "
            "pre-reg rule; it tests whether p_tra tracks RPS monotonically."
        ),
    }
    path = os.path.join(OUTPUT_DIR, "h3_h4_h5/h3_continuous.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"H3 continuous JSON: {path}  [rho={rho:.3f}, p={p:.4g}]")
    return payload


# ==============================================================================
# PLOTTING
# ==============================================================================
def plot_p_tra_vs_rps(results: list[dict]) -> None:
    xs = [r["rps"] for r in results]
    ys = [r["p_tra"] for r in results]
    ylo = [r["p_tra_ci_lo"] for r in results]
    yhi = [r["p_tra_ci_hi"] for r in results]
    labels = [r["market"] for r in results]
    cats = [r["category"] for r in results]
    cat_colors = {"Frontier": "#c0392b", "Emerging": "#d35400",
                  "Developed": "#2980b9", "Crypto": "#8e44ad"}
    fig, ax = plt.subplots(figsize=(9, 6.5))
    for x, y, lo, hi, lbl, cat in zip(xs, ys, ylo, yhi, labels, cats):
        ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], fmt="o",
                    color=cat_colors.get(cat, "gray"),
                    markersize=9, capsize=4, alpha=0.9,
                    markeredgecolor="black", markeredgewidth=0.8,
                    label=cat)
        ax.annotate(lbl, (x, y), xytext=(6, 6),
                    textcoords="offset points", fontsize=9)
    handles, lbls = ax.get_legend_handles_labels()
    uniq = dict(zip(lbls, handles))
    ax.legend(uniq.values(), uniq.keys(), loc="best")
    ax.axhline(H3_FRONTIER_LOWER, linestyle="--", color="gray", alpha=0.5,
               label=f"H3 frontier lower ({H3_FRONTIER_LOWER})")
    ax.axhline(H3_DEVELOPED_UPPER, linestyle=":", color="gray", alpha=0.5,
               label=f"H3 developed upper ({H3_DEVELOPED_UPPER})")
    ax.axhline(H3_FRONTIER_FAIL, linestyle="-", color="red", alpha=0.35,
               label=f"H3 frontier FAIL ({H3_FRONTIER_FAIL})")
    ax.axhline(H3_DEVELOPED_FAIL, linestyle="-", color="red", alpha=0.35,
               label=f"H3 developed FAIL ({H3_DEVELOPED_FAIL})")
    ax.set_xlabel("Retail Participation Share (RPS)")
    ax.set_ylabel("p(Transitional) with 95% block-bootstrap CI")
    ax.set_title("Transitional Dominance vs RPS (H3 — pre-reg + bootstrap CI)")
    ax.grid(alpha=0.3)
    out = os.path.join(OUTPUT_DIR, "h3_h4_h5/p_transitional_vs_rps.png")
    plt.tight_layout()
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"H3 figure: {out}")


# ==============================================================================
# REGRESSION CHECK AGAINST PRE-REG ARCHIVE
# ==============================================================================
def regression_check_legacy(df_new: pd.DataFrame) -> None:
    """Guard the pre-registered legacy columns (see validation/_regression_guard)."""
    _reg_guard(
        df_new, "h3_h4_h5/hysteresis_summary_v2.csv",
        num_cols=["raw_flips_per_year", "filtered_flips_per_year", "reduction_pct",
                  "p_det", "p_tra", "p_sto", "T_det_days", "T_tra_days",
                  "T_sto_days", "overall_mean_days", "shuffle_observed",
                  "shuffle_null_mean", "shuffle_p_value"],
        str_cols=["category", "shuffle_verdict"],
    )
# ==============================================================================
# MAIN
# ==============================================================================
def main() -> int:
    print("=" * 78)
    print("PHASE 2 — HYSTERESIS + DURATION + SHUFFLE (H3/H4 REFINED) × 8 markets")
    print(f"Pre-registration commit: b130b0f   Refactor date: 2026-04-19")
    print(f"Common window: {COMMON_START} -> {COMMON_END}")
    print("=" * 78)

    results: list[dict] = []
    for cfg in MARKETS:
        r = analyze_one(cfg)
        if r is not None:
            results.append(r)

    if not results:
        print("\n[FATAL] no markets produced valid results.")
        return 1

    summary = build_summary_csv(results)
    h3_refined = build_h3_refined_csv(results)
    h4_block = build_h4_block_permutation_csv(results)
    h3_cont = build_h3_continuous_json(results)
    plot_p_tra_vs_rps(results)

    print("\n" + "=" * 78)
    print("PHASE 2 SUMMARY")
    print("=" * 78)
    display_cols = [
        "market", "category", "p_det", "p_tra", "p_sto",
        "p_tra_ci_lo", "p_tra_ci_hi", "shuffle_p_value",
        "h3_verdict_categorical", "h3_verdict_refined",
    ]
    print(summary[display_cols].to_string(index=False))

    # --- Pre-reg categorical verdicts (headline) ---
    print("\n--- H3 PRE-REG CATEGORICAL VERDICTS (reported verbatim) ---")
    for r in results:
        flag = "  " if r["h3_verdict_categorical"] == "PASS" else "! "
        print(f"  {flag}{r['market']:<8} [{r['category']:<9}]  "
              f"p_tra={r['p_tra']:.3f}  -> H3 {r['h3_verdict_categorical']}")

    print("\n--- H3 REFINED VERDICTS (bootstrap CI context) ---")
    for r in results:
        flag = "  " if "PASS" in r["h3_verdict_refined"] else "! "
        print(f"  {flag}{r['market']:<8} [{r['category']:<9}]  "
              f"p_tra={r['p_tra']:.3f} CI[{r['p_tra_ci_lo']:.3f}, {r['p_tra_ci_hi']:.3f}]"
              f"  -> {r['h3_verdict_refined']}")

    print("\n--- H3 CONTINUOUS: Spearman(p_tra, RPS) ---")
    print(f"  rho = {h3_cont['rho']:.3f}   p = {h3_cont['p_value']:.4g}   n = {h3_cont['n']}")
    boot = h3_cont["bootstrap_95ci_for_rho"]
    mc = h3_cont["monte_carlo_sensitivity_RPS_noise_sd_0p05"]
    print(f"  95% CI: [{boot['ci95_low']:.3f}, {boot['ci95_high']:.3f}]  "
          f"MC P(rho>0.5) = {mc['frac_rho_gt_0p5']*100:.1f}%")

    print("\n--- H4 VERDICTS (pre-reg label-shuffle + block-permutation robustness) ---")
    for r in results:
        block_str = "  ".join(
            f"b{b}={r['shuffle_block_p'][str(b)]:.4f}" for b in SHUFFLE_BLOCKS
        )
        print(f"  {r['market']:<8} [{r['category']:<9}]  "
              f"p(label)={r['shuffle_p_value']:.4f} [{r['shuffle_verdict']}]  "
              f"block: {block_str}")

    print("\n")
    regression_check_legacy(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
