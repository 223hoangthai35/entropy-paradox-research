"""Is the cross-market ordering uniform in time, or carried by part of the window?

App J compares two analysis windows that differ by two and a half months. That
tests vendor-revision and refit sensitivity. It cannot detect whether the ordering
itself is concentrated in part of the period, because both windows are essentially
the same period.

This script asks the question App J cannot. The labels are held fixed -- one
full-sample mixture per market, exactly as the paper reports -- and only the
segment on which Kruskal-Wallis H is evaluated moves. Two independent split
designs are run so the answer does not rest on one arbitrary cut:

  * by bar fraction, scoring the last 30/40/50/60% of each market's own bars;
  * by calendar date, scoring before and after 2023-01-01, 2024-01-01, 2025-01-01.

Three artifacts could produce an apparent collapse and each is controlled.

  Power. A shorter segment gives a noisier H. Controlled by also scoring the
  EARLY segment at the same sizes: if the early segment carries the ordering on
  fewer bars than the late segment has, the collapse is not about n.

  Partition degeneracy. If a market sits in one regime through a calm period, H
  is computed on fewer groups and measures less. Controlled by recording, per
  segment, how many markets still have three usable regime groups.

  Labeling. A full-sample mixture has seen the scored bars. Controlled separately
  in causal_labeling_check.py, which fits on the first 60% and applies forward:
  causal labels retain 99% of the full-sample H and the retention does not favour
  high-participation markets, so labeling is not the channel.

  Trading-calendar heterogeneity. The twenty-seven exchanges do not share a
  calendar, and two anomalies matter. The crypto assets trade 365 days a year, so
  a bar-fraction cut spans a different calendar period for them than for the
  equity indices; and one market, TWII, carries a data gap leaving it 230 bars
  after 2024 where its peers carry 564 to 615. Both are controlled below, and
  they turn out to determine the SIGN of the late-segment estimate without
  touching the early-segment one -- which is exactly how a calendar artifact is
  told apart from a substantive result. The bar-fraction design is inherently
  calendar-misaligned for the same reason; the calendar design is not, and is the
  one to read.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

with contextlib.redirect_stdout(io.StringIO()):
    from validation._features import (build_plane1_features,
                                      fit_classifier_and_filter, load_ohlcv)
    from validation.cross_market_v2 import compute_forward_metrics
    from validation.h1_dml import END, START
    from validation.markets_n27 import MARKETS_N27

R = os.path.join(os.path.dirname(__file__), "results_v2")
OUT = os.path.join(R, "subperiod_stability.json")
SEED = 42
MIN_PER_GROUP = 5
FRACS = (0.30, 0.40, 0.50, 0.60)
DATES = ("2023-01-01", "2024-01-01", "2025-01-01")

RPS = json.load(io.open(os.path.join(R, "n27_experiment",
                                     "h2_eta_squared_n27.json"),
                        encoding="utf-8"))["rps_point_estimates"]


def kw(lab: np.ndarray, y: np.ndarray) -> tuple[float, int]:
    g = [y[lab == k] for k in np.unique(lab)]
    g = [x for x in g if len(x) >= MIN_PER_GROUP]
    if len(g) < 2:
        return float("nan"), len(g)
    try:
        return float(stats.kruskal(*g)[0]), len(g)
    except ValueError:
        return float("nan"), len(g)


def rho(H: np.ndarray, v: np.ndarray) -> dict:
    ok = np.isfinite(H)
    r, p = stats.spearmanr(H[ok], v[ok])
    return {"rho": float(r), "p": float(p), "n_markets": int(ok.sum()),
            "median_H": float(np.nanmedian(H))}


def main() -> int:
    t0 = time.time()
    data = {}
    for cfg in MARKETS_N27:
        m = cfg["name"]
        if m not in RPS:
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                ohlcv = load_ohlcv(m, cfg["ticker"], cfg["source"], START, END)
                feat = build_plane1_features(ohlcv)
                fit = fit_classifier_and_filter(feat, random_state=SEED)
            fwd = compute_forward_metrics(ohlcv, horizon=20)["FwdVol20d"].reindex(feat.index)
        except Exception as e:
            print(f"  [{m}] SKIP {type(e).__name__}")
            continue
        data[m] = (fit["raw_labels"].values, fwd.values,
                   np.isfinite(fwd.values), feat.index)

    ms = list(data)
    v = np.array([RPS[m] for m in ms])
    out = {
        "spec": "Sub-period stability of the cross-market ordering. Labels are the "
                "full-sample mixture, held fixed; only the segment on which H is "
                "evaluated moves. Two split designs, with power and partition-"
                "degeneracy controls.",
        "window": [START, END], "seed": SEED, "n_markets": len(ms),
        "by_bar_fraction": {}, "by_calendar": {},
    }

    H_all = np.array([kw(data[m][0][data[m][2]], data[m][1][data[m][2]])[0] for m in ms])
    out["full_window"] = rho(H_all, v)
    print(f"{len(ms)} markets\n")
    print(f"  full window                rho = {out['full_window']['rho']:+.3f} "
          f"(p = {out['full_window']['p']:.4f})\n")

    print(f"  {'segment':22} {'rho':>8} {'p':>8} {'median n':>9} {'3-group':>8}")
    for f in FRACS:
        for side in ("early", "late"):
            H, ns, g3 = [], [], 0
            for m in ms:
                lab, y, ok, _ = data[m]
                c = int(len(lab) * (1 - f)) if side == "late" else int(len(lab) * f)
                s = slice(c, None) if side == "late" else slice(0, c)
                h, g = kw(lab[s][ok[s]], y[s][ok[s]])
                H.append(h)
                ns.append(int(ok[s].sum()))
                g3 += (g >= 3)
            H = np.array(H)
            d = rho(H, v)
            d.update({"median_bars": float(np.median(ns)),
                      "markets_with_3_groups": int(g3)})
            out["by_bar_fraction"][f"{side}_{int(f*100)}pct"] = d
            print(f"  {side + ' ' + format(f, '.0%') + ' of bars':22} "
                  f"{d['rho']:+8.3f} {d['p']:8.4f} {d['median_bars']:9.0f} "
                  f"{g3:6}/{len(ms)}")

    print(f"\n  {'calendar segment':22} {'rho':>8} {'p':>8} {'median n':>9} {'3-group':>8}")
    for cut in DATES:
        for side in ("before", "after"):
            H, ns, g3 = [], [], 0
            for m in ms:
                lab, y, ok, idx = data[m]
                sel = (idx >= pd.Timestamp(cut)) if side == "after" else (idx < pd.Timestamp(cut))
                h, g = kw(lab[sel][ok[sel]], y[sel][ok[sel]])
                H.append(h)
                ns.append(int((sel & ok).sum()))
                g3 += (g >= 3)
            H = np.array(H)
            d = rho(H, v)
            d.update({"median_bars": float(np.median(ns)),
                      "markets_with_3_groups": int(g3)})
            out["by_calendar"][f"{side}_{cut}"] = d
            print(f"  {side + ' ' + cut:22} {d['rho']:+8.3f} {d['p']:8.4f} "
                  f"{d['median_bars']:9.0f} {g3:6}/{len(ms)}")

    # Calendar-anomaly controls on the split that matters. The naive late-segment
    # estimate carries a negative sign that these subsets remove entirely, while
    # the early-segment estimate does not move at all.
    CRY = {"BTC", "ETH", "BNB"}
    GAPPED = {"TWII"}
    print(f"\n  {'calendar-anomaly control (2024 cut)':34} {'n':>3} "
          f"{'late rho':>9} {'p':>8} {'early rho':>10} {'p':>8}")
    out["calendar_anomaly_control"] = {}
    for lab, drop in (("all markets", set()), ("drop gapped (TWII)", GAPPED),
                      ("drop crypto (365-day calendar)", CRY),
                      ("drop both", GAPPED | CRY)):
        S = [m for m in ms if m not in drop]
        vv = np.array([RPS[m] for m in S])
        He, Hl = [], []
        for m in S:
            lab2, y, ok, idx = data[m]
            early = (idx < pd.Timestamp("2024-01-01")) & ok
            late = (idx >= pd.Timestamp("2024-01-01")) & ok
            He.append(kw(lab2[early], y[early])[0])
            Hl.append(kw(lab2[late], y[late])[0])
        He, Hl = np.array(He), np.array(Hl)
        g = np.isfinite(He) & np.isfinite(Hl)
        re_, pe = stats.spearmanr(He[g], vv[g])
        rl, pl = stats.spearmanr(Hl[g], vv[g])
        out["calendar_anomaly_control"][lab] = {
            "n_markets": int(g.sum()),
            "late": {"rho": float(rl), "p": float(pl)},
            "early": {"rho": float(re_), "p": float(pe)}}
        print(f"  {lab:34} {g.sum():3} {rl:+9.3f} {pl:8.4f} {re_:+10.3f} {pe:8.4f}")

    out["elapsed_min"] = round((time.time() - t0) / 60, 1)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nJSON: {OUT}  ({out['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
