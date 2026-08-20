"""
Phase 2b — Hysteresis robustness (T4 extended to 8 markets).
H5 SCIENTIFICALLY REFINED (post-hoc, 2026-04-19).

ORIGINAL (pre-registered b130b0f). For each market, fit the Plane-1 GMM
ONCE, then apply three hysteresis configs to the same fitted classifier and
report p(Det/Tra/Sto), regime durations, and filtered flip-rate under each
config. Pre-reg H5 verdict per market: PASS iff max(p_tra) - min(p_tra)
across configs < 5 pp.

REFACTOR (2026-04-19). Adds block-bootstrap confidence intervals on both
the per-config p_tra point estimates and the spread statistic itself. The
bootstrap is *joint* — a single set of circular-block indices is drawn and
applied to all 3 config-specific filtered label sequences, so correlated
sampling noise cancels inside the spread and the resulting CI reflects the
real uncertainty on `max - min`. The refactor is additive: the legacy CSV
columns (config point-estimates, spread, verdict) are unchanged and
regression-checked against the pre-reg archive.

Configs (from pre_registration/hypotheses_v2_combined.md):
  A_current: delta_hard=0.60, delta_soft=0.35, t_persist=8   (production)
  B_looser : delta_hard=0.50, delta_soft=0.30, t_persist=6
  C_tighter: delta_hard=0.70, delta_soft=0.40, t_persist=10

H5 pre-reg verdict per market: PASS iff max(p_tra) - min(p_tra) across
configs < 5 pp.
H5 refined verdict per market:
  PASS_DECISIVE    spread_ci_hi < 0.05
  PASS_BORDERLINE  spread < 0.05 but spread_ci_hi >= 0.05
  REJECT_BORDERLINE spread >= 0.05 but spread_ci_lo < 0.05
  REJECT_DECISIVE  spread_ci_lo >= 0.05

Outputs:
  validation/results_v2/hysteresis_robustness_v2.csv     (legacy, unchanged)
  validation/results_v2/hysteresis_robustness_v2.json    (legacy, unchanged)
  validation/results_v2/h5_refined.csv                   (bootstrap CIs)

Run:
  python validation/hysteresis_robustness_v2.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import numpy as np
import pandas as pd

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from skills.ds_skill import (
    EntropyPhaseSpaceClassifier,
    HysteresisGMMWrapper,
)
from validation._features import (
    load_ohlcv, build_plane1_features, flip_rate_per_year, SPE_Z_WIN,
)
from validation._regression_guard import guard as _reg_guard
from validation.h3_h4_h5.regime_duration import regime_duration_stats, NATIVE_BPY
from validation.h2_magnitude.cross_market_v2 import (
    MARKETS, START, END,
    _circular_block_indices,
)

OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2")
ARCHIVE_DIR = os.path.join(OUTPUT_DIR, "prereg_b130b0f")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COMMON_START = "2020-01-01"

CONFIGS: dict[str, dict[str, Any]] = {
    "A_current": dict(delta_hard=0.60, delta_soft=0.35, t_persist=8),
    "B_looser":  dict(delta_hard=0.50, delta_soft=0.30, t_persist=6),
    "C_tighter": dict(delta_hard=0.70, delta_soft=0.40, t_persist=10),
}

H5_SPREAD_THRESHOLD = 0.05   # H5 rejects if any market's p_tra spread > 5pp

# Refinement constants
BOOT_BLOCK = 20
N_BOOT = 2000
RNG_SEED = 42


def _slice_common(labels: pd.Series) -> pd.Series:
    s = labels.copy()
    s.index = pd.to_datetime(s.index)
    return s.loc[s.index >= COMMON_START]


def _joint_bootstrap(label_arrs: dict[str, np.ndarray], block: int,
                     n_boot: int, seed: int, alpha: float = 0.05
                     ) -> dict[str, Any]:
    """Joint circular block bootstrap across all 3 configs.

    For each bootstrap draw: sample the SAME circular block indices once,
    then apply them to each config's filtered label sequence. This is the
    correct null for the `spread` stat because sampling noise is shared
    across configs (same GMM, same fwd bars) and therefore cancels.

    Returns per-config p_tra CIs + spread CI.
    """
    # All three configs share the same index, so pick any
    any_arr = next(iter(label_arrs.values()))
    n = len(any_arr)
    rng = np.random.default_rng(seed)
    idx_mat = _circular_block_indices(n, block, n_boot, rng)  # (n_boot, n)

    boot_p = {}
    for cfg_name, arr in label_arrs.items():
        # (n_boot, n) bool matrix -> row-mean = p_tra per bootstrap draw
        boot_p[cfg_name] = np.mean(arr[idx_mat] == 1, axis=1)

    # Per-config CI
    per_cfg_ci = {}
    for cfg_name, bp in boot_p.items():
        per_cfg_ci[cfg_name] = {
            "ci_lo": float(np.percentile(bp, 100 * alpha / 2)),
            "ci_hi": float(np.percentile(bp, 100 * (1 - alpha / 2))),
            "mean":  float(bp.mean()),
            "std":   float(bp.std()),
        }

    # Spread per bootstrap draw: max - min across configs
    stacked = np.stack([boot_p[k] for k in label_arrs.keys()], axis=0)  # (3, n_boot)
    spread_boot = stacked.max(axis=0) - stacked.min(axis=0)
    spread_ci = {
        "ci_lo": float(np.percentile(spread_boot, 100 * alpha / 2)),
        "ci_hi": float(np.percentile(spread_boot, 100 * (1 - alpha / 2))),
        "mean":  float(spread_boot.mean()),
        "std":   float(spread_boot.std()),
        "frac_gt_threshold": float((spread_boot > H5_SPREAD_THRESHOLD).mean()),
    }

    return {"per_config_ci": per_cfg_ci, "spread_ci": spread_ci}


def _h5_refined_verdict(spread: float, ci_lo: float, ci_hi: float) -> str:
    thr = H5_SPREAD_THRESHOLD
    if spread < thr and ci_hi < thr:
        return "PASS_DECISIVE"
    if spread < thr and ci_hi >= thr:
        return "PASS_BORDERLINE"
    if spread >= thr and ci_lo < thr:
        return "REJECT_BORDERLINE"
    return "REJECT_DECISIVE"


def _analyze_market(cfg: dict[str, Any]) -> dict[str, Any] | None:
    name = cfg["name"]
    print(f"\n[{name}] fitting GMM once, then 3 hysteresis configs + joint bootstrap ...")

    try:
        t0 = time.time()
        df = load_ohlcv(name, cfg["ticker"], cfg["source"], START, END)
        feat = build_plane1_features(df)
    except Exception as e:
        print(f"  [SKIP] data load failed: {type(e).__name__}: {e}")
        return None

    if len(feat) < SPE_Z_WIN:
        print(f"  [SKIP] insufficient labelable bars: {len(feat)}")
        return None

    clf = EntropyPhaseSpaceClassifier(n_components=3, random_state=42)
    clf.fit_predict(feat.values)
    print(f"  GMM fitted on {len(feat)} bars ({time.time()-t0:.1f}s)")

    rows_per_config = []
    label_arrs: dict[str, np.ndarray] = {}
    for cfg_name, hparams in CONFIGS.items():
        wrapper = HysteresisGMMWrapper(clf, **hparams)
        filt_arr = wrapper.transform(feat.values)
        labels = pd.Series(filt_arr, index=feat.index, name=f"filt_{cfg_name}")
        labels_common = _slice_common(labels)

        stats = regime_duration_stats(labels_common, name)
        fpy = flip_rate_per_year(labels_common)

        label_arrs[cfg_name] = labels_common.astype(int).values

        rows_per_config.append({
            "market":     name,
            "category":   cfg["category"],
            "config":     cfg_name,
            "delta_hard": hparams["delta_hard"],
            "delta_soft": hparams["delta_soft"],
            "t_persist":  hparams["t_persist"],
            "n_bars":     int(stats.n_bars),
            "flips_per_year": round(fpy, 2),
            "p_det":      round(stats.label_share[0], 3),
            "p_tra":      round(stats.label_share[1], 3),
            "p_sto":      round(stats.label_share[2], 3),
            "T_det_days": round(stats.by_regime_mean_days[0], 1),
            "T_tra_days": round(stats.by_regime_mean_days[1], 1),
            "T_sto_days": round(stats.by_regime_mean_days[2], 1),
            "overall_d":  round(stats.overall_mean_days, 1),
        })

    # spread check (pre-reg)
    p_tras = [row["p_tra"] for row in rows_per_config]
    spread = max(p_tras) - min(p_tras)
    verdict = "PASS" if spread < H5_SPREAD_THRESHOLD else "REJECT"

    for row in rows_per_config:
        row["p_tra_spread"] = round(spread, 3)
        row["H5_verdict"] = verdict

    # --- Joint bootstrap refinement
    # Equalize lengths across configs (wrapper may emit identical windows, but be safe)
    min_len = min(len(v) for v in label_arrs.values())
    label_arrs = {k: v[:min_len] for k, v in label_arrs.items()}

    t_b = time.time()
    boot = _joint_bootstrap(label_arrs, BOOT_BLOCK, N_BOOT, RNG_SEED)
    elapsed_b = time.time() - t_b

    refined = _h5_refined_verdict(
        spread, boot["spread_ci"]["ci_lo"], boot["spread_ci"]["ci_hi"]
    )

    print(f"  p(Tra) across configs: {p_tras}  spread={spread:.3f}  pre-reg H5={verdict}")
    print(
        f"  spread 95% CI: [{boot['spread_ci']['ci_lo']:.4f}, "
        f"{boot['spread_ci']['ci_hi']:.4f}]  -> refined={refined}  ({elapsed_b:.1f}s)"
    )

    return {
        "market": name,
        "category": cfg["category"],
        "rows": rows_per_config,
        "p_tra_spread": spread,
        "H5_verdict": verdict,
        "H5_verdict_refined": refined,
        "bootstrap": boot,
    }


def build_h5_refined_csv(market_results: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for mres in market_results:
        spread = mres["p_tra_spread"]
        sci = mres["bootstrap"]["spread_ci"]
        per_cfg = mres["bootstrap"]["per_config_ci"]
        row: dict[str, Any] = {
            "market":   mres["market"],
            "category": mres["category"],
            "spread":           round(spread, 4),
            "spread_ci_lo":     round(sci["ci_lo"], 4),
            "spread_ci_hi":     round(sci["ci_hi"], 4),
            "spread_boot_mean": round(sci["mean"], 4),
            "spread_boot_std":  round(sci["std"], 4),
            "spread_boot_P(>0.05)": round(sci["frac_gt_threshold"], 4),
            "H5_verdict_pre_reg":  mres["H5_verdict"],
            "H5_verdict_refined":  mres["H5_verdict_refined"],
        }
        # Per-config p_tra + CI
        for cfg_name in CONFIGS.keys():
            point = next(r["p_tra"] for r in mres["rows"] if r["config"] == cfg_name)
            ci = per_cfg[cfg_name]
            row[f"p_tra_{cfg_name}"] = round(point, 4)
            row[f"p_tra_{cfg_name}_ci_lo"] = round(ci["ci_lo"], 4)
            row[f"p_tra_{cfg_name}_ci_hi"] = round(ci["ci_hi"], 4)
        rows.append(row)
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "h5_refined.csv")
    df.to_csv(path, index=False)
    print(f"\nH5 refined CSV: {path}")
    return df


def regression_check_legacy(df_new: pd.DataFrame) -> None:
    """Guard the pre-registered legacy columns (see validation/_regression_guard).

    Keyed on market+config, since this artifact carries one row per hysteresis
    configuration rather than one row per market.
    """
    _reg_guard(
        df_new, "hysteresis_robustness_v2.csv", key=["market", "config"],
        num_cols=["delta_hard", "delta_soft", "t_persist", "n_bars",
                  "flips_per_year", "p_det", "p_tra", "p_sto", "T_det_days",
                  "T_tra_days", "T_sto_days", "overall_d", "p_tra_spread"],
        str_cols=["category", "H5_verdict"],
    )
def main() -> int:
    print("=" * 78)
    print("PHASE 2b — HYSTERESIS ROBUSTNESS (H5 REFINED) × 8 markets × 3 configs")
    print(f"Pre-registration commit: b130b0f   Refactor date: 2026-04-19")
    print("=" * 78)

    all_market_results = []
    all_rows: list[dict[str, Any]] = []

    for cfg in MARKETS:
        res = _analyze_market(cfg)
        if res is None:
            continue
        all_market_results.append(res)
        all_rows.extend(res["rows"])

    if not all_rows:
        print("\n[FATAL] no markets produced results.")
        return 1

    df = pd.DataFrame(all_rows)
    csv_path = os.path.join(OUTPUT_DIR, "hysteresis_robustness_v2.csv")
    df.to_csv(csv_path, index=False)

    json_path = os.path.join(OUTPUT_DIR, "hysteresis_robustness_v2.json")
    payload = {
        "pre_registration_commit": "b130b0f1f2769566eaf548181d6816eb31b1963e",
        "refactor_date": "2026-04-19",
        "configs": CONFIGS,
        "h5_spread_threshold": H5_SPREAD_THRESHOLD,
        "common_window_start": COMMON_START,
        "markets": [
            {
                "market":  m["market"],
                "category": m["category"],
                "rows":     m["rows"],
                "p_tra_spread":       m["p_tra_spread"],
                "H5_verdict":         m["H5_verdict"],
                "H5_verdict_refined": m["H5_verdict_refined"],
                "bootstrap":          m["bootstrap"],
            } for m in all_market_results
        ],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    print(f"\nSummary CSV: {csv_path}")
    print(f"JSON: {json_path}")

    refined_df = build_h5_refined_csv(all_market_results)

    print("\n" + "=" * 96)
    print("PHASE 2b ROBUSTNESS SUMMARY")
    print("=" * 96)
    cols = ["market", "category", "config", "flips_per_year",
            "p_det", "p_tra", "p_sto",
            "p_tra_spread", "H5_verdict"]
    print(df[cols].to_string(index=False))

    print("\n--- H5 PRE-REG CATEGORICAL VERDICTS (reported verbatim) ---")
    for res in all_market_results:
        flag = "  " if res["H5_verdict"] == "PASS" else "! "
        print(f"  {flag}{res['market']:<8} [{res['category']:<9}]  "
              f"spread={res['p_tra_spread']:.3f}  -> H5 {res['H5_verdict']}")

    print("\n--- H5 REFINED VERDICTS (joint-bootstrap CI context) ---")
    for res in all_market_results:
        flag = "  " if "PASS" in res["H5_verdict_refined"] else "! "
        sci = res["bootstrap"]["spread_ci"]
        print(f"  {flag}{res['market']:<8} [{res['category']:<9}]  "
              f"spread={res['p_tra_spread']:.3f}  "
              f"CI[{sci['ci_lo']:.4f}, {sci['ci_hi']:.4f}]  "
              f"P(>0.05)={sci['frac_gt_threshold']*100:5.1f}%  -> "
              f"{res['H5_verdict_refined']}")

    print("\n")
    regression_check_legacy(df)

    return 0


if __name__ == "__main__":
    sys.exit(main())
