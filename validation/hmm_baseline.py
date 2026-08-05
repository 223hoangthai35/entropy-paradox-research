"""HMM baseline for the regime classifier (referee item B8).

Fits a 3-state Gaussian HMM (full covariance, seed 42) on the IDENTICAL
Plane-1 features [WPE, SPE_Z] per market and scores the same downstream
quantities as the GMM + Schmitt pipeline: KW-H on forward 20-day realized
vol, flips/yr, and the cross-market correlations rho(H_HMM, RPS/tier) on
both panels. The HMM embeds temporal persistence in the model (transition
matrix) rather than as a post-filter, making it the natural alternative
architecture a referee will ask about.

States are ordered by their SPE_Z mean so label semantics align with the
GMM convention (0 = lowest SPE_Z).

Output: validation/results_v2/hmm_baseline.json
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from scipy import stats

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from validation._features import run_full_pipeline, flip_rate_per_year  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

START = "2018-01-01"
END = "2026-06-30"
ANALYSIS_START = "2020-01-01"
SEED = 42
FWD_H = 20

RES = os.path.join(os.path.dirname(__file__), "results_v2")
RPS_VALUES = json.load(open(os.path.join(
    RES, "n27_experiment", "h2_cascade_n27_full_classification.json"),
    encoding="utf-8"))["all_p1_reference"]["rps_values"]
TIER_RANK = {c["name"]: c["tier_rank"] for c in MARKETS_N27}
N8 = ["VNINDEX", "BVB", "KOSPI", "NIFTY", "SPX", "FTSE", "NIKKEI", "BTC"]


def kw_h(labels: np.ndarray, y: np.ndarray) -> float:
    groups = [y[labels == k] for k in np.unique(labels)]
    groups = [g for g in groups if len(g) >= 5]
    if len(groups) < 2:
        return np.nan
    return float(stats.kruskal(*groups).statistic)


def main() -> int:
    t0 = time.time()
    per_market = {}
    for cfg in MARKETS_N27:
        name = cfg["name"]
        try:
            out = run_full_pipeline(market=name, ticker=cfg["ticker"],
                                    source=cfg["source"], start=START, end=END)
        except Exception as e:
            print(f"[{name}] SKIP: {type(e).__name__}: {e}")
            continue
        feat = out["features"][["WPE", "SPE_Z"]] if "WPE" in out["features"].columns \
            else out["features"].iloc[:, :2]
        X = feat.to_numpy()
        hmm = GaussianHMM(n_components=3, covariance_type="full",
                          random_state=SEED, n_iter=200)
        hmm.fit(X)
        states = hmm.predict(X)
        order = np.argsort(hmm.means_[:, 1])          # by SPE_Z mean
        remap = np.empty(3, dtype=int)
        remap[order] = np.arange(3)
        lab = pd.Series(remap[states], index=feat.index)

        r = np.log(out["ohlcv"]["Close"]).diff()
        fv = r.rolling(FWD_H).std().shift(-FWD_H) * np.sqrt(252) * 100
        d = pd.DataFrame({"lab": lab, "fv": fv}).loc[ANALYSIS_START:].dropna()
        h = kw_h(d["lab"].to_numpy(), d["fv"].to_numpy())
        fpy = flip_rate_per_year(lab.loc[ANALYSIS_START:])
        per_market[name] = {"H_hmm": h, "flips_per_year": float(fpy),
                            "N_obs": int(len(d)),
                            "converged": bool(hmm.monitor_.converged)}
        print(f"[{name}] H_hmm={h:8.2f} flips/yr={fpy:6.1f} N={len(d)}")

    cross = {}
    for panel_name, ms in (("n8", [m for m in N8 if m in per_market]),
                           ("n27", list(per_market))):
        hs = [per_market[m]["H_hmm"] for m in ms]
        r1, p1 = stats.spearmanr(hs, [RPS_VALUES[m] for m in ms])
        r2, p2 = stats.spearmanr(hs, [TIER_RANK[m] for m in ms])
        cross[panel_name] = {"n": len(ms), "rho_H_rps": float(r1), "p_rps": float(p1),
                             "rho_H_tier": float(r2), "p_tier": float(p2)}
        print(f"{panel_name}: rho(H_hmm,RPS)={r1:+.3f} (p={p1:.4f}) | "
              f"rho(H_hmm,tier)={r2:+.3f} (p={p2:.4f})")

    doc = {"spec": ("3-state Gaussian HMM (full cov, seed 42, 200 iter) on identical "
                    "Plane-1 [WPE, SPE_Z]; states ordered by SPE_Z mean; KW-H on fwd "
                    "20d vol; cross-market Spearman vs RPS/tier."),
           "window": [ANALYSIS_START, END], "seed": SEED,
           "per_market": per_market, "cross_market": cross,
           "elapsed_min": round((time.time() - t0) / 60, 1)}
    path = os.path.join(RES, "hmm_baseline.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, default=float)
    print("JSON:", path, f"({doc['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
