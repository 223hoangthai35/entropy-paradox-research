"""Is the cross-market ordering an artifact of fitting the mixture on the full sample?

The paper's labels come from a Gaussian mixture fitted on every bar in the window,
so the cluster boundaries are informed by the whole period including the days whose
forward volatility the labels are then asked to separate. The paper scopes its claim
to that -- the H statistic measures how much structure the partition organizes, not
what a real-time user could have extracted -- and pre-registers walk-forward
labeling as a forward extension.

Scoping the claim answers the deployment question. It does not answer the referee's
question, which is different and sharper: could the cross-market ORDERING itself be
manufactured by full-sample fitting? A full-sample mixture may find more exploitable
structure in exactly the markets that have more structure to find, which would make
the ordering an artifact of the fitting procedure rather than a property of the
markets.

That question does not need a walk-forward rebuild. It needs one honest
out-of-sample labeling, which is what this script runs: fit the mixture and calibrate
the Schmitt trigger on the first 60% of each market's bars, apply the frozen fit to
the remaining 40%, and compute Kruskal-Wallis H on the held-out segment alone. No
information from the evaluated bars enters the labeling. If the ordering survives, the
full-sample-fitting objection is answered at the level it was raised.

Two controls make the comparison readable. The full-sample H is recomputed on the
SAME held-out bars, so the two differ only in how the labels were produced and not in
which days are scored. And the raw and filtered tracks are reported separately, since
the stabilizer is the component whose transport the paper already reports as failing.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from validation._features import (  # noqa: E402
    SPE_Z_WIN, build_plane1_features, fit_classifier_and_filter, load_ohlcv,
)
from validation.cross_market_v2 import compute_forward_metrics  # noqa: E402
from validation.h1_dml import START, END  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

R = os.path.join(os.path.dirname(__file__), "results_v2")
OUT = os.path.join(R, "causal_labeling_check.json")
TRAIN_FRAC = 0.60
MIN_PER_GROUP = 5
SEED = 42

eta = json.load(io.open(os.path.join(R, "n27_experiment",
                                     "h2_eta_squared_n27.json"), encoding="utf-8"))
RPS = eta["rps_point_estimates"]


def kw(lab: np.ndarray, y: np.ndarray) -> float:
    g = [y[lab == k] for k in np.unique(lab)]
    g = [x for x in g if len(x) >= MIN_PER_GROUP]
    if len(g) < 2:
        return float("nan")
    try:
        return float(stats.kruskal(*g)[0])
    except ValueError:
        return float("nan")


def one_market(m: str, cfg: dict) -> dict | None:
    try:
        ohlcv = load_ohlcv(m, cfg["ticker"], cfg["source"], START, END)
        feat = build_plane1_features(ohlcv)
    except Exception as e:
        print(f"  [{m}] SKIP {type(e).__name__}")
        return None
    if len(feat) < SPE_Z_WIN + 300:
        print(f"  [{m}] SKIP only {len(feat)} feature bars")
        return None

    cut = int(len(feat) * TRAIN_FRAC)
    train, test = feat.iloc[:cut], feat.iloc[cut:]

    # Causal labels: the mixture and the trigger see the training segment only,
    # then the frozen fit is applied forward.
    fit = fit_classifier_and_filter(train, random_state=SEED)
    raw_oos = fit["classifier"].predict(test.values)
    filt_oos = fit["wrapper"].transform(test.values)

    # Full-sample labels, scored on the same held-out bars so the only difference
    # between the two readings is how the labels were produced.
    full = fit_classifier_and_filter(feat, random_state=SEED)
    raw_full = full["raw_labels"].loc[test.index].values
    filt_full = full["filtered_labels"].loc[test.index].values

    fwd = compute_forward_metrics(ohlcv, horizon=20)["FwdVol20d"].reindex(test.index)
    ok = fwd.notna().values
    y = fwd.values[ok]
    if ok.sum() < 200:
        print(f"  [{m}] SKIP only {int(ok.sum())} scorable held-out bars")
        return None

    out = {
        "n_train": int(cut), "n_test_scored": int(ok.sum()),
        "H_causal_raw": kw(np.asarray(raw_oos)[ok], y),
        "H_causal_filt": kw(np.asarray(filt_oos)[ok], y),
        "H_fullsample_raw": kw(np.asarray(raw_full)[ok], y),
        "H_fullsample_filt": kw(np.asarray(filt_full)[ok], y),
    }
    print(f"  [{m:9}] causal {out['H_causal_raw']:7.2f} | "
          f"full-sample {out['H_fullsample_raw']:7.2f}  "
          f"({out['n_test_scored']} held-out bars)")
    return out


def main() -> int:
    t0 = time.time()
    print(f"Fit on first {TRAIN_FRAC:.0%} of bars, score the remainder.\n")
    per = {}
    for cfg in MARKETS_N27:
        m = cfg["name"]
        if m not in RPS:
            continue
        r = one_market(m, cfg)
        if r is not None:
            per[m] = r

    ms = [m for m in per if np.isfinite(per[m]["H_causal_raw"])]
    v = np.array([RPS[m] for m in ms])
    res = {
        "spec": "Out-of-sample labeling control: mixture and Schmitt trigger fitted "
                "on the first 60% of each market's bars, applied forward, scored on "
                "the held-out remainder. The full-sample labels are scored on the "
                "same held-out bars for comparison.",
        "window": [START, END], "train_frac": TRAIN_FRAC, "seed": SEED,
        "n_markets": len(ms), "per_market": per, "cross_market": {},
    }

    print(f"\n{len(ms)} markets scored on held-out bars\n")
    print(f"  {'labels':22} {'rho(H, RPS)':>12} {'p':>9}")
    for lab, key in (("causal (out-of-sample)", "H_causal"),
                     ("full-sample", "H_fullsample")):
        for track in ("raw", "filt"):
            H = np.array([per[m][f"{key}_{track}"] for m in ms])
            good = np.isfinite(H)
            r, p = stats.spearmanr(H[good], v[good])
            res["cross_market"][f"{key}_{track}"] = {
                "rho": float(r), "p": float(p), "n": int(good.sum())}
            print(f"  {lab + ' / ' + track:22} {r:+12.3f} {p:9.4f}")

    # How much of the full-sample H is lost when the labels cannot see the bars
    ratio = np.array([per[m]["H_causal_raw"] / per[m]["H_fullsample_raw"]
                      for m in ms if per[m]["H_fullsample_raw"] > 0])
    rr, rp = stats.spearmanr(ratio, np.array(
        [RPS[m] for m in ms if per[m]["H_fullsample_raw"] > 0]))
    res["retention"] = {"median": float(np.median(ratio)),
                        "mean": float(ratio.mean()),
                        "rho_vs_RPS": float(rr), "p_vs_RPS": float(rp)}
    print(f"\n  H retained by causal labels: median {np.median(ratio):.2f}x "
          f"of the full-sample reading")
    print(f"  does that retention favour high-RPS markets? rho = {rr:+.3f} "
          f"(p = {rp:.3f})  <- the artifact channel")

    res["elapsed_min"] = round((time.time() - t0) / 60, 1)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\nJSON: {OUT}  ({res['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
