"""SimpleVol control for H2 entropy-specificity (referee item A4).

Runs trivial volatility features — rolling 22-day SD of log returns and its
20-day change — through the IDENTICAL downstream machinery (K=3 full-cov GMM
seed 42, Schmitt trigger 0.60/0.35/8, KW-H on forward 20-day realized vol),
then computes the cross-market correlations rho(H_SimpleVol, RPS/tier) on
both panels. If a mechanical volatility feature reproduces the cross-market
gradient, the entropy-specificity claim re-scopes to incremental
informativeness; if it does not, entropy-plane specificity is established
against the trivial control (complementing the Chronos learned-feature
control of App H).

Output: validation/results_v2/h2_simplevol_control.json
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.mixture import GaussianMixture

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))
from validation._features import load_ohlcv  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402
from skills.ds_skill import apply_hysteresis  # noqa: E402

START = "2018-01-01"
END = "2026-06-30"
ANALYSIS_START = "2020-01-01"
SEED = 42
FWD_H = 20
VOL_W = 22
CHG_H = 20

RES = os.path.join(_VALIDATION, "results_v2")
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
            df = load_ohlcv(market=name, ticker=cfg["ticker"],
                            source=cfg["source"], start=START, end=END)
        except Exception as e:
            print(f"[{name}] SKIP: {type(e).__name__}: {e}")
            continue
        r = np.log(df["Close"]).diff()
        feat = pd.DataFrame({
            "roll_sd": r.rolling(VOL_W).std() * np.sqrt(252) * 100,
        })
        feat["sd_chg"] = feat["roll_sd"].diff(CHG_H)
        feat = feat.dropna()
        X = ((feat - feat.mean()) / feat.std()).to_numpy()
        gmm = GaussianMixture(n_components=3, covariance_type="full",
                              random_state=SEED, n_init=10).fit(X)
        # order components by roll_sd mean so label semantics are stable
        order = np.argsort(gmm.means_[:, 0])
        remap = np.empty(3, dtype=int)
        remap[order] = np.arange(3)
        post = gmm.predict_proba(X)[:, order]
        raw = pd.Series(post.argmax(axis=1), index=feat.index)
        filt = pd.Series(apply_hysteresis(post), index=feat.index)

        fv = (r.rolling(FWD_H).std().shift(-FWD_H) * np.sqrt(252) * 100)
        entry = {}
        for lbl_key, series in (("raw", raw), ("filtered", filt)):
            d = pd.DataFrame({"lab": series, "fv": fv}).loc[ANALYSIS_START:].dropna()
            entry[lbl_key] = {"H": kw_h(d["lab"].to_numpy(), d["fv"].to_numpy()),
                              "N_obs": int(len(d))}
        per_market[name] = entry
        print(f"[{name}] SimpleVol H raw={entry['raw']['H']:8.2f} "
              f"filt={entry['filtered']['H']:8.2f} N={entry['raw']['N_obs']}")

    cross = {}
    for panel_name, ms in (("n8", [m for m in N8 if m in per_market]),
                           ("n27", list(per_market))):
        for lbl in ("raw", "filtered"):
            hs = [per_market[m][lbl]["H"] for m in ms]
            r1, p1 = stats.spearmanr(hs, [RPS_VALUES[m] for m in ms])
            r2, p2 = stats.spearmanr(hs, [TIER_RANK[m] for m in ms])
            cross[f"{panel_name}_{lbl}"] = {"n": len(ms),
                                            "rho_H_rps": float(r1), "p_rps": float(p1),
                                            "rho_H_tier": float(r2), "p_tier": float(p2)}
            print(f"{panel_name} {lbl}: rho(H_sv,RPS)={r1:+.3f} (p={p1:.4f}) | "
                  f"rho(H_sv,tier)={r2:+.3f} (p={p2:.4f})")

    out_doc = {"spec": ("SimpleVol control (A4): [22d rolling SD, 20d SD change] z-scored -> "
                        "K=3 full-cov GMM (seed 42, components ordered by SD mean) -> Schmitt "
                        "0.60/0.35/8 -> KW-H on fwd 20d vol; cross-market Spearman vs RPS/tier."),
               "window": [ANALYSIS_START, END], "seed": SEED,
               "per_market": per_market, "cross_market": cross,
               "elapsed_min": round((time.time() - t0) / 60, 1)}
    path = os.path.join(RES, "controls/h2_simplevol_control.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, indent=2, default=float)
    print("JSON:", path, f"({out_doc['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
