"""
FROZEN EVALUATION SCRIPT for the forward direction test registered in
pre_registration/forward_direction_test_2026H2.md (registration 2026-07-10).

Evaluates P1 (SPX ATE > 0), P2 (BTC ATE < 0), P3 (SHANGHAI ATE > 0) on the
full extended sample 2018-01-01 -> 2027-06-30, per the frozen specification:
canonical pipeline invariants + CausalForestDML + PurgedKFold on filtered
labels; fresh data snapshot with SHA256 at evaluation time; crc32 seeds.
Optional --placebo adds the rotation-placebo calibrated p (N=100), the
"strongest" grade of the registration.

The REGISTERED evaluation is the first run on or after 2027-07-01. Earlier
runs are labeled INTERIM and are not the registered outcome.

Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/forward_test_2026H2_eval.py [--placebo]
Output: validation/results_v2/forward_2026H2/forward_test_results.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import zlib

from validation._features import load_ohlcv, build_plane1_features, fit_classifier_and_filter
from validation.h1_dml import build_dml_dataset, PRIMARY_HORIZON
from validation.h1_dml_cpcv import fit_causal_forest_dml_cpcv

START = "2018-01-01"
EVAL_END = "2027-06-30"          # inclusive; fetch buffer handles yfinance exclusivity
FETCH_END = "2027-07-05"
WINDOW_START = "2026-07-13"      # registered post-registration slice (descriptive)
REGISTERED_FROM = _dt.date(2027, 7, 1)
RNG_SEED = 42
N_ROT = 100

PREDICTIONS = [
    {"id": "P1", "market": "SPX",      "ticker": "^GSPC",     "sign": +1},
    {"id": "P2", "market": "BTC",      "ticker": "BTC-USD",   "sign": -1},
    {"id": "P3", "market": "SHANGHAI", "ticker": "000001.SS", "sign": +1},
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2", "forward_2026H2")
SNAP_DIR = os.path.join(OUT_DIR, "data_snapshot")
os.makedirs(SNAP_DIR, exist_ok=True)


def _seed(name: str) -> int:
    return RNG_SEED + zlib.crc32(name.encode()) % 1000


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def evaluate(pred: dict, run_placebo: bool) -> dict:
    name = pred["market"]
    df = load_ohlcv(name, pred["ticker"], "yfinance", START, FETCH_END)
    df = df[df.index <= pd.Timestamp(EVAL_END)]
    snap = os.path.join(SNAP_DIR, f"{name}.csv")
    df.to_csv(snap)

    feat = build_plane1_features(df)
    out = fit_classifier_and_filter(feat, hysteresis_kwargs=None, random_state=RNG_SEED)
    filt = out["filtered_labels"]

    dml_df = build_dml_dataset(df, filt, horizon=PRIMARY_HORIZON)
    rng = np.random.default_rng(_seed(name))
    cf = fit_causal_forest_dml_cpcv(dml_df, rng)

    ate, lo, hi = cf["ate"], cf["ci_lo"], cf["ci_hi"]
    sign_ok = bool(np.sign(ate) == pred["sign"]) if np.isfinite(ate) else None
    ci_ok = bool(lo > 0) if pred["sign"] > 0 else bool(hi < 0)

    res = {
        "prediction": pred["id"], "market": name,
        "predicted_sign": pred["sign"],
        "n_bars": int(len(feat)), "last_bar": str(df.index[-1].date()),
        "snapshot_sha256": _sha256(snap),
        "ate": ate, "ci_lo": lo, "ci_hi": hi, "fit_status": cf["fit_status"],
        "grade_primary_sign": sign_ok,
        "grade_strong_ci": bool(sign_ok and ci_ok),
    }

    if run_placebo and cf["fit_status"] == "ok":
        ates = []
        n = len(filt)
        for _ in range(N_ROT):
            off = int(rng.integers(252, n - 252))
            rot = pd.Series(np.roll(filt.to_numpy(), off), index=filt.index)
            dfp = build_dml_dataset(df, rot, horizon=PRIMARY_HORIZON)
            if int(dfp["T"].sum()) < 30 or int((1 - dfp["T"]).sum()) < 30:
                continue
            p = fit_causal_forest_dml_cpcv(dfp, rng)
            if p["fit_status"] == "ok":
                ates.append(p["ate"])
        a = np.array(ates)
        if len(a) >= 10:
            p1 = ((np.sum(a >= ate) + 1) / (len(a) + 1) if ate > 0
                  else (np.sum(a <= ate) + 1) / (len(a) + 1))
            res["p_cal_1sided"] = float(p1)
            res["grade_strongest"] = bool(res["grade_strong_ci"] and p1 <= 0.10)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--placebo", action="store_true")
    args = ap.parse_args()

    today = _dt.date.today()
    registered = today >= REGISTERED_FROM
    banner = "REGISTERED EVALUATION" if registered else "INTERIM RUN — NOT the registered outcome"
    print("=" * 74)
    print(f"  FORWARD DIRECTION TEST 2026H2 — {banner} ({today})")
    print(f"  registration: pre_registration/forward_direction_test_2026H2.md")
    print("=" * 74)

    results = []
    for pred in PREDICTIONS:
        print(f"\n[{pred['id']}] {pred['market']} — predicted sign {'+' if pred['sign']>0 else '−'}")
        try:
            r = evaluate(pred, args.placebo)
        except Exception as e:
            r = {"prediction": pred["id"], "market": pred["market"],
                 "error": f"{type(e).__name__}: {str(e)[:200]}"}
            print(f"  ERROR: {r['error']}")
            results.append(r)
            continue
        print(f"  ATE={r['ate']:+.3f} [{r['ci_lo']:+.2f}, {r['ci_hi']:+.2f}]  "
              f"last bar {r['last_bar']}")
        print(f"  primary (sign): {'PASS' if r['grade_primary_sign'] else 'FAIL'}   "
              f"strong (CI): {'PASS' if r['grade_strong_ci'] else 'no'}"
              + (f"   strongest (p_cal={r.get('p_cal_1sided'):.3f}): "
                 f"{'PASS' if r.get('grade_strongest') else 'no'}" if "p_cal_1sided" in r else ""))
        results.append(r)

    payload = {
        "spec": "Forward test 2026H2 evaluation (P1-P3). S1-S2 via oos_n27 scripts "
                "with OOS_END=2027-06-30 (see registration §3).",
        "run_type": "registered" if registered else "interim",
        "run_date": str(today),
        "window": [START, EVAL_END], "post_registration_slice_from": WINDOW_START,
        "results": results,
    }
    out = os.path.join(OUT_DIR, "forward_test_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\n  JSON: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
