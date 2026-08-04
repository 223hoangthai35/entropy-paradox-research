"""
Plane-1 phase-space visualisation: raw GMM (unsupervised argmax) vs
hysteresis-filtered labels on VNINDEX.

Both panels share the SAME fitted GMM (k=3, full covariance,
random_state=42) — so the cluster ellipses are identical. The only
difference is how the per-bar label is derived:

  - Left  panel: argmax(P[t, :])             → raw_labels (memoryless)
  - Right panel: HysteresisGMMWrapper output → filtered_labels
                 (Schmitt-trigger state machine over the same posteriors)

Bars where the two labels disagree are highlighted in the diff readout
printed at the end, since these are the bars hysteresis "holds" against
the instantaneous argmax (single-bar flicker suppression).

Output: validation/results_v2/regime_phase_space_vnindex_raw_vs_filtered.png
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import run_full_pipeline

# ---- styling ----------------------------------------------------------
DARK_BG = "#0E1117"
COLORS = {
    "Deterministic": "#FF3B3B",   # red — low entropy, paradox-relevant
    "Transitional":  "#FFC83B",   # yellow — mid entropy
    "Stochastic":    "#3CFF6E",   # green — high entropy
}
REGIME_NAMES = ["Deterministic", "Transitional", "Stochastic"]

MARKET = "VNINDEX"
TICKER = "VNINDEX"
SOURCE = "vnstock"
# Match the canonical paper pipeline (cross_market_v2.py START = 2018-01-01,
# hysteresis_cross_market_v2.py COMMON_START = 2020-01-01). Loading from
# 2018 gives the GMM its full 504-bar SPE_Z warmup; labels are then sliced
# to >= COMMON_START so flip-rate / regime-share numbers in the figure
# match section 7 of the paper exactly (raw flip rate 15.23 /yr, filtered
# 6.53 /yr on VNINDEX).
START        = "2018-01-01"
COMMON_START = "2020-01-01"
END          = "2026-06-30"
TRADING_DAYS_PER_YEAR = 252

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(DARK_BG)
    ax.tick_params(colors="white")
    for side, spine in ax.spines.items():
        spine.set_visible(side in ("bottom", "left"))
        spine.set_color("#444")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")
    ax.grid(alpha=0.15, color="white", linestyle="-", linewidth=0.5)


def plot_panel(ax: plt.Axes, features: np.ndarray, labels: np.ndarray,
               cluster_to_semantic: dict[int, int],
               gmm_means: np.ndarray, gmm_covs: np.ndarray,
               title: str) -> None:
    style_axes(ax)
    for k, regime in enumerate(REGIME_NAMES):
        mask = labels == k
        ax.scatter(features[mask, 0], features[mask, 1],
                   c=COLORS[regime], s=10, alpha=0.55,
                   edgecolors="none", label=f"{regime} (n={int(mask.sum())})")
    # 2-sigma ellipses (≈95% confidence) per semantic regime
    for cluster_idx, semantic_k in cluster_to_semantic.items():
        regime = REGIME_NAMES[semantic_k]
        mean = gmm_means[cluster_idx]
        cov = gmm_covs[cluster_idx]
        eigvals, eigvecs = np.linalg.eigh(cov)
        order = eigvals.argsort()[::-1]
        eigvals = eigvals[order]
        eigvecs = eigvecs[:, order]
        angle = float(np.degrees(np.arctan2(eigvecs[1, 0], eigvecs[0, 0])))
        width = float(2 * 2 * np.sqrt(eigvals[0]))
        height = float(2 * 2 * np.sqrt(eigvals[1]))
        ellipse = Ellipse(
            xy=(float(mean[0]), float(mean[1])),
            width=width, height=height, angle=angle,
            edgecolor=COLORS[regime], facecolor="none",
            linewidth=1.8, linestyle="--", alpha=0.95,
        )
        ax.add_patch(ellipse)
    ax.set_xlabel("WPE (Weighted Permutation Entropy)")
    ax.set_ylabel("SPE_Z (Standardized Price Sample Entropy)")
    ax.set_title(title, fontsize=11, fontweight="bold")
    legend = ax.legend(
        facecolor=DARK_BG, edgecolor="#444",
        labelcolor="white", title="Price Regime",
        loc="upper left", fontsize=9, title_fontsize=10, framealpha=0.85,
    )
    legend.get_title().set_color("white")


def main() -> None:
    print(f"[1/3] Pipeline: {MARKET} fit window {START} -> {END}, "
          f"display window >= {COMMON_START}")
    pipe = run_full_pipeline(MARKET, TICKER, SOURCE, start=START, end=END)
    feat_full = pipe["features"]
    raw_full = pipe["raw_labels"].astype(int)
    filt_full = pipe["filtered_labels"].astype(int)
    clf = pipe["classifier"]
    gmm_means = clf.gmm.means_
    gmm_covs = clf.gmm.covariances_

    # Slice to the canonical display window (matches H3 _slice_common).
    common_mask = feat_full.index >= pd.Timestamp(COMMON_START)
    features = feat_full.values[common_mask]
    raw_labels = raw_full.values[common_mask]
    filt_labels = filt_full.values[common_mask]

    # Reproduce semantic mapping (lowest centroid-sum -> 0=Deterministic).
    combined = gmm_means.sum(axis=1)
    order = np.argsort(combined)
    cluster_to_semantic = {int(order[i]): i for i in range(clf.n_components)}

    n = len(features)
    n_diff = int((raw_labels != filt_labels).sum())
    raw_dist = np.bincount(raw_labels, minlength=3)
    filt_dist = np.bincount(filt_labels, minlength=3)
    flips_raw = int((np.diff(raw_labels) != 0).sum())
    flips_filt = int((np.diff(filt_labels) != 0).sum())
    rate_raw = flips_raw * TRADING_DAYS_PER_YEAR / n
    rate_filt = flips_filt * TRADING_DAYS_PER_YEAR / n
    print(f"      labelable bars in window: {n}")
    print(f"      raw     flips: {flips_raw} total -> {rate_raw:.2f}/yr"
          f" | n_det/n_tra/n_sto = {raw_dist[0]} / {raw_dist[1]} / {raw_dist[2]}")
    print(f"      filtered flips: {flips_filt} total -> {rate_filt:.2f}/yr"
          f" | n_det/n_tra/n_sto = {filt_dist[0]} / {filt_dist[1]} / {filt_dist[2]}")
    print(f"      labels differ on {n_diff} bars ({100*n_diff/n:.1f}%)")

    print("[2/3] Plotting")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), sharey=True)
    fig.patch.set_facecolor(DARK_BG)
    plot_panel(
        axes[0], features, raw_labels, cluster_to_semantic, gmm_means, gmm_covs,
        f"Raw GMM (unsupervised argmax per bar)\n"
        f"{flips_raw} flips total · {rate_raw:.2f}/yr",
    )
    plot_panel(
        axes[1], features, filt_labels, cluster_to_semantic, gmm_means, gmm_covs,
        f"Hysteresis-Filtered (Schmitt-trigger δ_hard=0.60, δ_soft=0.35, t_persist=8)\n"
        f"{flips_filt} flips total · {rate_filt:.2f}/yr  "
        f"({100*(1-rate_filt/rate_raw):.0f}% reduction vs raw)",
    )
    fig.suptitle(
        f"{MARKET}  Plane-1 Phase Space — Raw GMM vs Hysteresis-Filtered\n"
        f"display {COMMON_START} → {END}    n={n} bars    "
        f"labels differ on {n_diff} bars ({100*n_diff/n:.1f}%)",
        color="white", fontsize=12, fontweight="bold", y=1.0,
    )
    plt.tight_layout()
    out_path = os.path.join(
        OUTPUT_DIR, "regime_phase_space_vnindex_raw_vs_filtered.png"
    )
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"[3/3] Saved: {out_path}")


if __name__ == "__main__":
    main()
