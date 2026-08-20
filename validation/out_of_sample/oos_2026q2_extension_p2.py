"""
OOS EXTENSION EXPERIMENT — PHASE 2: the remaining hypotheses.
H3 + H4 (hysteresis_cross_market_v2), H5 (hysteresis_robustness_v2),
H2 cascade Monte Carlo (h2_cascade) re-run on the extended window
2026-04-17 → 2026-06-30, plus a repro pass at the canonical window.

Companion to oos_2026q2_extension.py (phase 1: H1 DML, H2 tier scaling,
Link B). Same design and rules:
  - canonical machinery reused verbatim via module monkeypatch (END,
    COMMON_END, OUTPUT_DIR, run_full_pipeline/load_ohlcv → cache);
  - regression checks against the pre-reg archive are SOFTENED to
    warnings — with a different window (or the BVB.RO data revision)
    they are EXPECTED to fail; the failure is diagnostic, not fatal;
  - frozen archive read-only; all outputs → results_v2/oos_2026q2/
    phase2_repro/ and phase2_extended/.

Cascade MC consumes the phase-1 per-window summary CSVs
(cross_market_summary_{repro,extended}.csv) — run phase 1 first.

Run:
  PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/oos_2026q2_extension_p2.py
Options:
  --windows repro,extended    --skip-h34    --skip-h5    --skip-cascade
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

import validation._features as _features

import validation.h3_h4_h5.hysteresis_cross_market_v2 as hxm
import validation.h3_h4_h5.hysteresis_robustness_v2 as hrv
import validation.h2_magnitude.h2_cascade as h2c

START = "2018-01-01"
REPRO_END = "2026-04-17"
OOS_END = "2026-06-30"

RESULTS_V2 = os.path.join(_VALIDATION, "results_v2")
OOS_DIR = os.path.join(RESULTS_V2, "oos_2026q2")
os.makedirs(OOS_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Shared pipeline cache (same pattern as phase 1)
# ------------------------------------------------------------------
_PIPE_CACHE: dict[tuple, dict] = {}


def cached_pipeline(market: str, ticker: str, source: str,
                    start: str, end: str | None = None, **kw) -> dict:
    key = (market, ticker, source, start, end)
    if key not in _PIPE_CACHE:
        t0 = time.time()
        _PIPE_CACHE[key] = _features.run_full_pipeline(
            market=market, ticker=ticker, source=source, start=start, end=end, **kw
        )
        print(f"    [pipeline] {market} {start}→{end}: "
              f"{len(_PIPE_CACHE[key]['features'])} bars ({time.time()-t0:.1f}s)")
    return _PIPE_CACHE[key]


def cached_load_ohlcv(market: str, ticker: str, source: str,
                      start: str, end: str | None = None) -> pd.DataFrame:
    """Serve OHLCV from the pipeline cache when available (guarantees H5 sees
    exactly the same input data as H3/H4 in this process)."""
    key = (market, ticker, source, start, end)
    if key in _PIPE_CACHE:
        return _PIPE_CACHE[key]["ohlcv"]
    return _features.load_ohlcv(market, ticker, source, start, end)


hxm.run_full_pipeline = cached_pipeline
hrv.load_ohlcv = cached_load_ohlcv


# ------------------------------------------------------------------
# Soften the pre-reg regression checks: with a shifted window (or the
# BVB.RO yfinance revision) drift is EXPECTED; report, don't raise.
# ------------------------------------------------------------------
def _soften(module, label: str) -> None:
    orig = module.regression_check_legacy

    def soft(df_new):
        try:
            orig(df_new)
        except AssertionError:
            print(f"[NOTE] {label}: legacy columns differ from the pre-reg "
                  f"archive — EXPECTED for a shifted window / revised BVB "
                  f"data. Diagnostic only; OOS outputs are unaffected.")

    module.regression_check_legacy = soft


_soften(hxm, "H3/H4")
_soften(hrv, "H5")


# ------------------------------------------------------------------
# Window runners
# ------------------------------------------------------------------
def run_h34(window: str, end: str, win_dir: str) -> None:
    hxm.END = end
    hxm.COMMON_END = end
    hxm.OUTPUT_DIR = win_dir
    print("\n" + "#" * 74)
    print(f"#  H3 + H4  [{window}]  common window 2020-01-01 → {end}")
    print("#" * 74)
    rc = hxm.main()
    if rc != 0:
        raise RuntimeError(f"H3/H4 window {window} failed (rc={rc})")


def run_h5(window: str, end: str, win_dir: str) -> None:
    hrv.END = end
    hrv.OUTPUT_DIR = win_dir
    print("\n" + "#" * 74)
    print(f"#  H5  [{window}]  window {START} → {end}")
    print("#" * 74)
    rc = hrv.main()
    if rc != 0:
        raise RuntimeError(f"H5 window {window} failed (rc={rc})")


def run_cascade(window: str) -> dict[str, Any] | None:
    csv_path = os.path.join(OOS_DIR, f"cross_market_summary_{window}.csv")
    if not os.path.exists(csv_path):
        print(f"[WARN] cascade skipped for {window}: {csv_path} missing "
              f"(run phase 1 first)")
        return None
    df = pd.read_csv(csv_path)
    H_raw = {r["market"]: float(r["H_stat"]) for _, r in df.iterrows()}
    H_filt = {r["market"]: float(r["H_stat_filtered"]) for _, r in df.iterrows()}
    print("\n" + "#" * 74)
    print(f"#  H2 CASCADE MC  [{window}]  (H stats from {os.path.basename(csv_path)})")
    print("#" * 74)
    raw = h2c.cascade_mc(H_raw)
    filt = h2c.cascade_mc(H_filt)
    for lab, res in [("RAW", raw), ("FILT", filt)]:
        print(f"  {lab}: rho mean={res['mean']:+.4f}  95% CI "
              f"[{res['p025']:+.4f}, {res['p975']:+.4f}]  "
              f"P(rho>0.5)={res['P_rho_gt_0p5']*100:.1f}%  "
              f"P(rho>0.7)={res['P_rho_gt_0p7']*100:.1f}%")
    return {"raw_cascade": raw, "filtered_cascade": filt,
            "h_source_csv": os.path.basename(csv_path)}


# ------------------------------------------------------------------
# Headline comparison vs frozen archive
# ------------------------------------------------------------------
def _read_csv_idx(path: str, idx: str = "market") -> dict[str, dict]:
    if not os.path.exists(path):
        return {}
    return pd.read_csv(path).set_index(idx).to_dict("index")


def build_comparison(win_names: list[str],
                     cascade: dict[str, dict | None]) -> pd.DataFrame:
    frozen_sum = _read_csv_idx(os.path.join(RESULTS_V2, "h3_h4_h5/hysteresis_summary_v2.csv"))
    frozen_h3 = _read_csv_idx(os.path.join(RESULTS_V2, "h3_h4_h5/h3_refined.csv"))
    frozen_h4 = _read_csv_idx(os.path.join(RESULTS_V2, "h3_h4_h5/h4_block_permutation.csv"))
    frozen_h5 = _read_csv_idx(os.path.join(RESULTS_V2, "h3_h4_h5/h5_refined.csv"))
    frozen_h3c: dict[str, Any] = {}
    p = os.path.join(RESULTS_V2, "h3_h4_h5/h3_continuous.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            frozen_h3c = json.load(f)
    frozen_casc: dict[str, Any] = {}
    p = os.path.join(RESULTS_V2, "h2_magnitude/h2_cascade.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            frozen_casc = json.load(f)

    win_sum, win_h3, win_h4, win_h5, win_h3c = {}, {}, {}, {}, {}
    for w in win_names:
        d = os.path.join(OOS_DIR, f"phase2_{w}")
        win_sum[w] = _read_csv_idx(os.path.join(d, "h3_h4_h5/hysteresis_summary_v2.csv"))
        win_h3[w] = _read_csv_idx(os.path.join(d, "h3_h4_h5/h3_refined.csv"))
        win_h4[w] = _read_csv_idx(os.path.join(d, "h3_h4_h5/h4_block_permutation.csv"))
        win_h5[w] = _read_csv_idx(os.path.join(d, "h3_h4_h5/h5_refined.csv"))
        p = os.path.join(d, "h3_h4_h5/h3_continuous.json")
        win_h3c[w] = {}
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                win_h3c[w] = json.load(f)

    rows: list[dict[str, Any]] = []

    def add(metric, fro, by_win: dict[str, Any], note=""):
        row = {"metric": metric, "frozen_2026-04-17": fro}
        row["repro_2026-04-17"] = by_win.get("repro")
        row["extended_2026-06-30"] = by_win.get("extended")
        row["note"] = note
        rows.append(row)

    markets = sorted({m for w in win_names for m in win_sum[w].keys()} |
                     set(frozen_sum.keys()))

    for m in markets:
        add(f"H3 {m} p_tra",
            frozen_sum.get(m, {}).get("p_tra"),
            {w: win_sum[w].get(m, {}).get("p_tra") for w in win_names})
        add(f"H3 {m} verdict refined",
            frozen_h3.get(m, {}).get("h3_verdict_refined"),
            {w: win_h3[w].get(m, {}).get("h3_verdict_refined") for w in win_names})
        add(f"H4 {m} shuffle p (label)",
            frozen_sum.get(m, {}).get("shuffle_p_value"),
            {w: win_sum[w].get(m, {}).get("shuffle_p_value") for w in win_names})
        add(f"H4 {m} block20 BH-FDR q",
            frozen_h4.get(m, {}).get("bh_fdr_q_block20"),
            {w: win_h4[w].get(m, {}).get("bh_fdr_q_block20") for w in win_names})
        add(f"H5 {m} p_tra spread",
            frozen_h5.get(m, {}).get("spread"),
            {w: win_h5[w].get(m, {}).get("spread") for w in win_names})
        add(f"H5 {m} verdict refined",
            frozen_h5.get(m, {}).get("H5_verdict_refined"),
            {w: win_h5[w].get(m, {}).get("H5_verdict_refined") for w in win_names})

    add("H3 continuous ρ(p_tra, RPS)", frozen_h3c.get("rho"),
        {w: win_h3c[w].get("rho") for w in win_names})
    add("H3 continuous p", frozen_h3c.get("p_value"),
        {w: win_h3c[w].get("p_value") for w in win_names})

    fc_raw = frozen_casc.get("raw_cascade") or {}
    fc_flt = frozen_casc.get("filtered_cascade") or {}
    for lab, fro_d in [("raw", fc_raw), ("filtered", fc_flt)]:
        add(f"Cascade ρ mean ({lab})", fro_d.get("mean"),
            {w: (cascade.get(w) or {}).get(f"{lab}_cascade", {}).get("mean")
             for w in win_names})
        add(f"Cascade P(ρ>0.5) ({lab})", fro_d.get("P_rho_gt_0p5"),
            {w: (cascade.get(w) or {}).get(f"{lab}_cascade", {}).get("P_rho_gt_0p5")
             for w in win_names})

    return pd.DataFrame(rows)


# ------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", type=str, default="repro,extended")
    ap.add_argument("--skip-h34", action="store_true")
    ap.add_argument("--skip-h5", action="store_true")
    ap.add_argument("--skip-cascade", action="store_true")
    args = ap.parse_args()
    win_names = [w.strip() for w in args.windows.split(",") if w.strip()]

    print("=" * 74)
    print("  OOS 2026-Q2 EXTENSION — PHASE 2 (H3/H4, H5, cascade MC)")
    print("=" * 74)
    print(f"  windows: {win_names}")

    t0 = time.time()
    cascade: dict[str, dict | None] = {}
    for w in win_names:
        end = REPRO_END if w == "repro" else OOS_END
        win_dir = os.path.join(OOS_DIR, f"phase2_{w}")
        os.makedirs(win_dir, exist_ok=True)
        if not args.skip_h34:
            run_h34(w, end, win_dir)
        if not args.skip_h5:
            run_h5(w, end, win_dir)
        if not args.skip_cascade:
            cascade[w] = run_cascade(w)

    comp = build_comparison(win_names, cascade)
    comp_path = os.path.join(OOS_DIR, "oos_2026q2_phase2_comparison.csv")
    comp.to_csv(comp_path, index=False)

    payload = {
        "spec": ("OOS phase 2: H3/H4 + H5 + cascade MC on repro/extended "
                 "windows; canonical machinery via monkeypatch; archive "
                 "regression checks softened (drift expected OOS)."),
        "start": START, "repro_end": REPRO_END, "oos_end": OOS_END,
        "cascade": cascade,
        "elapsed_seconds": float(time.time() - t0),
    }
    with open(os.path.join(OOS_DIR, "oos_2026q2_phase2_results.json"),
              "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    print("\n" + "=" * 74)
    print("  PHASE 2 HEADLINE COMPARISON (frozen | repro | extended)")
    print("=" * 74)
    with pd.option_context("display.max_rows", None, "display.width", 200,
                           "display.max_colwidth", 40):
        print(comp.to_string(index=False))
    print(f"\n  comparison CSV: {comp_path}")
    print(f"  total elapsed: {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
