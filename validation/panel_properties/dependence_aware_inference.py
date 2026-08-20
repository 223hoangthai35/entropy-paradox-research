"""Inference on the cross-market ordering when the markets are not independent.

The headline Spearman test treats twenty-seven markets as twenty-seven draws.
They are not: the panel shares global shocks, fourteen members are Asian, and
three are crypto assets on overlapping infrastructure. A permutation null that
shuffles the predictor freely across all markets destroys more structure than the
data contain, so its p-value is optimistic by an unknown amount.

Two permutation nulls bracket the truth, and reporting only one of them
misrepresents the evidence.

  BETWEEN-BLOCK permutation moves whole strata against each other, holding the
  within-stratum arrangement fixed. It asks whether the ordering is anything more
  than four or five block means lining up. It is very conservative: it discards
  all within-stratum variation in the predictor, which is exactly where this
  paper's claim lives, since Section 4.3 shows the ordering survives holding the
  stratum fixed. With k blocks there are only k! arrangements, so the smallest
  p-value the test can return is 1/k! -- 0.042 at four blocks. A p-value near
  that floor means the test has run out of resolution, not that the effect is
  absent.

  WITHIN-BLOCK permutation shuffles the predictor inside each stratum, holding
  the between-stratum structure fixed. It asks whether the predictor orders
  informativeness beyond what stratum membership already explains. This is the
  permutation analogue of the partial correlation the paper reports, and it is
  the direct test of what the paper actually claims.

A cluster bootstrap over strata accompanies both.

The effective sample size implied by the mean pairwise return correlation is
reported as context only. That adjustment is derived for the variance of a mean
of correlated observations; it is not the right correction for a rank
correlation between two market-level attributes, one of which -- retail
participation -- is not a function of the return series at all. Quoting it as an
inferential n would overstate the problem as badly as ignoring dependence
understates it.
"""
from __future__ import annotations

import io
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(_VALIDATION))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from validation._features import load_ohlcv  # noqa: E402
from validation.h1_direction.h1_dml import START, END  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

R = os.path.join(_VALIDATION, "results_v2")
OUT = os.path.join(R, "panel_properties/dependence_aware_inference.json")
SEED, N_PERM, N_BOOT = 42, 20000, 20000

eta = json.load(io.open(os.path.join(R, "n27_experiment",
                                     "h2_eta_squared_n27.json"), encoding="utf-8"))
RPS, PER = eta["rps_point_estimates"], eta["per_market"]
CAT = {c["name"]: c["category"] for c in MARKETS_N27}
ASIAN = {"VNINDEX", "SHANGHAI", "KOSPI", "NIFTY", "JKSE", "TWII", "SET", "PSEI",
         "HSI", "STI", "NIKKEI", "KSE100", "DSEX"}


def stratum(m: str) -> str:
    c = CAT.get(m)
    if c == "Crypto":
        return "crypto"
    if c == "Developed":
        return "developed"
    if c == "Frontier":
        return "frontier"
    return "asian-emerging" if m in ASIAN else "other-emerging"


def between_block_p(H, v, blocks, rng, n_perm):
    obs = stats.spearmanr(H, v)[0]
    uniq = sorted(set(blocks))
    idx = [np.flatnonzero(np.array(blocks) == b) for b in uniq]
    hits = 0
    for _ in range(n_perm):
        order = rng.permutation(len(uniq))
        vp = np.empty_like(v)
        pool = np.concatenate([v[idx[k]] for k in order])
        pos = 0
        for d in idx:
            vp[d] = pool[pos:pos + len(d)]
            pos += len(d)
        if abs(stats.spearmanr(H, vp)[0]) >= abs(obs):
            hits += 1
    return obs, (1 + hits) / (1 + n_perm)


def within_block_p(H, v, blocks, rng, n_perm):
    obs = stats.spearmanr(H, v)[0]
    idx = [np.flatnonzero(np.array(blocks) == b) for b in sorted(set(blocks))]
    hits = 0
    for _ in range(n_perm):
        vp = v.copy()
        for d in idx:
            vp[d] = rng.permutation(v[d])
        if abs(stats.spearmanr(H, vp)[0]) >= abs(obs):
            hits += 1
    return obs, (1 + hits) / (1 + n_perm)


def cluster_bootstrap(H, v, blocks, rng, n_boot):
    uniq = sorted(set(blocks))
    idx = {b: np.flatnonzero(np.array(blocks) == b) for b in uniq}
    draws = []
    for _ in range(n_boot):
        pick = rng.choice(len(uniq), len(uniq), replace=True)
        sel = np.concatenate([idx[uniq[k]] for k in pick])
        if len(np.unique(v[sel])) < 3:
            continue
        draws.append(stats.spearmanr(H[sel], v[sel])[0])
    d = np.array(draws)
    return {"mean": float(d.mean()), "ci_lo": float(np.percentile(d, 2.5)),
            "ci_hi": float(np.percentile(d, 97.5)),
            "P_gt_0": float((d > 0).mean()), "P_gt_0.5": float((d > 0.5).mean()),
            "n_draws": int(len(d))}


def main() -> int:
    t0 = time.time()
    series = {}
    for cfg in MARKETS_N27:
        m = cfg["name"]
        if m not in PER:
            continue
        try:
            df = load_ohlcv(m, cfg["ticker"], cfg["source"], START, END)
        except Exception as e:
            print(f"  [{m}] SKIP {type(e).__name__}")
            continue
        c = df["Close"].astype(float)
        series[m] = np.log(c / c.shift(1)).dropna()

    # How dependent is the panel. The 27 exchanges share no fully common
    # calendar, so this is pairwise-complete; thin frontier markets that overlap
    # no partner for a full year drop out of the *descriptive* matrix only. The
    # tests below run on all 27 -- they need H, RPS and stratum, not returns --
    # so the dependence adjustment is never confounded with a change of sample.
    ret = pd.DataFrame(series)
    C = ret.corr(method="pearson", min_periods=250)
    corr_names = [m for m in C.columns if C[m].notna().sum() > 1]
    C = C.loc[corr_names, corr_names]
    nc = len(corr_names)
    off = C.values[np.triu_indices(nc, 1)]
    off = off[np.isfinite(off)]
    r_bar, r_med = float(off.mean()), float(np.median(off))
    n_eff = 27 / (1 + 26 * r_bar)

    names = [m for m in PER if m in RPS]
    n = len(names)
    print(f"correlation structure measured on {nc} of {n} markets "
          f"({len(off)} pairs with >=250 shared days)")
    print(f"  mean pairwise return correlation : {r_bar:+.3f} "
          f"(median {r_med:+.3f}, max {off.max():+.3f})")
    print(f"  n_eff under the mean-of-correlated-observations adjustment: "
          f"{n_eff:.1f} — context only, see module docstring")
    print(f"  permutation and bootstrap run on all {n} markets")

    H_raw = np.array([PER[m]["raw"]["H_stat"] for m in names])
    H_filt = np.array([PER[m]["filtered"]["H_stat"] for m in names])
    v = np.array([RPS[m] for m in names])
    blocks = [stratum(m) for m in names]
    k = len(set(blocks))
    floor = 1 / math.factorial(k)
    print(f"  strata: {k} blocks -> between-block permutation floor p = {floor:.3f}")
    for b in sorted(set(blocks)):
        print(f"     {b:16} n = {blocks.count(b)}")

    out = {
        "spec": "Dependence-aware inference: between-block and within-block "
                "permutation over market strata, plus cluster bootstrap.",
        "window": [START, END], "n_markets": n,
        "n_markets_in_corr_matrix": nc,
        "corr_matrix_markets": corr_names,
        "mean_pairwise_return_corr": r_bar,
        "median_pairwise_return_corr": r_med,
        "n_effective_context_only": float(n_eff),
        "n_blocks": k, "between_block_p_floor": float(floor),
        "seed": SEED, "n_perm": N_PERM, "n_boot": N_BOOT,
        "strata": {b: [m for m, x in zip(names, blocks) if x == b]
                   for b in sorted(set(blocks))},
        "tests": {},
    }

    print(f"\n{'track':10} {'free p':>9} {'between p':>11} {'within p':>10}")
    for track, H in (("raw", H_raw), ("filtered", H_filt)):
        free_r, free_p = stats.spearmanr(H, v)
        _, bp = between_block_p(H, v, blocks, np.random.default_rng(SEED), N_PERM)
        _, wp = within_block_p(H, v, blocks, np.random.default_rng(SEED), N_PERM)
        cb = cluster_bootstrap(H, v, blocks, np.random.default_rng(SEED), N_BOOT)
        out["tests"][track] = {
            "rho": float(free_r), "p_free_permutation": float(free_p),
            "p_between_block": float(bp), "p_within_block": float(wp),
            "cluster_bootstrap": cb,
        }
        print(f"{track:10} {free_p:9.4f} {bp:11.4f} {wp:10.4f}   "
              f"rho = {free_r:+.3f}")
        print(f"{'':10} cluster bootstrap 95% CI [{cb['ci_lo']:+.3f}, "
              f"{cb['ci_hi']:+.3f}]  P(rho>0) = {cb['P_gt_0']:.3f}")

    out["elapsed_min"] = round((time.time() - t0) / 60, 1)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nJSON: {OUT}  ({out['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
