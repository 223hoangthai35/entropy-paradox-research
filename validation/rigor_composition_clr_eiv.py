"""
RIGOR UPGRADE — STEP B: composition tests done right (exploratory, NOT pre-registered).

Two fixes applied to the Link-B / H3-continuous composition correlations
(rho(p_sto, RPS), rho(p_tra, RPS)) that the OOS exercise showed to be fragile:

  1. CoDA: (p_det, p_tra, p_sto) lives on the simplex (sums to 1). Correlating
     a raw share ignores that constraint. We apply the centered log-ratio
     transform (Aitchison 1986): clr_i = ln(p_i / g(p)), g = geometric mean.
  2. EIV: within-market sampling uncertainty of the shares enters via a
     circular block bootstrap (2000 draws, block=20) of the label series;
     RPS enters via the cascade P1/P2/P3 measurement prior; conclusion is
     the MC distribution of a precision-weighted WLS slope: P(beta<0) for
     clr(p_sto) (mechanism sign), P(beta>0) for clr(p_tra).

Also computed here (STEP B2): the label-stability diagnostic — agreement and
adjusted Rand index (ARI) between the repro-window and extended-window label
series on their common index, per market, raw + filtered. This quantifies the
FTSE-style GMM refit instability as a routine reported number.

Old-method reference (for the "new vs old" comparison): plain Spearman of the
point shares vs point RPS with the 10k permutation p, exactly as the
manuscript B.5.3 headline was computed.

Outputs: validation/results_v2/oos_2026q2/rigor_composition_clr_eiv.json
Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/rigor_composition_clr_eiv.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import zlib

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import run_full_pipeline
from validation.cross_market_v2 import MARKETS, _circular_block_indices
from validation.link_b_tests import RPS, permutation_spearman_ci
from validation.h2_cascade import sample_rps_cascade
from validation.oos_2026q2_h2_alt_estimators import wls_slope

START = "2018-01-01"
WINDOWS = {"repro": "2026-04-17", "extended": "2026-06-30"}

BLOCK = 20
N_BOOT = 2000
N_MC = 10_000
SHARE_FLOOR = 1e-3       # clr needs strictly positive parts
RNG_SEED = 42

OOS_DIR = os.path.join(os.path.dirname(__file__), "results_v2", "oos_2026q2")
os.makedirs(OOS_DIR, exist_ok=True)


def _seed(name: str) -> int:
    """Stable per-market seed (independent of PYTHONHASHSEED)."""
    return RNG_SEED + zlib.crc32(name.encode()) % 1000


def clr(p: np.ndarray) -> np.ndarray:
    """Centered log-ratio on the 3-part composition, floored + renormalized."""
    q = np.maximum(p, SHARE_FLOOR)
    q = q / q.sum()
    g = np.exp(np.mean(np.log(q)))
    return np.log(q / g)


def shares_point_and_boot(labels: pd.Series, seed: int) -> dict:
    arr = labels.astype(int).to_numpy()
    n = len(arr)
    point = np.array([(arr == k).mean() for k in (0, 1, 2)])
    rng = np.random.default_rng(seed)
    idx = _circular_block_indices(n, BLOCK, N_BOOT, rng)          # (N_BOOT, n)
    boot = np.stack([(arr[idx] == k).mean(axis=1) for k in (0, 1, 2)], axis=1)
    clr_point = clr(point)
    clr_boot = np.apply_along_axis(clr, 1, boot)                  # (N_BOOT, 3)
    return {"p_point": point, "clr_point": clr_point, "clr_boot": clr_boot}


def eiv_mc(y_boot: dict[str, np.ndarray], y_point: dict[str, float],
           sign: str, seed: int = RNG_SEED) -> dict:
    """MC over (cascade RPS draw, bootstrap y draw); precision-weighted WLS."""
    names = list(y_boot.keys())
    var = np.array([np.var(y_boot[m]) for m in names])
    w = 1.0 / np.maximum(var, 1e-6)
    w = w / w.sum()
    rng = np.random.default_rng(seed)
    betas = np.empty(N_MC)
    for i in range(N_MC):
        x = np.array([sample_rps_cascade(m, rng) for m in names])
        y = np.array([y_boot[m][rng.integers(len(y_boot[m]))] for m in names])
        betas[i] = wls_slope(x, y, w)
    p_dir = float(np.mean(betas < 0)) if sign == "neg" else float(np.mean(betas > 0))
    return {"beta_mean": float(betas.mean()), "beta_sd": float(betas.std(ddof=1)),
            "ci_lo": float(np.percentile(betas, 2.5)),
            "ci_hi": float(np.percentile(betas, 97.5)),
            "P_correct_sign": p_dir, "sign_expected": sign,
            "weights": {m: float(wi) for m, wi in zip(names, w)}}


def main() -> int:
    t0 = time.time()
    res: dict = {"spec": ("Composition tests with CoDA clr transform + EIV "
                          "(bootstrap y, cascade RPS prior, weighted WLS); "
                          "plus label-stability ARI. Exploratory."),
                 "share_floor": SHARE_FLOOR, "n_boot": N_BOOT, "n_mc": N_MC,
                 "windows": {}, "label_stability": {}}

    piped: dict[tuple, dict] = {}
    for win, end in WINDOWS.items():
        print("=" * 74)
        print(f"  WINDOW [{win}]  {START} → {end}")
        print("=" * 74)
        stats: dict[str, dict] = {}
        for cfg in MARKETS:
            name = cfg["name"]
            out = run_full_pipeline(market=name, ticker=cfg["ticker"],
                                    source=cfg["source"], start=START, end=end)
            piped[(name, win)] = out
            s = shares_point_and_boot(out["filtered_labels"], _seed(name))
            stats[name] = s
            print(f"  {name:<8} p=(det {s['p_point'][0]:.3f}, tra {s['p_point'][1]:.3f}, "
                  f"sto {s['p_point'][2]:.3f})  clr_sto={s['clr_point'][2]:+.3f}")

        names = list(stats.keys())
        rps_arr = np.array([RPS[m] for m in names])
        win_res: dict = {"end": end, "per_market": {
            m: {"p_point": stats[m]["p_point"].tolist(),
                "clr_point": stats[m]["clr_point"].tolist()} for m in names}}

        # --- OLD method (manuscript B.5.3 style): Spearman of raw shares ---
        for comp_i, comp, sign in [(2, "p_sto", "neg"), (1, "p_tra", "pos")]:
            x = np.array([stats[m]["p_point"][comp_i] for m in names])
            rho, p_perm, _, _ = permutation_spearman_ci(x, rps_arr)
            win_res[f"old_spearman_{comp}"] = {"rho": rho, "p_perm_2sided": p_perm}
            print(f"  OLD  ρ({comp}, RPS) = {rho:+.3f}  p_perm = {p_perm:.4f}")

        # --- NEW method: clr + EIV ---
        for comp_i, comp, sign in [(2, "clr_sto", "neg"), (1, "clr_tra", "pos")]:
            y_boot = {m: stats[m]["clr_boot"][:, comp_i] for m in names}
            y_pt = {m: stats[m]["clr_point"][comp_i] for m in names}
            mc = eiv_mc(y_boot, y_pt, sign)
            win_res[f"new_eiv_{comp}"] = mc
            print(f"  NEW  {comp}: β = {mc['beta_mean']:+.3f} "
                  f"[{mc['ci_lo']:+.3f}, {mc['ci_hi']:+.3f}]  "
                  f"P(sign {sign}) = {mc['P_correct_sign']*100:.1f}%")
            # plain Spearman on point clr, for the middle rung of the ladder
            x = np.array([y_pt[m] for m in names])
            rho, p_perm, _, _ = permutation_spearman_ci(x, rps_arr)
            win_res[f"mid_spearman_{comp}"] = {"rho": rho, "p_perm_2sided": p_perm}

        res["windows"][win] = win_res

    # --- STEP B2: label-stability diagnostic (repro vs extended) ---
    print("\n" + "=" * 74)
    print("  LABEL STABILITY (repro vs extended, common index)")
    print("=" * 74)
    for cfg in MARKETS:
        name = cfg["name"]
        a, b = piped[(name, "repro")], piped[(name, "extended")]
        d: dict[str, float] = {}
        for key, lab in [("raw", "raw_labels"), ("filt", "filtered_labels")]:
            s1, s2 = a[lab], b[lab]
            common = s1.index.intersection(s2.index)
            v1 = s1.loc[common].astype(int).to_numpy()
            v2 = s2.loc[common].astype(int).to_numpy()
            d[f"agreement_{key}"] = float((v1 == v2).mean())
            d[f"ari_{key}"] = float(adjusted_rand_score(v1, v2))
        d["n_common"] = int(len(common))
        res["label_stability"][name] = d
        print(f"  {name:<8} agree raw/filt = {d['agreement_raw']:.3f}/{d['agreement_filt']:.3f}   "
              f"ARI raw/filt = {d['ari_raw']:+.3f}/{d['ari_filt']:+.3f}")

    out_path = os.path.join(OOS_DIR, "rigor_composition_clr_eiv.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    print(f"total elapsed: {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
