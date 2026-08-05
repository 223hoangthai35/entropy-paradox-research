"""
RIGOR UPGRADE — STEP A: H1 placebo battery + overlap diagnostics
(exploratory, NOT pre-registered; canonical window 2018-01-01 → 2026-04-17).

A1. ROTATION PLACEBO (placebo treatment). The H1 claim is that the regime
label at t carries information about forward 20d vol. Null instrument:
circularly ROTATE the filtered label series by a random offset in
[252, n-252]. Rotation preserves the label marginal distribution AND its
full autocorrelation/run-length structure — it only destroys the alignment
with outcomes. Refit CausalForestDML+PurgedKFold on each rotated series.

Expected under a clean pipeline:
  - placebo ATEs scatter around 0;
  - the share of placebo CIs excluding 0 ~ the nominal 5% (small-N caveat);
  - the REAL |ATE| for decisive markets (SPX, BTC) sits in the tail of the
    placebo |ATE| distribution.
Red flag: placebo verdicts fire frequently -> leakage through controls/CV.

A2. OVERLAP / POSITIVITY. Out-of-fold propensity e(X) = P(T=Det | X) via the
same RF spec + PurgedKFold as the DML. Report min / p05 / median / p95 / max
and the share of observations outside [0.05, 0.95] common support. Makes the
"BVB/VNINDEX power floor" story quantitative.

Real reference ATEs are NOT refit — they are read from the phase-1 OOS run
(results_v2/oos_2026q2/oos_2026q2_results.json, repro window).

Outputs: validation/results_v2/oos_2026q2/rigor_h1_placebo.json
Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/rigor_h1_placebo.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import zlib

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sklearn.ensemble import RandomForestClassifier

from validation._features import run_full_pipeline
from validation.h1_dml import MARKETS, START, PRIMARY_HORIZON, build_dml_dataset
from validation.h1_dml_cpcv import (
    fit_causal_forest_dml_cpcv, PKF_N_SPLITS, PKF_EMBARGO,
)
from validation._cpcv_splitter import PurgedKFold

END = "2026-06-30"           # canonical paper window — the claim under test
RNG_SEED = 42
# Rotation counts are overridable via env vars (CF fits are ~3s each, so a
# properly-powered placebo-calibrated p is cheap).
N_ROT_FOCUS = int(os.environ.get("PLACEBO_ROT_FOCUS", "8"))
N_ROT_OTHER = int(os.environ.get("PLACEBO_ROT_OTHER", "3"))
OUT_SUFFIX = os.environ.get("PLACEBO_OUT_SUFFIX", "")
FOCUS = set(os.environ.get("PLACEBO_FOCUS_MARKETS", "SPX,BTC,BVB").split(","))

OOS_DIR = os.path.join(os.path.dirname(__file__), "results_v2", "oos_2026q2")
os.makedirs(OOS_DIR, exist_ok=True)
REAL_JSON = os.path.join(OOS_DIR, "oos_2026q2_results.json")


def _seed(name: str) -> int:
    return RNG_SEED + zlib.crc32(name.encode()) % 1000


def load_real_reference() -> dict[str, dict]:
    if not os.path.exists(REAL_JSON):
        print(f"[WARN] {REAL_JSON} missing — real reference ATEs unavailable")
        return {}
    with open(REAL_JSON, encoding="utf-8") as f:
        d = json.load(f)
    out = {}
    for m, entry in d["windows"]["repro"]["per_market"].items():
        cf = (entry.get("dml") or {}).get("causal_forest_dml") or {}
        if cf.get("fit_status") == "ok":
            out[m] = {"ate": cf["ate"], "ci_lo": cf["ci_lo"],
                      "ci_hi": cf["ci_hi"], "verdict": cf["direction_verdict"]}
    return out


def overlap_diagnostics(df: pd.DataFrame, seed: int) -> dict:
    """Out-of-fold propensity via the DML's own RF spec + PurgedKFold."""
    feature_cols = [c for c in df.columns if c not in ("fwd_vol", "T", "regime")]
    X = df[feature_cols].to_numpy()
    T = df["T"].to_numpy()
    e_hat = np.full(len(df), np.nan)
    pkf = PurgedKFold(n_splits=PKF_N_SPLITS, embargo=PKF_EMBARGO)
    for tr, te in pkf.split(X):
        clf = RandomForestClassifier(n_estimators=200, max_depth=6,
                                     random_state=seed, n_jobs=-1)
        clf.fit(X[tr], T[tr])
        e_hat[te] = clf.predict_proba(X[te])[:, 1]
    e = e_hat[~np.isnan(e_hat)]
    return {
        "n": int(len(e)),
        "min": float(e.min()), "p05": float(np.percentile(e, 5)),
        "median": float(np.median(e)),
        "p95": float(np.percentile(e, 95)), "max": float(e.max()),
        "frac_outside_05_95": float(np.mean((e < 0.05) | (e > 0.95))),
    }


def main() -> int:
    t0 = time.time()
    real = load_real_reference()
    results: dict = {"spec": ("H1 rotation-placebo battery + PurgedKFold OOF "
                              "overlap diagnostics on the canonical window. "
                              "Rotation preserves label marginals + run "
                              "structure; only alignment is destroyed."),
                     "window": [START, END],
                     "n_rot": {"focus": N_ROT_FOCUS, "other": N_ROT_OTHER,
                               "focus_markets": sorted(FOCUS)},
                     "per_market": {}}

    for cfg in MARKETS:
        name = cfg["name"]
        n_rot = N_ROT_FOCUS if name in FOCUS else N_ROT_OTHER
        print(f"\n[{name}] pipeline + {n_rot} rotation placebos ...")
        try:
            out = run_full_pipeline(market=name, ticker=cfg["ticker"],
                                    source=cfg["source"], start=START, end=END)
        except Exception as e:
            print(f"  [SKIP] pipeline failed: {type(e).__name__}: {e}")
            continue

        filt = out["filtered_labels"]
        n = len(filt)
        rng = np.random.default_rng(_seed(name))

        # Real dataset once — for overlap diagnostics
        df_real = build_dml_dataset(out["ohlcv"], filt, horizon=PRIMARY_HORIZON)
        if int(df_real["T"].sum()) < 30 or int((1 - df_real["T"]).sum()) < 30:
            print("  [SKIP] insufficient Det/Sto obs")
            continue
        ov = overlap_diagnostics(df_real, seed=_seed(name))
        print(f"  overlap: e(X) [{ov['min']:.3f} … {ov['max']:.3f}]  "
              f"p05={ov['p05']:.3f} p95={ov['p95']:.3f}  "
              f"outside[.05,.95]={ov['frac_outside_05_95']*100:.1f}%")

        placebos = []
        for r in range(n_rot):
            off = int(rng.integers(252, n - 252))
            lab_rot = pd.Series(np.roll(filt.to_numpy(), off), index=filt.index)
            df_p = build_dml_dataset(out["ohlcv"], lab_rot, horizon=PRIMARY_HORIZON)
            if int(df_p["T"].sum()) < 30 or int((1 - df_p["T"]).sum()) < 30:
                placebos.append({"offset": off, "fit_status": "skip: thin arm"})
                continue
            t_f = time.time()
            cf = fit_causal_forest_dml_cpcv(df_p, rng)
            cf["offset"] = off
            cf["elapsed"] = round(time.time() - t_f, 1)
            placebos.append(cf)
            if cf["fit_status"] == "ok":
                print(f"    rot {r+1}/{n_rot} off={off:>5}  ATE={cf['ate']:+7.3f} "
                      f"[{cf['ci_lo']:+7.2f},{cf['ci_hi']:+7.2f}] {cf['direction_verdict']:<8} "
                      f"({cf['elapsed']:.0f}s)")
            else:
                print(f"    rot {r+1}/{n_rot} off={off:>5}  {cf['fit_status'][:60]}")

        ok = [p for p in placebos if p.get("fit_status") == "ok"]
        ates = np.array([p["ate"] for p in ok]) if ok else np.array([])
        fp = [p for p in ok if p["direction_verdict"] in ("Paradox", "Inverted")]
        summary = {
            "n_ok": len(ok),
            "placebo_ate_mean": float(ates.mean()) if len(ates) else None,
            "placebo_abs_ate_max": float(np.abs(ates).max()) if len(ates) else None,
            "n_ci_excludes_0": len(fp),
            "false_positive_rate": (len(fp) / len(ok)) if ok else None,
        }
        r_ref = real.get(name)
        if r_ref and len(ates):
            summary["real_ate"] = r_ref["ate"]
            summary["real_abs_gt_all_placebos"] = bool(
                abs(r_ref["ate"]) > np.abs(ates).max())
        results["per_market"][name] = {
            "real_reference": r_ref, "overlap": ov,
            "placebos": placebos, "summary": summary,
        }
        fp_str = f"{len(fp)}/{len(ok)}"
        print(f"  summary: placebo mean ATE={summary['placebo_ate_mean']:+.3f}  "
              f"CI-excl-0: {fp_str}  real |ATE| > all placebos: "
              f"{summary.get('real_abs_gt_all_placebos', 'n/a')}")

    out_path = os.path.join(OOS_DIR, f"rigor_h1_placebo{OUT_SUFFIX}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=float)

    # Panel-level placebo false-positive rate
    all_ok = [p for m in results["per_market"].values() for p in m["placebos"]
              if p.get("fit_status") == "ok"]
    all_fp = [p for p in all_ok if p["direction_verdict"] in ("Paradox", "Inverted")]
    print("\n" + "=" * 74)
    print(f"  PANEL PLACEBO SUMMARY: {len(all_fp)}/{len(all_ok)} placebo fits "
          f"produced a decisive verdict (nominal expectation ≈ 5%)")
    print("=" * 74)
    print(f"JSON: {out_path}")
    print(f"total elapsed: {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
