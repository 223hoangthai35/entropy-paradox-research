"""Is the cross-market dependence in the *object being tested*, or only in returns?

`dependence_aware_inference.py` measures how dependent the panel is using the
correlation of daily returns, then permutes under nulls built from that. The
implicit step is that correlated returns imply correlated regime-informativeness
statistics. That step is an assumption, and it is the one worth checking, because
the objection to it is specific and reasonable: two markets can move together
every day and still have entirely unrelated answers to "how well does this
market's own entropy partition organize this market's own forward volatility."
Global shocks propagate through prices; they do not obviously propagate through
the quality of a within-market measurement.

So this script measures dependence in H directly. Each market's sample is cut
into non-overlapping sub-periods; a Kruskal-Wallis H is computed inside each one
from that market's own labels against its own forward volatility; and the
resulting per-market time series of H are correlated across markets on their
shared sub-periods. If those correlations are near zero while return correlations
average +0.27, then return correlation is the wrong yardstick for this panel and
the dependence adjustment built on it is too conservative.

Two controls decide whether any co-movement found is real:

  1. The same computation on **forward volatility level** per sub-period, which
     is known to co-move strongly across markets. It sets the scale for what
     "dependent" looks like in this data, so a near-zero H correlation cannot be
     dismissed as an artifact of short sub-periods.

  2. A **within-market split-half reliability**: correlation between H computed
     on alternating sub-periods of the same market. If a market's own H is not
     even stable against itself, then a low cross-market correlation says nothing
     about independence -- it says the sub-period estimator is noise. This is the
     control that decides whether the headline of this script means anything.
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

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(_VALIDATION))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from validation._features import load_ohlcv, run_full_pipeline  # noqa: E402
from validation.h2_magnitude.cross_market_v2 import compute_forward_metrics  # noqa: E402
from validation.h1_direction.h1_dml import START, END  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

R = os.path.join(_VALIDATION, "results_v2")
OUT = os.path.join(R, "panel_properties/h_comovement_check.json")
BLOCK = 126           # ~6 months of trading days
MIN_PER_GROUP = 5
MIN_SHARED = 6        # sub-periods two markets must share to be correlated


def _kw(d: pd.DataFrame) -> float:
    """Kruskal-Wallis H of forward vol across regime labels on any slice."""
    g = [v["FwdVol20d"].values for _, v in d.groupby("lab") if len(v) >= MIN_PER_GROUP]
    if len(g) < 2:
        return float("nan")
    try:
        return float(stats.kruskal(*g)[0])
    except ValueError:
        return float("nan")


def per_block_stats(m: str, cfg: dict):
    """H and mean forward vol inside each non-overlapping sub-period, plus the
    aligned label/forward-vol frame the jackknife stage recomputes H from."""
    try:
        out = run_full_pipeline(m, cfg["ticker"], cfg["source"], START, END)
        ohlcv = out["ohlcv"]
    except Exception as e:
        print(f"  [{m}] SKIP {type(e).__name__}: {e}")
        return None, None

    lab = out["filtered_labels"]
    fwd = compute_forward_metrics(ohlcv, horizon=20)
    df = pd.DataFrame({"lab": lab.astype(int).values}, index=lab.index).join(fwd, how="left")
    df = df.dropna(subset=["FwdVol20d"])
    if len(df) < 3 * BLOCK:
        print(f"  [{m}] SKIP too short ({len(df)})")
        return None, None

    rows = []
    for s in range(0, len(df) - BLOCK + 1, BLOCK):
        b = df.iloc[s:s + BLOCK]
        H = _kw(b)
        if not np.isfinite(H):
            continue
        rows.append({"end": b.index[-1], "H": H,
                     "vol": float(b["FwdVol20d"].mean())})
    if len(rows) < MIN_SHARED:
        print(f"  [{m}] SKIP only {len(rows)} usable sub-periods")
        return None, None
    print(f"  [{m}] {len(rows)} sub-periods")
    return pd.DataFrame(rows).set_index("end"), df


def pairwise(frame: pd.DataFrame, label: str) -> dict:
    C = frame.corr(method="spearman", min_periods=MIN_SHARED)
    v = C.values[np.triu_indices(len(C), 1)]
    v = v[np.isfinite(v)]
    print(f"  {label:26} mean {v.mean():+.3f}  median {np.median(v):+.3f}  "
          f"n_pairs {len(v)}  share |r|>0.5: {np.mean(np.abs(v) > 0.5):.2f}")
    return {"mean": float(v.mean()), "median": float(np.median(v)),
            "n_pairs": int(len(v)), "share_abs_gt_0.5": float(np.mean(np.abs(v) > 0.5)),
            "p05": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}


def main() -> int:
    t0 = time.time()
    print(f"Sub-period statistics, block = {BLOCK} bars\n")
    blocks, panel = {}, {}
    for cfg in MARKETS_N27:
        d, full = per_block_stats(cfg["name"], cfg)
        if d is not None:
            blocks[cfg["name"]] = d
            panel[cfg["name"]] = full

    # Align on a common calendar grid: sub-periods are dated by their last bar,
    # so round to month-end before joining, otherwise no two markets share a key.
    def grid(col):
        s = {m: d[col].groupby(d.index.to_period("Q")).mean() for m, d in blocks.items()}
        return pd.DataFrame(s)

    H_grid, V_grid = grid("H"), grid("vol")
    print(f"\n{len(blocks)} markets on a {len(H_grid)}-quarter grid\n")

    out = {
        "spec": "Cross-market dependence measured in the regime-informativeness "
                "statistic itself, against a forward-volatility benchmark and a "
                "within-market split-half reliability control.",
        "window": [START, END], "block_bars": BLOCK,
        "n_markets": len(blocks), "n_quarters": int(len(H_grid)),
    }

    print("Cross-market dependence:")
    out["H_pairwise"] = pairwise(H_grid, "regime informativeness H")
    out["vol_pairwise"] = pairwise(V_grid, "forward volatility (control)")

    # Split-half: does a market's own H agree with itself across sub-periods?
    rel = {}
    for m, d in blocks.items():
        h = d["H"].values
        if len(h) < 6:
            continue
        a, b = h[0::2], h[1::2]
        k = min(len(a), len(b))
        if k >= 3:
            rel[m] = float(stats.spearmanr(a[:k], b[:k])[0])
    rv = np.array([v for v in rel.values() if np.isfinite(v)])
    print(f"\nWithin-market split-half reliability of sub-period H:")
    print(f"  mean {rv.mean():+.3f}  median {np.median(rv):+.3f}  over {len(rv)} markets")
    print(f"  share of markets with positive self-agreement: {np.mean(rv > 0):.2f}")
    out["split_half"] = {"mean": float(rv.mean()), "median": float(np.median(rv)),
                         "n_markets": int(len(rv)),
                         "share_positive": float(np.mean(rv > 0)),
                         "per_market": rel}

    # ------------------------------------------------------------------
    # The sub-period estimator above is too noisy to answer the question --
    # a market's own H does not agree with itself across sub-periods, so its
    # near-zero correlation with other markets is uninformative. The jackknife
    # below asks the same question with an estimator that cannot have that
    # problem: H is recomputed on the FULL sample minus one quarter, so every
    # value rests on ~96% of the data. The influence of quarter q on market m is
    # H_full - H_{-q}. If global shocks drive regime informativeness commonly,
    # the influence vectors of different markets agree on which quarters mattered.
    # ------------------------------------------------------------------
    print("\nLeave-one-quarter-out jackknife influence on full-sample H:")
    infl = {}
    for m, cfg in [(c["name"], c) for c in MARKETS_N27 if c["name"] in blocks]:
        d = panel.get(m)
        if d is None:
            continue
        q = d.index.to_period("Q")
        full = _kw(d)
        if not np.isfinite(full):
            continue
        s = {}
        for qq in sorted(set(q)):
            sub = d[q != qq]
            h = _kw(sub)
            if np.isfinite(h):
                s[str(qq)] = full - h
        if len(s) >= MIN_SHARED:
            infl[m] = pd.Series(s)
    # The parallel control, and it is not optional: the same jackknife applied to
    # mean forward volatility, a quantity known to co-move. If ITS influence
    # vectors also correlate near zero, the design cannot detect dependence and
    # the H reading means nothing -- the same trap the split-half caught above.
    vinfl = {}
    for m, d in panel.items():
        if d is None or m not in infl:
            continue
        q = d.index.to_period("Q")
        full = float(d["FwdVol20d"].mean())
        vinfl[m] = pd.Series({str(qq): full - float(d[q != qq]["FwdVol20d"].mean())
                              for qq in sorted(set(q))})
    I_grid = pd.DataFrame(infl)
    V_infl = pd.DataFrame(vinfl)
    print(f"  {I_grid.shape[1]} markets on a {I_grid.shape[0]}-quarter grid")
    out["jackknife_influence"] = pairwise(I_grid, "H jackknife influence")
    out["jackknife_influence_vol_control"] = pairwise(V_infl, "forward-vol influence (control)")
    out["jackknife_influence"]["n_markets"] = int(I_grid.shape[1])
    out["jackknife_influence"]["n_quarters"] = int(I_grid.shape[0])

    out["elapsed_min"] = round((time.time() - t0) / 60, 1)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nJSON: {OUT}  ({out['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
