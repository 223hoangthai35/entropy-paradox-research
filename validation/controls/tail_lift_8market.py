"""
Paper v1 V3 (tail-risk Lift on drawdowns) — redo on the 8-market panel
under v2.1's hysteresis-filtered labels and a per-market adaptive
threshold.

This is the §12.3 appendix of paper v2.1: an exploratory robustness
redo of the original `validation/risk_alert_hitrate.py` (frozen at
v1.0-paper, single-market VNINDEX, fixed thresholds 3% / 5% / 7%).

Design choices that differ from v1 V3:

  - Panel: 8 markets (VNINDEX, BVB, KOSPI, NIFTY, SPX, FTSE, NIKKEI,
    BTC) — same as cross_market_v2.py / hysteresis_cross_market_v2.py.

  - Labels: BOTH `raw_labels` and `filtered_labels` reported side-by-
    side so the reader sees how hysteresis affects the Lift signal.

  - Thresholds: per-market quantiles of that market's own forward-DD
    distribution at q ∈ {0.90, 0.95, 0.99}, computed independently of
    regime. This makes Lift comparable across markets with very
    different absolute drawdown levels (BTC vs FTSE).

  - Lift = P(DD ≥ thr | Deterministic) / P(DD ≥ thr | Stochastic).
    Returns inf if denominator is zero but numerator > 0; NaN if both
    zero; reports `n/a` when n_sto < 3 to avoid divide-by-near-zero.

  - 95% CI via circular block bootstrap (block=20, n_boot=2000) on
    the (label, fwd_dd) pair — same machinery as H1 / H3.

Window: 2020-01-01 → 2026-04-17 (matches H3, post-COVID).

Outputs (validation/results_v2/):
  - tail_lift_8market.csv  : 8 × 2 × 3 × 3 = 144 rows.
  - tail_lift_8market.json : nested per-market dict with thresholds.
  - tail_lift_8market.png  : 8-market grid of Lift bars at h=10d.

Run:
  python validation/tail_lift_8market.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from typing import Any

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from validation._features import run_full_pipeline
from validation.h2_magnitude.cross_market_v2 import MARKETS, OUTPUT_DIR

START   = "2020-01-01"
END     = "2026-06-30"
HORIZONS = [5, 10, 20]
QUANTILES = [0.90, 0.95, 0.99]
BLOCK    = 20
N_BOOT   = 2000
RNG_SEED = 42

DET_LABEL = 0   # Deterministic
STO_LABEL = 2   # Stochastic
MIN_N_SUBGROUP = 3   # below this, report n/a


def forward_max_dd(close: pd.Series, horizon: int) -> pd.Series:
    """Max drawdown over the next `horizon` bars, in absolute %."""
    future_min = close.shift(-1).rolling(horizon).min().shift(-(horizon - 1))
    pct = (future_min / close - 1.0) * 100.0
    return pct.clip(upper=0.0).abs()


def lift_one(label_arr: np.ndarray, dd_arr: np.ndarray, thr: float
             ) -> tuple[float, int, int, float, float]:
    det_mask = label_arr == DET_LABEL
    sto_mask = label_arr == STO_LABEL
    n_det = int(det_mask.sum())
    n_sto = int(sto_mask.sum())
    if n_det == 0 or n_sto == 0:
        return float("nan"), n_det, n_sto, float("nan"), float("nan")
    p_det = float((dd_arr[det_mask] >= thr).mean())
    p_sto = float((dd_arr[sto_mask] >= thr).mean())
    if p_sto > 0:
        lift = p_det / p_sto
    elif p_det > 0:
        lift = float("inf")
    else:
        lift = float("nan")
    return lift, n_det, n_sto, p_det, p_sto


def circular_block_indices(n: int, block: int, n_boot: int,
                           rng: np.random.Generator) -> np.ndarray:
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    offsets = np.arange(block)[None, None, :]
    idx = (starts[:, :, None] + offsets) % n
    return idx.reshape(n_boot, -1)[:, :n]


def lift_bootstrap_ci(label_arr: np.ndarray, dd_arr: np.ndarray, thr: float,
                      block: int, n_boot: int, rng: np.random.Generator,
                      ) -> tuple[float, float]:
    n = len(label_arr)
    idx_mat = circular_block_indices(n, block, n_boot, rng)
    boot = np.empty(n_boot)
    for b in range(n_boot):
        idx = idx_mat[b]
        l = label_arr[idx]
        d = dd_arr[idx]
        n_det = int((l == DET_LABEL).sum())
        n_sto = int((l == STO_LABEL).sum())
        if n_det < MIN_N_SUBGROUP or n_sto < MIN_N_SUBGROUP:
            boot[b] = np.nan
            continue
        p_d = (d[l == DET_LABEL] >= thr).mean()
        p_s = (d[l == STO_LABEL] >= thr).mean()
        if p_s > 0:
            boot[b] = p_d / p_s
        elif p_d > 0:
            boot[b] = np.inf
        else:
            boot[b] = np.nan
    finite = boot[np.isfinite(boot)]
    if len(finite) < 50:
        return float("nan"), float("nan")
    return (float(np.percentile(finite, 2.5)),
            float(np.percentile(finite, 97.5)))


def process_market(spec: dict, rng: np.random.Generator) -> tuple[list[dict], dict]:
    name = spec["name"]
    print(f"  [{name}] loading + pipeline …")
    pipe = run_full_pipeline(
        name, spec["ticker"], spec["source"], start=START, end=END,
    )
    ohlcv = pipe["ohlcv"]
    raw_labels = pipe["raw_labels"]        # indexed by features.index
    filt_labels = pipe["filtered_labels"]
    close = ohlcv["Close"].astype(float)

    rows: list[dict] = []
    market_block: dict[str, Any] = {"market": name, "category": spec["category"]}
    for h in HORIZONS:
        fwd_dd = forward_max_dd(close, h)
        # Align fwd_dd with the labels (which start later due to SPE_Z 504d).
        df = pd.DataFrame({
            "fwd_dd":   fwd_dd,
            "raw":      raw_labels.reindex(close.index),
            "filtered": filt_labels.reindex(close.index),
        }).dropna(subset=["fwd_dd", "raw", "filtered"])
        if df.empty:
            continue
        thresholds = {q: float(df["fwd_dd"].quantile(q)) for q in QUANTILES}
        market_block.setdefault("thresholds", {})[f"h={h}"] = thresholds
        for q in QUANTILES:
            thr = thresholds[q]
            for label_src in ("raw", "filtered"):
                lab = df[label_src].astype(int).values
                dd = df["fwd_dd"].values
                lift, n_det, n_sto, p_det, p_sto = lift_one(lab, dd, thr)
                if n_det >= MIN_N_SUBGROUP and n_sto >= MIN_N_SUBGROUP:
                    ci_lo, ci_hi = lift_bootstrap_ci(
                        lab, dd, thr, BLOCK, N_BOOT, rng,
                    )
                else:
                    ci_lo, ci_hi = float("nan"), float("nan")
                rows.append({
                    "market":          name,
                    "category":        spec["category"],
                    "label_source":    label_src,
                    "horizon_d":       h,
                    "percentile_q":    q,
                    "threshold_dd_pct": round(thr, 4),
                    "n_det":           n_det,
                    "n_sto":           n_sto,
                    "p_dd_det":        round(p_det, 6) if not np.isnan(p_det) else None,
                    "p_dd_sto":        round(p_sto, 6) if not np.isnan(p_sto) else None,
                    "lift_ratio":      round(lift, 4) if np.isfinite(lift) else (
                        "inf" if np.isinf(lift) else None
                    ),
                    "lift_ci_lo":      round(ci_lo, 4) if not np.isnan(ci_lo) else None,
                    "lift_ci_hi":      round(ci_hi, 4) if not np.isnan(ci_hi) else None,
                })
    return rows, market_block


def plot_grid(df: pd.DataFrame, out_path: str) -> None:
    """8-market grid of Lift at h=10d, raw vs filtered side-by-side."""
    sub = df[df["horizon_d"] == 10].copy()
    sub["lift_ratio"] = pd.to_numeric(sub["lift_ratio"], errors="coerce")

    market_order = [m["name"] for m in MARKETS]
    fig, axes = plt.subplots(2, 4, figsize=(16, 8), sharey=True)
    fig.suptitle(
        "Tail-risk Lift by regime — h=10d, per-market q-quantile thresholds\n"
        "(Lift = P(DD ≥ thr | Deterministic) / P(DD ≥ thr | Stochastic))",
        fontsize=11,
    )
    for i, name in enumerate(market_order):
        ax = axes[i // 4, i % 4]
        m = sub[sub["market"] == name]
        if m.empty:
            ax.set_title(f"{name} — no data")
            continue
        x = np.arange(len(QUANTILES))
        width = 0.35
        raw_lifts = [
            m[(m["label_source"] == "raw") & (m["percentile_q"] == q)]["lift_ratio"].iloc[0]
            if not m[(m["label_source"] == "raw") & (m["percentile_q"] == q)].empty
            else np.nan
            for q in QUANTILES
        ]
        filt_lifts = [
            m[(m["label_source"] == "filtered") & (m["percentile_q"] == q)]["lift_ratio"].iloc[0]
            if not m[(m["label_source"] == "filtered") & (m["percentile_q"] == q)].empty
            else np.nan
            for q in QUANTILES
        ]
        ax.bar(x - width/2, raw_lifts, width, label="raw", color="#7f8c8d", alpha=0.9)
        ax.bar(x + width/2, filt_lifts, width, label="filtered", color="#e74c3c", alpha=0.9)
        ax.axhline(1.0, color="#444", linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_title(f"{name} ({m['category'].iloc[0]})")
        ax.set_xticks(x)
        ax.set_xticklabels([f"q={q:.2f}" for q in QUANTILES])
        if i % 4 == 0:
            ax.set_ylabel("Lift ratio (Det/Sto)")
        if i == 0:
            ax.legend(fontsize=9)
        ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close()


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)
    print(f"[1/3] Tail-Lift on {len(MARKETS)} markets, window {START} → {END}")
    print(f"      horizons={HORIZONS}, quantiles={QUANTILES}, n_boot={N_BOOT}")
    all_rows: list[dict] = []
    market_blocks: list[dict] = []
    for spec in MARKETS:
        try:
            rows, blk = process_market(spec, rng)
        except Exception as exc:
            print(f"  [{spec['name']}] FAILED: {exc!r}")
            continue
        all_rows.extend(rows)
        market_blocks.append(blk)
        print(f"  [{spec['name']}] {len(rows)} rows")

    df = pd.DataFrame(all_rows)
    csv_path = os.path.join(OUTPUT_DIR, "controls/tail_lift_8market.csv")
    df.to_csv(csv_path, index=False)
    print(f"[2/3] CSV saved: {csv_path}  ({len(df)} rows)")

    json_path = os.path.join(OUTPUT_DIR, "controls/tail_lift_8market.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "window": f"{START} -> {END}",
                "horizons": HORIZONS,
                "quantiles": QUANTILES,
                "block": BLOCK,
                "n_boot": N_BOOT,
                "markets": market_blocks,
            },
            fh, indent=2,
        )
    print(f"      JSON saved: {json_path}")

    png_path = os.path.join(OUTPUT_DIR, "controls/tail_lift_8market.png")
    plot_grid(df, png_path)
    print(f"[3/3] PNG saved: {png_path}")


if __name__ == "__main__":
    main()
