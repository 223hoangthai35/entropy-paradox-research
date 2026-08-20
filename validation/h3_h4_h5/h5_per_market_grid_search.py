"""
H5 per-market hysteresis grid search + retest.

For each market, finds the (delta_hard, delta_soft, t_persist) triplet that
produces filtered flip rate closest to 7.0/yr (centre of the 4-10/yr target
band). Then perturbs each market's own optimum by ±0.10 / ±0.05 / ±2 to form
B_looser and C_tighter configs and reports the p(Tra) spread on those three
own-centred configs.

This complements the production hysteresis_robustness_v2.py (which fixes
shared configs A=0.60/0.35/8, B=0.50/0.30/6, C=0.70/0.40/10 from VNINDEX
calibration) by removing the calibration bias for markets with different
underlying flip-rate distributions.

Output: validation/results_v2/h5_per_market_grid_search.json,
        validation/results_v2/h5_per_market_grid_search.csv

Run: python validation/h5_per_market_grid_search.py
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

from skills.ds_skill import EntropyPhaseSpaceClassifier, HysteresisGMMWrapper
from validation._features import load_ohlcv, build_plane1_features, flip_rate_per_year
from validation.h2_magnitude.cross_market_v2 import MARKETS, START, END

OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2")
COMMON_START = "2020-01-01"
TARGET_FLIPS_YR = 7.0
RNG_SEED = 42

DH_GRID = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
DS_GRID = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
TP_GRID = [3, 5, 8, 10, 13, 15]


def _filtered_p_tra_and_flips(gmm: EntropyPhaseSpaceClassifier,
                               feat: pd.DataFrame, dh: float, ds: float,
                               tp: int) -> tuple[float, float]:
    wrapper = HysteresisGMMWrapper(gmm, delta_hard=dh, delta_soft=ds, t_persist=tp)
    filt = wrapper.transform(feat.values)
    filt = pd.Series(filt, index=feat.index)
    filt.index = pd.to_datetime(filt.index)
    filt_common = filt.loc[filt.index >= COMMON_START]
    bpy = 365 if "BTC" in feat.attrs.get("market", "") else 252
    return float((filt_common == 1).mean()), float(flip_rate_per_year(filt_common.values, bpy))


def find_optimum(gmm: EntropyPhaseSpaceClassifier, feat: pd.DataFrame,
                  bpy: int) -> dict[str, Any]:
    """Grid-search for (dh, ds, tp) closest to TARGET_FLIPS_YR; return optimum + grid."""
    best = None
    full_grid = []
    for dh in DH_GRID:
        for ds in DS_GRID:
            if ds >= dh:
                continue
            for tp in TP_GRID:
                wrapper = HysteresisGMMWrapper(gmm, delta_hard=dh, delta_soft=ds, t_persist=tp)
                filt = pd.Series(wrapper.transform(feat.values), index=feat.index)
                filt.index = pd.to_datetime(filt.index)
                filt_common = filt.loc[filt.index >= COMMON_START]
                fpy = float(flip_rate_per_year(filt_common))
                p_tra = float((filt_common == 1).mean())
                in_band = 4.0 <= fpy <= 10.0
                full_grid.append({"dh": dh, "ds": ds, "tp": tp, "fpy": fpy, "p_tra": p_tra, "in_band": in_band})
                d = abs(fpy - TARGET_FLIPS_YR)
                if best is None or d < best["d"]:
                    best = {"dh": dh, "ds": ds, "tp": tp, "fpy": fpy, "p_tra": p_tra, "d": d}
    in_band_count = sum(1 for g in full_grid if g["in_band"])
    return {
        "optimum": {"dh": best["dh"], "ds": best["ds"], "tp": best["tp"], "fpy": best["fpy"], "p_tra": best["p_tra"]},
        "n_grid": len(full_grid),
        "n_in_band": in_band_count,
        "full_grid": full_grid,
    }


def _round_to_grid(val: float, grid: list[float], delta: float, sign: int) -> float:
    target = val + sign * delta
    return min(grid, key=lambda x: abs(x - target))


def perturb_around(opt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    dh, ds, tp = opt["dh"], opt["ds"], opt["tp"]
    looser_dh = _round_to_grid(dh, DH_GRID, 0.10, -1)
    looser_ds = _round_to_grid(ds, DS_GRID, 0.05, -1)
    looser_tp = max(TP_GRID[0], tp - 2)
    tighter_dh = _round_to_grid(dh, DH_GRID, 0.10, +1)
    tighter_ds = _round_to_grid(ds, DS_GRID, 0.05, +1)
    tighter_tp = min(TP_GRID[-1], tp + 2)
    if looser_ds >= looser_dh:
        looser_ds = max([d for d in DS_GRID if d < looser_dh], default=DS_GRID[0])
    if tighter_ds >= tighter_dh:
        tighter_ds = max([d for d in DS_GRID if d < tighter_dh], default=DS_GRID[0])
    return {
        "B_looser":  {"dh": looser_dh,  "ds": looser_ds,  "tp": looser_tp},
        "A_optimum": {"dh": dh,         "ds": ds,         "tp": tp},
        "C_tighter": {"dh": tighter_dh, "ds": tighter_ds, "tp": tighter_tp},
    }


def main() -> int:
    print("=" * 90)
    print("  H5 PER-MARKET HYSTERESIS GRID SEARCH + RETEST")
    print(f"  Target band: 4-10 flips/yr  (centre {TARGET_FLIPS_YR})")
    print("=" * 90)

    rows = []
    payload: dict[str, Any] = {
        "spec": "H5 per-market hysteresis grid search + own-optimum retest",
        "target_flips_yr": TARGET_FLIPS_YR,
        "common_start": COMMON_START,
        "seed": RNG_SEED,
        "per_market": {},
    }

    for cfg in MARKETS:
        name = cfg["name"]
        print(f"\n[{name}] fitting GMM, running grid search ...")
        df = load_ohlcv(market=name, ticker=cfg["ticker"], source=cfg["source"], start=START, end=END)
        feat = build_plane1_features(df)
        feat.attrs["market"] = name
        bpy = 365 if name == "BTC" else 252
        gmm = EntropyPhaseSpaceClassifier(random_state=RNG_SEED)
        gmm.fit(feat.values)
        n_bars = len(feat)
        print(f"  GMM fitted on {n_bars} bars")

        grid_out = find_optimum(gmm, feat, bpy)
        opt = grid_out["optimum"]
        configs = perturb_around(opt)
        config_results = {}
        ptra_vals = []
        for label, c in configs.items():
            wrapper = HysteresisGMMWrapper(gmm, delta_hard=c["dh"], delta_soft=c["ds"], t_persist=c["tp"])
            filt = pd.Series(wrapper.transform(feat.values), index=feat.index)
            filt.index = pd.to_datetime(filt.index)
            filt_common = filt.loc[filt.index >= COMMON_START]
            p_tra = float((filt_common == 1).mean())
            fpy = float(flip_rate_per_year(filt_common))
            config_results[label] = {**c, "p_tra": p_tra, "fpy": fpy}
            ptra_vals.append(p_tra)
            print(f"  {label}: dh={c['dh']:.2f} ds={c['ds']:.2f} tp={c['tp']} -> {fpy:.2f} flips/yr  p_tra={p_tra:.3f}")
        spread = max(ptra_vals) - min(ptra_vals)
        verdict = "PASS" if spread < 0.05 else "REJECT"
        print(f"  p(Tra) spread = {spread:.3f}  H5={verdict}")

        payload["per_market"][name] = {
            "category": cfg["category"],
            "optimum": opt,
            "n_grid": grid_out["n_grid"],
            "n_in_band": grid_out["n_in_band"],
            "configs": config_results,
            "p_tra_spread": spread,
            "h5_verdict": verdict,
        }
        rows.append({
            "market": name,
            "category": cfg["category"],
            "opt_dh": opt["dh"],
            "opt_ds": opt["ds"],
            "opt_tp": opt["tp"],
            "opt_fpy": opt["fpy"],
            "p_tra_spread": spread,
            "h5_verdict": verdict,
        })

    df = pd.DataFrame(rows)
    csv_path = os.path.join(OUTPUT_DIR, "h3_h4_h5/h5_per_market_grid_search.csv")
    json_path = os.path.join(OUTPUT_DIR, "h3_h4_h5/h5_per_market_grid_search.json")
    df.to_csv(csv_path, index=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\nCSV : {csv_path}")
    print(f"JSON: {json_path}")
    print("\n" + "=" * 90)
    print("  H5 PER-MARKET RETEST SUMMARY")
    print("=" * 90)
    print(df.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
