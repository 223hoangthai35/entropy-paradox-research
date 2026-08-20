"""
Paper v1 V4 (entropy vs simple-vol vs combined) — redo on the 8-market
panel with raw + filtered labels.

This is the §12.4 appendix of paper v2.1: an exploratory robustness
redo of `validation/entropy_vs_simple.py` (frozen at v1.0-paper, single-
market VNINDEX, raw labels only).

Three GMM models per market:
  A. Entropy  : [WPE, SPE_Z]            (the v2.1 canonical Plane-1)
  B. SimpleVol: [Rolling22, VolChange5]
  C. Combined : [WPE, SPE_Z, Rolling22]

Each model is fit with the same EntropyPhaseSpaceClassifier (k=3, full
covariance, random_state=42) and wrapped with HysteresisGMMWrapper
using the production defaults (δ_hard=0.60, δ_soft=0.35, t_persist=8).
The hysteresis parameters were CALIBRATED on VNINDEX entropy GMM only;
borrowing them for SimpleVol and Combined GMMs is disclosed in §12.5.

Statistic per (market, model, label_source):
  - Kruskal-Wallis H on forward 20-day realized vol across 3 regimes.
    Higher H = better regime discrimination of forward vol.
  - Per-regime mean vol (descriptive).

Note on regime semantics: EntropyPhaseSpaceClassifier sorts clusters by
sum of centroid means (lowest -> 0=Deterministic). For SimpleVol features
[Rolling22, VolChange5] the lowest combined value is usually the calm
regime, so the "Deterministic" label is borrowed and points the OPPOSITE
direction from entropy. KW H is invariant to label ordering — the
discrimination test is unaffected — but mean_vol_det vs mean_vol_sto
should be read as "lowest-feature-sum cluster vs highest-feature-sum
cluster", not as paradox direction.

Window: 2020-01-01 → 2026-04-17 (matches H3, post-COVID).

Outputs (validation/results_v2/):
  - entropy_vs_simple_8market.csv  : 8 × 3 × 2 = 48 rows.
  - entropy_vs_simple_8market.json : nested per-market dict.
  - entropy_vs_simple_8market.png  : 8-market × 3-model heatmap of H,
    raw vs filtered side-by-side.

Run:
  python validation/entropy_vs_simple_8market.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import kruskal
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

from validation._features import run_full_pipeline, DEFAULT_HYSTERESIS
from validation.h2_magnitude.cross_market_v2 import MARKETS, OUTPUT_DIR
from skills.ds_skill import EntropyPhaseSpaceClassifier, HysteresisGMMWrapper

START = "2020-01-01"
END   = "2026-06-30"
FWD_VOL_HORIZON = 20
RNG_SEED = 42

DET_LABEL, TRA_LABEL, STO_LABEL = 0, 1, 2
MODELS = ("Entropy", "SimpleVol", "Combined")


def forward_vol_pct(close: pd.Series, horizon: int) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    return (log_ret.shift(-1).rolling(horizon).std()
            .shift(-(horizon - 1)) * np.sqrt(252) * 100.0)


def fit_labels(features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit GMM + apply hysteresis. Returns (raw_labels, filtered_labels)."""
    clf = EntropyPhaseSpaceClassifier(n_components=3, random_state=RNG_SEED)
    raw = clf.fit_predict(features)
    wrapper = HysteresisGMMWrapper(clf, **DEFAULT_HYSTERESIS)
    filt = wrapper.transform(features)
    return raw, filt


def kw_per_model(label_arr: np.ndarray, fwd_vol_arr: np.ndarray
                 ) -> tuple[float, float, dict[int, dict]]:
    groups: dict[int, np.ndarray] = {}
    for lab in (DET_LABEL, TRA_LABEL, STO_LABEL):
        v = fwd_vol_arr[label_arr == lab]
        v = v[~np.isnan(v)]
        if len(v) >= 3:
            groups[lab] = v
    per_regime = {
        lab: {"n": int(len(v)),
              "mean": float(v.mean()) if len(v) else float("nan"),
              "median": float(np.median(v)) if len(v) else float("nan")}
        for lab, v in groups.items()
    }
    if len(groups) < 2:
        return float("nan"), float("nan"), per_regime
    H, p = kruskal(*groups.values())
    return float(H), float(p), per_regime


def process_market(spec: dict) -> tuple[list[dict], dict]:
    name = spec["name"]
    print(f"  [{name}] pipeline …")
    pipe = run_full_pipeline(
        name, spec["ticker"], spec["source"], start=START, end=END,
    )
    ohlcv = pipe["ohlcv"]
    feat_idx = pipe["features"].index

    log_ret_raw = np.log(ohlcv["Close"] / ohlcv["Close"].shift(1))
    rolling22 = log_ret_raw.rolling(22).std() * np.sqrt(252) * 100.0
    vol_change_5 = rolling22.pct_change(5)
    fwd_vol = forward_vol_pct(ohlcv["Close"].astype(float), FWD_VOL_HORIZON)

    # Model A: Entropy (reuse run_full_pipeline labels — same as H1).
    raw_A = pipe["raw_labels"].astype(int)
    filt_A = pipe["filtered_labels"].astype(int)

    # Model B: SimpleVol [Rolling22, VolChange5]. Build features aligned
    # with the same SPE_Z 504-day cutoff so all three models run on the
    # same set of bars, ensuring fair H comparison.
    feat_B_full = pd.DataFrame({
        "Rolling22":   rolling22,
        "VolChange5":  vol_change_5,
    }).reindex(feat_idx).dropna()
    raw_B_arr, filt_B_arr = fit_labels(feat_B_full.values)
    raw_B = pd.Series(raw_B_arr, index=feat_B_full.index)
    filt_B = pd.Series(filt_B_arr, index=feat_B_full.index)

    # Model C: Combined [WPE, SPE_Z, Rolling22].
    feat_C_full = pd.concat(
        [pipe["features"], rolling22.reindex(feat_idx).rename("Rolling22")],
        axis=1,
    ).dropna()
    raw_C_arr, filt_C_arr = fit_labels(feat_C_full.values)
    raw_C = pd.Series(raw_C_arr, index=feat_C_full.index)
    filt_C = pd.Series(filt_C_arr, index=feat_C_full.index)

    # Common alignment for KW: take the intersection of all label series'
    # indices and fwd_vol index.
    common = (
        raw_A.index
        .intersection(raw_B.index)
        .intersection(raw_C.index)
        .intersection(fwd_vol.dropna().index)
    )
    fwd_vol_aligned = fwd_vol.reindex(common).values

    rows: list[dict] = []
    block: dict[str, Any] = {"market": name, "category": spec["category"], "n_common": int(len(common))}
    label_table = {
        ("Entropy",   "raw"):      raw_A.reindex(common).values,
        ("Entropy",   "filtered"): filt_A.reindex(common).values,
        ("SimpleVol", "raw"):      raw_B.reindex(common).values,
        ("SimpleVol", "filtered"): filt_B.reindex(common).values,
        ("Combined",  "raw"):      raw_C.reindex(common).values,
        ("Combined",  "filtered"): filt_C.reindex(common).values,
    }
    for (model, src), lab_arr in label_table.items():
        H, p, per_regime = kw_per_model(lab_arr, fwd_vol_aligned)
        rows.append({
            "market":    name,
            "category":  spec["category"],
            "model":     model,
            "label_source": src,
            "n":         int(len(common)),
            "kw_h":      round(H, 4) if not np.isnan(H) else None,
            "kw_p":      round(p, 6) if not np.isnan(p) else None,
            "n_det":     per_regime.get(DET_LABEL, {}).get("n", 0),
            "n_tra":     per_regime.get(TRA_LABEL, {}).get("n", 0),
            "n_sto":     per_regime.get(STO_LABEL, {}).get("n", 0),
            "mean_vol_det": (
                round(per_regime.get(DET_LABEL, {}).get("mean", float("nan")), 4)
                if DET_LABEL in per_regime else None
            ),
            "mean_vol_tra": (
                round(per_regime.get(TRA_LABEL, {}).get("mean", float("nan")), 4)
                if TRA_LABEL in per_regime else None
            ),
            "mean_vol_sto": (
                round(per_regime.get(STO_LABEL, {}).get("mean", float("nan")), 4)
                if STO_LABEL in per_regime else None
            ),
        })
    block["rows"] = rows
    return rows, block


def plot_heatmaps(df: pd.DataFrame, out_path: str) -> None:
    market_order = [m["name"] for m in MARKETS]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    fig.suptitle(
        "KW H by (market × model) — forward 20d realized vol\n"
        "Higher H = stronger regime discrimination",
        fontsize=11,
    )
    for ax, src in zip(axes, ("raw", "filtered")):
        sub = df[df["label_source"] == src]
        H = (
            sub.pivot_table(index="market", columns="model", values="kw_h",
                            aggfunc="first")
               .reindex(market_order)
               .reindex(columns=list(MODELS))
        )
        im = ax.imshow(H.values, cmap="viridis", aspect="auto",
                       vmin=0, vmax=max(50, np.nanmax(H.values) if H.size else 50))
        ax.set_xticks(range(len(MODELS)))
        ax.set_xticklabels(MODELS)
        ax.set_yticks(range(len(market_order)))
        ax.set_yticklabels(market_order)
        ax.set_title(f"label_source = {src}")
        for i in range(H.shape[0]):
            for j in range(H.shape[1]):
                v = H.iat[i, j]
                if pd.notna(v):
                    ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                            color="white" if v < 30 else "black", fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.04, pad=0.04, label="KW H")
    plt.tight_layout()
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close()


def main() -> None:
    print(f"[1/3] V4 entropy-vs-simple on {len(MARKETS)} markets, window {START} → {END}")
    print(f"      models={MODELS}, fwd_vol horizon={FWD_VOL_HORIZON}d")
    all_rows: list[dict] = []
    market_blocks: list[dict] = []
    for spec in MARKETS:
        try:
            rows, blk = process_market(spec)
        except Exception as exc:
            print(f"  [{spec['name']}] FAILED: {exc!r}")
            continue
        all_rows.extend(rows)
        market_blocks.append(blk)
        print(f"  [{spec['name']}] {len(rows)} rows  "
              f"(common-aligned bars={blk['n_common']})")

    df = pd.DataFrame(all_rows)
    csv_path = os.path.join(OUTPUT_DIR, "entropy_vs_simple_8market.csv")
    df.to_csv(csv_path, index=False)
    print(f"[2/3] CSV saved: {csv_path}  ({len(df)} rows)")

    json_path = os.path.join(OUTPUT_DIR, "entropy_vs_simple_8market.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({
            "window":          f"{START} -> {END}",
            "fwd_vol_horizon": FWD_VOL_HORIZON,
            "models":          list(MODELS),
            "hysteresis":      DEFAULT_HYSTERESIS,
            "markets":         market_blocks,
        }, fh, indent=2)
    print(f"      JSON saved: {json_path}")

    png_path = os.path.join(OUTPUT_DIR, "entropy_vs_simple_8market.png")
    plot_heatmaps(df, png_path)
    print(f"[3/3] PNG saved: {png_path}")


if __name__ == "__main__":
    main()
