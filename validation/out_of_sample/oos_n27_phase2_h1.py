"""
oos-n27-rigor PHASE 2 — H1 under the new inference regime, full n=27 panel.

Per market × window (repro 2026-04-17, extended 2026-06-30), from the frozen
snapshot:
  - real CausalForestDML + PurgedKFold fit (canonical spec; LinearDML dropped
    per plan — demonstrated boundary-churn at n=8);
  - PurgedKFold OOF overlap diagnostics;
  - rotation placebo battery: N=100 (repro) / N=50 (extended) per user
    decision — placebo-calibrated one-sided p per market;
  - frozen 3-tier verdict scheme (decisive-calibrated / leaning /
    indeterminate + quality flags), identical to the n=8 campaign.

Frozen reference: results_v2/n27_experiment/h1_dml_cpcv_n27.json.
Output: results_v2/oos_n27/phase2_h1_placebo.json
Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/oos_n27_phase2_h1.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from sklearn.ensemble import RandomForestClassifier

from validation.h1_direction.h1_dml import build_dml_dataset, PRIMARY_HORIZON
from validation.h1_direction.h1_dml_cpcv import (
    fit_causal_forest_dml_cpcv, PKF_N_SPLITS, PKF_EMBARGO,
)
from validation._cpcv_splitter import PurgedKFold
from validation.out_of_sample.oos_n27_common import (
    REPRO_END, OOS_END, OOS_DIR, pipeline_from_snapshot, market_seed,
)

N_ROT = {"repro": 100, "extended": 50}
FROZEN = os.path.join(_VALIDATION, "results_v2",
                      "n27_experiment", "h1_dml_cpcv_n27.json")
# Per-market checkpoints: a completed market is never recomputed, so the run
# survives interruption (e.g. hardware swap) at market granularity. Safe
# because each market uses its own crc32-derived rng — no cross-market state.
CKPT_DIR = os.path.join(OOS_DIR, "phase2_checkpoints")
os.makedirs(CKPT_DIR, exist_ok=True)


def overlap_diagnostics(df: pd.DataFrame, seed: int) -> dict:
    feature_cols = [c for c in df.columns if c not in ("fwd_vol", "T", "regime")]
    X, T = df[feature_cols].to_numpy(), df["T"].to_numpy()
    e_hat = np.full(len(df), np.nan)
    for tr, te in PurgedKFold(n_splits=PKF_N_SPLITS, embargo=PKF_EMBARGO).split(X):
        clf = RandomForestClassifier(n_estimators=200, max_depth=6,
                                     random_state=seed, n_jobs=-1)
        clf.fit(X[tr], T[tr])
        e_hat[te] = clf.predict_proba(X[te])[:, 1]
    e = e_hat[~np.isnan(e_hat)]
    return {"min": float(e.min()), "p05": float(np.percentile(e, 5)),
            "p95": float(np.percentile(e, 95)), "max": float(e.max()),
            "frac_outside_05_95": float(np.mean((e < 0.05) | (e > 0.95)))}


def verdict(real: dict, p1: float, fp_rate: float, ovl: float) -> dict:
    ci_excl = (real["ci_lo"] > 0) or (real["ci_hi"] < 0)
    if ci_excl and p1 <= 0.05:
        v = "DECISIVE_calibrated"
    elif ci_excl:
        v = "LEANING_model_based"
    else:
        v = "indeterminate"
    flags = []
    if ovl > 0.10:
        flags.append("ovl")
    if fp_rate > 0.15:
        flags.append("CI")
    return {"verdict": v, "flags": flags}


def main() -> int:
    with open(os.path.join(OOS_DIR, "phase0_manifest.json"), encoding="utf-8") as f:
        recs = [r for r in json.load(f)["records"] if r.get("gate_ok")]
    frozen = {}
    if os.path.exists(FROZEN):
        with open(FROZEN, encoding="utf-8") as f:
            frozen = json.load(f).get("results", {})

    print("=" * 74)
    print(f"  oos-n27-rigor PHASE 2 — CF-DML + rotation placebo "
          f"({len(recs)} markets; N_rot={N_ROT})")
    print("=" * 74)
    t0 = time.time()
    results: dict[str, dict] = {}

    for i, rec in enumerate(recs, 1):
        name, source = rec["market"], rec["source"]
        ckpt = os.path.join(CKPT_DIR, f"{name}.json")
        if os.path.exists(ckpt):
            with open(ckpt, encoding="utf-8") as f:
                results[name] = json.load(f)
            print(f"  [{i:>2}/27] {name:<9} RESUMED from checkpoint")
            continue
        seed = market_seed(name)
        results[name] = {"tier_rank": rec["tier_rank"], "category": rec["category"],
                         "frozen_cf": (frozen.get(name) or {}).get("causal_forest_dml"),
                         "windows": {}}
        for win, end in [("repro", REPRO_END), ("extended", OOS_END)]:
            t_w = time.time()
            try:
                out = pipeline_from_snapshot(name, end, source)
                df = build_dml_dataset(out["ohlcv"], out["filtered_labels"],
                                       horizon=PRIMARY_HORIZON)
            except Exception as e:
                results[name]["windows"][win] = {
                    "status": f"pipeline-failed: {type(e).__name__}: {str(e)[:120]}"}
                print(f"  [{i:>2}/27] {name:<9} {win:<8} PIPELINE FAIL")
                continue
            n_det, n_sto = int(df["T"].sum()), int((1 - df["T"]).sum())
            if n_det < 30 or n_sto < 30:
                results[name]["windows"][win] = {
                    "status": f"thin-arm: det={n_det} sto={n_sto}"}
                print(f"  [{i:>2}/27] {name:<9} {win:<8} THIN ARM det={n_det} sto={n_sto}")
                continue

            rng = np.random.default_rng(seed)
            real = fit_causal_forest_dml_cpcv(df, rng)
            ov = overlap_diagnostics(df, seed)

            filt = out["filtered_labels"]
            n = len(filt)
            placebo_ates, n_fp = [], 0
            for r in range(N_ROT[win]):
                off = int(rng.integers(252, n - 252))
                lab_rot = pd.Series(np.roll(filt.to_numpy(), off), index=filt.index)
                dfp = build_dml_dataset(out["ohlcv"], lab_rot, horizon=PRIMARY_HORIZON)
                if int(dfp["T"].sum()) < 30 or int((1 - dfp["T"]).sum()) < 30:
                    continue
                cf = fit_causal_forest_dml_cpcv(dfp, rng)
                if cf["fit_status"] != "ok":
                    continue
                placebo_ates.append(cf["ate"])
                if cf["direction_verdict"] in ("Paradox", "Inverted"):
                    n_fp += 1
            ates = np.array(placebo_ates)
            real_ate = real["ate"]
            if len(ates) >= 10 and np.isfinite(real_ate):
                p1 = ((np.sum(ates >= real_ate) + 1) / (len(ates) + 1) if real_ate > 0
                      else (np.sum(ates <= real_ate) + 1) / (len(ates) + 1))
                p2 = (np.sum(np.abs(ates) >= abs(real_ate)) + 1) / (len(ates) + 1)
                fp_rate = n_fp / len(ates)
            else:
                p1 = p2 = fp_rate = float("nan")

            vd = verdict(real, p1, fp_rate, ov["frac_outside_05_95"])
            results[name]["windows"][win] = {
                "status": "ok", "n_obs": int(len(df)),
                "n_det": n_det, "n_sto": n_sto,
                "cf": real, "overlap": ov,
                "placebo": {"n_ok": int(len(ates)), "fp_rate": fp_rate,
                            "ate_sd": float(ates.std()) if len(ates) else None,
                            "p_cal_1sided": float(p1), "p_cal_2sided": float(p2)},
                **vd,
            }
            print(f"  [{i:>2}/27] {name:<9} {win:<8} ATE={real_ate:+7.2f} "
                  f"[{real['ci_lo']:+7.2f},{real['ci_hi']:+7.2f}] p_cal={p1:.3f} "
                  f"FP={fp_rate:.0%} -> {vd['verdict']}{'/'.join([''] + vd['flags'])} "
                  f"({(time.time()-t_w)/60:.1f}m)")

        # checkpoint the completed market, then free cache memory
        with open(ckpt, "w", encoding="utf-8") as f:
            json.dump(results[name], f, indent=2, default=float)
        from validation.out_of_sample.oos_n27_common import _PIPE_CACHE
        for k in [k for k in _PIPE_CACHE if k[0] == name]:
            del _PIPE_CACHE[k]

    payload = {
        "spec": ("oos-n27-rigor phase 2: CF-DML + PurgedKFold real fits, OOF "
                 "overlap, rotation placebo (repro N=100 / extended N=50), "
                 "frozen 3-tier verdict scheme."),
        "n_rot": N_ROT, "results": results,
        "elapsed_seconds": float(time.time() - t0),
    }
    out_path = os.path.join(OOS_DIR, "phase2_h1_placebo.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\n  JSON: {out_path}   total {(time.time()-t0)/3600:.1f} h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
