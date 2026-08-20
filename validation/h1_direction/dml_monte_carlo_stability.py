"""Measure the Monte Carlo noise of the causal-forest ATE, and whether the
canonical forest size is large enough for the reported point estimates.

Why this exists
---------------
The input data are deterministic: fixed OHLCV, fixed entropy features, fixed GMM
labels, fixed PurgedKFold folds. The ESTIMATOR is not. CausalForestDML draws
randomness from three places:

  1. each of the `n_estimators` causal trees is fit on a random subsample, and
     honest splitting halves that subsample again (one half chooses splits, the
     other estimates leaf values);
  2. a random subset of features is considered at each split;
  3. the two nuisance forests -- E[Y|X] and E[T|X], 200 trees each -- carry
     their own bootstrap draws.

The reported ATE is therefore a Monte Carlo average over `n_estimators` trees.
Its seed-to-seed standard deviation falls roughly as 1/sqrt(n_estimators), so a
fixed seed makes a number REPRODUCIBLE without making it STABLE: with too few
trees you are reporting one draw from a distribution that is still wide.

This script measures that distribution directly. For each market it fits the
canonical specification across S seeds at several forest sizes and reports the
across-seed SD of the ATE against the model's own reported standard error. The
decision rule is the ratio MC_SD / SE: when it is small the Monte Carlo noise is
negligible next to sampling uncertainty and the forest is large enough; when it
approaches 1 the point estimate is as much estimator noise as it is signal, and
n_estimators must rise.

Everything else -- window, features, labels, folds, depth, nuisance models --
is the canonical specification, imported rather than reimplemented.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(_VALIDATION))

from econml.dml import CausalForestDML  # noqa: E402
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor  # noqa: E402

from validation._features import run_full_pipeline  # noqa: E402
from validation.h1_direction.h1_dml import (  # noqa: E402
    MARKETS, START, END, PRIMARY_HORIZON, build_dml_dataset,
)
from validation.h1_direction.h1_dml_cpcv import PurgedKFold, PKF_N_SPLITS, PKF_EMBARGO  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

# Markets are drawn from either panel and chosen for what they bracket:
#   KSE100   -- largest observed run-to-run ATE spread, smallest treated cell
#   SHANGHAI -- the only two-gate decisive market; must be stable or the
#               paper's single strongest directional claim is estimator noise
#   SPX      -- a directional claim on a comfortable sample
#   NIKKEI   -- one of the two markets whose ATE sign differed across runs
# If 300 trees suffice anywhere it is SPX; if they fail anywhere it is KSE100.
FOCUS = os.environ.get("MC_MARKETS", "KSE100,SHANGHAI,SPX,NIKKEI").split(",")
# Two sizes are enough to test the mechanism as well as the level: if the noise
# really is a tree-count Monte Carlo effect, SD must fall by about sqrt(5).
TREE_GRID = [int(x) for x in os.environ.get("MC_TREES", "300,1500").split(",")]
N_SEEDS = int(os.environ.get("MC_SEEDS", "6"))

OUT_DIR = os.path.join(_VALIDATION, "results_v2")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_JSON = os.path.join(OUT_DIR, "dml_monte_carlo_stability.json")


def fit_once(df, n_trees: int, seed: int) -> dict:
    feature_cols = [c for c in df.columns if c not in ("fwd_vol", "T", "regime")]
    Y, T, X = df["fwd_vol"].values, df["T"].values, df[feature_cols].values
    model = CausalForestDML(
        model_y=RandomForestRegressor(n_estimators=200, max_depth=6,
                                      random_state=seed, n_jobs=-1),
        model_t=RandomForestClassifier(n_estimators=200, max_depth=6,
                                       random_state=seed, n_jobs=-1),
        n_estimators=n_trees, max_depth=6,
        discrete_treatment=True,
        cv=PurgedKFold(n_splits=PKF_N_SPLITS, embargo=PKF_EMBARGO),
        random_state=seed, n_jobs=-1,
    )
    model.fit(Y, T, X=X, W=None)
    ate = float(model.ate(X))
    lo, hi = model.ate_interval(X, alpha=0.05)
    return {"ate": ate, "ci_lo": float(lo), "ci_hi": float(hi),
            "se": float((float(hi) - float(lo)) / (2 * 1.959963984540054))}


def main() -> int:
    # n=8 entries win on collision; the two panels agree on ticker/source anyway.
    cfg_by_name = {c["name"]: c for c in MARKETS_N27}
    cfg_by_name.update({c["name"]: c for c in MARKETS})
    results: dict[str, dict] = {}

    for name in FOCUS:
        cfg = cfg_by_name.get(name)
        if cfg is None:
            print(f"[{name}] not in MARKETS -- skipped")
            continue
        print(f"\n=== {name} ===")
        out = run_full_pipeline(market=name, ticker=cfg["ticker"],
                                source=cfg["source"], start=START, end=END)
        # Filtered labels are the canonical DML track (Sec 3.4, Sec 4.2.1).
        df = build_dml_dataset(out["ohlcv"], out["filtered_labels"],
                               horizon=PRIMARY_HORIZON)
        n_det = int(df["T"].sum())
        print(f"  N = {len(df)}  treated = {n_det}  control = {len(df) - n_det}")

        per_market = {"n_obs": int(len(df)), "n_det": n_det,
                      "n_sto": int(len(df) - n_det), "grid": {}}

        for n_trees in TREE_GRID:
            ates, ses, t0 = [], [], time.time()
            for s in range(N_SEEDS):
                r = fit_once(df, n_trees, seed=1000 + s)
                ates.append(r["ate"])
                ses.append(r["se"])
            ates, ses = np.array(ates), np.array(ses)
            mc_sd = float(ates.std(ddof=1))
            mean_se = float(ses.mean())
            signs = set(np.sign(ates).astype(int).tolist())
            row = {
                "n_estimators": n_trees,
                "n_seeds": N_SEEDS,
                "ate_mean": float(ates.mean()),
                "ate_mc_sd": mc_sd,
                "ate_min": float(ates.min()),
                "ate_max": float(ates.max()),
                "ate_range": float(ates.max() - ates.min()),
                "mean_reported_se": mean_se,
                # The decision statistic: Monte Carlo noise as a fraction of the
                # sampling uncertainty the paper already reports.
                "mc_sd_over_se": mc_sd / mean_se if mean_se else float("nan"),
                "sign_stable": len(signs) == 1,
                "elapsed_s": round(time.time() - t0, 1),
                "ates": [float(a) for a in ates],
            }
            per_market["grid"][str(n_trees)] = row
            print(f"  trees={n_trees:5d}  mean={row['ate_mean']:+8.3f}  "
                  f"MC_SD={mc_sd:6.3f}  range={row['ate_range']:6.3f}  "
                  f"SE={mean_se:7.3f}  MC_SD/SE={row['mc_sd_over_se']:.3f}  "
                  f"sign_stable={row['sign_stable']}  ({row['elapsed_s']}s)")
        results[name] = per_market

    payload = {
        "spec": "Monte Carlo stability of the canonical CausalForestDML ATE: "
                "S seeds x forest-size grid, canonical window/features/labels/folds.",
        "window": [START, END],
        "horizon": PRIMARY_HORIZON,
        "purged_kfold": {"n_splits": PKF_N_SPLITS, "embargo": PKF_EMBARGO},
        "n_seeds": N_SEEDS,
        "tree_grid": TREE_GRID,
        "results": results,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nJSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
