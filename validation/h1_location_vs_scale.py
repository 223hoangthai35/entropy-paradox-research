"""What kind of forward-volatility information do the regime labels carry?

The panel's direction effects do not reject homogeneity once the rotation-placebo
interval inflation is applied, and the pooled contrast is essentially zero. That
is a statement about the LOCATION of the forward-volatility distribution: on
average, the Deterministic and Stochastic regimes are followed by the same mean
volatility. It is not a statement about whether the labels are informative --
Kruskal-Wallis H is sensitive to any distributional separation, not only to a
shift in the mean.

This script separates the two. For each market it computes, on the canonical
filtered labels:

  location  -- the standardized gap between the Det and Sto MEANS of forward vol
               (the quantity the DML ATE estimates)
  scale     -- the ratio of the Det and Sto standard deviations, and the ratio of
               their interquartile ranges (robust to the tail)
  tail      -- the ratio of their 90th percentiles

and then asks which of these tracks H across markets, and which tracks retail
participation. If regime informativeness is a location phenomenon, H should
follow the standardized mean gap. If it is a dispersion phenomenon, H should
follow the scale ratios while the mean gap stays near zero -- which would say
the labels separate volatility REGIMES rather than volatility LEVELS.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import kruskal, spearmanr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation._features import run_full_pipeline  # noqa: E402
from validation.h1_dml import START, END, PRIMARY_HORIZON  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2", "n27_experiment")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_JSON = os.path.join(OUT_DIR, "h1_location_vs_scale.json")

RPS = json.load(io.open(os.path.join(os.path.dirname(__file__), "results_v2",
                                     "n27_experiment", "h2_eta_squared_n27.json"),
                        encoding="utf-8"))["rps_point_estimates"]

DET, TRA, STO = 0, 1, 2


def describe(name: str, ticker: str, source: str) -> dict | None:
    out = run_full_pipeline(market=name, ticker=ticker, source=source,
                            start=START, end=END)
    ohlcv = out["ohlcv"]
    # Same forward-vol construction as h2_eta_squared_n27, so H reproduces.
    close = ohlcv["Close"].astype(float)
    log_ret = np.log(close / close.shift(1))
    fwd_vol = (log_ret.shift(-1).rolling(PRIMARY_HORIZON).std()
               .shift(-(PRIMARY_HORIZON - 1)) * np.sqrt(252) * 100.0)

    rec: dict = {"market": name}
    for track, labels in (("raw", out["raw_labels"]), ("filtered", out["filtered_labels"])):
        df = pd.DataFrame({"label": labels.reindex(ohlcv.index),
                           "fwd_vol": fwd_vol}).dropna()
        g = {k: df.loc[df["label"] == k, "fwd_vol"].values for k in (DET, TRA, STO)}
        if min(len(v) for v in g.values()) < 30:
            return None
        H, p = kruskal(*[g[k] for k in (DET, TRA, STO)])

        det, sto = g[DET], g[STO]
        pooled_sd = float(np.std(np.concatenate([det, sto]), ddof=1))
        rec[track] = {
            "H": float(H), "p": float(p),
            "n_det": len(det), "n_tra": len(g[TRA]), "n_sto": len(sto),
            # location: the quantity the DML ATE estimates, standardized
            "mean_det": float(det.mean()), "mean_sto": float(sto.mean()),
            "mean_gap": float(det.mean() - sto.mean()),
            "cohens_d": float((det.mean() - sto.mean()) / pooled_sd) if pooled_sd else 0.0,
            # scale: dispersion contrast
            "sd_det": float(det.std(ddof=1)), "sd_sto": float(sto.std(ddof=1)),
            "sd_ratio": float(det.std(ddof=1) / sto.std(ddof=1)) if sto.std(ddof=1) else np.nan,
            "iqr_det": float(np.subtract(*np.percentile(det, [75, 25]))),
            "iqr_sto": float(np.subtract(*np.percentile(sto, [75, 25]))),
            "iqr_ratio": float(np.subtract(*np.percentile(det, [75, 25])) /
                               np.subtract(*np.percentile(sto, [75, 25]))),
            # tail
            "p90_det": float(np.percentile(det, 90)),
            "p90_sto": float(np.percentile(sto, 90)),
            "p90_ratio": float(np.percentile(det, 90) / np.percentile(sto, 90)),
        }
    return rec


def main() -> int:
    per: dict[str, dict] = {}
    t0 = time.time()
    for cfg in MARKETS_N27:
        try:
            r = describe(cfg["name"], cfg["ticker"], cfg["source"])
        except Exception as e:
            print(f"[{cfg['name']}] SKIP {type(e).__name__}: {e}")
            continue
        if r is None:
            print(f"[{cfg['name']}] SKIP thin regime cell")
            continue
        per[cfg["name"]] = r
        f = r["filtered"]
        print(f"[{cfg['name']:9}] H={f['H']:8.2f}  d={f['cohens_d']:+6.3f}  "
              f"sd_ratio={f['sd_ratio']:5.2f}  iqr_ratio={f['iqr_ratio']:5.2f}  "
              f"p90_ratio={f['p90_ratio']:5.2f}")

    names = sorted(per)
    print(f"\n{len(names)} markets\n")
    summary = {}
    for track in ("raw", "filtered"):
        H = np.array([per[m][track]["H"] for m in names])
        rps = np.array([RPS[m] for m in names])
        block = {}
        print(f"--- {track} labels ---")
        for key, lab in [("cohens_d", "location (Cohen's d, Det vs Sto)"),
                         ("mean_gap", "location (raw mean gap)"),
                         ("sd_ratio", "scale (SD ratio)"),
                         ("iqr_ratio", "scale (IQR ratio)"),
                         ("p90_ratio", "tail (p90 ratio)")]:
            v = np.array([per[m][track][key] for m in names])
            # |.| for the ratio measures: separation in EITHER direction is
            # separation, and the direction is exactly what does not generalize.
            mag = np.abs(np.log(v)) if key.endswith("ratio") else np.abs(v)
            r_h, p_h = spearmanr(H, mag)
            r_r, p_r = spearmanr(rps, mag)
            r_sig, p_sig = spearmanr(H, v)
            block[key] = {"rho_H_absmag": float(r_h), "p_H_absmag": float(p_h),
                          "rho_RPS_absmag": float(r_r), "p_RPS_absmag": float(p_r),
                          "rho_H_signed": float(r_sig), "p_H_signed": float(p_sig),
                          "median": float(np.median(v))}
            print(f"  {lab:38} median {np.median(v):+7.3f} | "
                  f"rho(H, |.|) = {r_h:+.3f} (p={p_h:.4f}) | "
                  f"rho(RPS, |.|) = {r_r:+.3f} (p={p_r:.4f})")
        summary[track] = block
        print()

    payload = {
        "spec": "Location vs scale decomposition of the Det/Sto forward-volatility "
                "contrast on the n=27 panel: does regime informativeness live in the "
                "mean or in the dispersion?",
        "window": [START, END], "horizon": PRIMARY_HORIZON,
        "per_market": per, "cross_market": summary,
        "elapsed_min": round((time.time() - t0) / 60, 1),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"JSON: {OUT_JSON}  ({payload['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
