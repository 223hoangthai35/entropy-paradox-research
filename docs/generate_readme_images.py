"""
Generate README illustration images from live VNINDEX data.
Saves to docs/images/:
  - market_structure.png    : VNIndex price + regime background + WPE subplot
  - price_phase_space.png   : WPE vs SPE_Z scatter + GMM ellipses
  - volume_phase_space.png  : Shannon vs SampEn scatter + GMM ellipses
"""

import sys, os, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Ellipse
import matplotlib.transforms as transforms

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.data_skill import get_latest_market_data
from skills.quant_skill import (
    calc_rolling_wpe, calc_rolling_price_sample_entropy, calc_spe_z,
    calc_rolling_volume_entropy,
)
from skills.ds_skill import (
    fit_predict_regime, fit_predict_volume_regime, REGIME_NAMES,
)

OUT = os.path.join(os.path.dirname(__file__), "images")
DARK_BG  = "#0E1117"
DARK_AX  = "#161B22"
GRID_COL = "rgba(255,255,255,0.05)"

# ── palette ───────────────────────────────────────────────────────────────────
PRICE_PAL = {"Deterministic": "#FF3131", "Transitional": "#FFD700", "Stochastic": "#00FF41"}
VOL_PAL   = {"Consensus Flow": "#00BFFF", "Dispersed Flow": "#BA55D3", "Erratic/Noisy Flow": "#FF6347"}


def style_ax(ax, dark=DARK_AX):
    ax.set_facecolor(dark)
    ax.tick_params(colors="#AAAAAA", labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333")
    ax.xaxis.label.set_color("#AAAAAA")
    ax.yaxis.label.set_color("#AAAAAA")
    ax.title.set_color("#00FF41")
    ax.grid(color="#333", linewidth=0.4, alpha=0.6)


def draw_ellipse(ax, mean, cov, color, n_std=2.0):
    """Draw 95% confidence ellipse from GMM component covariance."""
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    order = eigenvalues.argsort()[::-1]
    eigenvalues, eigenvectors = eigenvalues[order], eigenvectors[:, order]
    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
    w = 2 * n_std * np.sqrt(eigenvalues[0])
    h = 2 * n_std * np.sqrt(eigenvalues[1])
    ellipse = Ellipse(
        xy=mean, width=w, height=h, angle=angle,
        edgecolor=color, facecolor="none",
        linewidth=1.5, linestyle="--", alpha=0.8, zorder=5
    )
    ax.add_patch(ellipse)


# ══════════════════════════════════════════════════════════════════════════════
def load_and_compute():
    print("[1/4] Loading VNINDEX data ...")
    df = get_latest_market_data(ticker="VNINDEX", start_date="2020-01-01")
    df = df.sort_index()
    print(f"      {len(df)} days")

    print("[2/4] Computing entropy features ...")
    log_rets = np.log(df["Close"] / df["Close"].shift(1)).fillna(0).values
    wpe_arr, _ = calc_rolling_wpe(log_rets, m=3, tau=1, window=22)
    df["WPE"] = wpe_arr

    spe_raw = calc_rolling_price_sample_entropy(df["Close"].values, window=60, m=2, r_factor=0.2)
    df["SPE_Z"] = calc_spe_z(spe_raw)
    df["SMA20"]  = df["Close"].rolling(20).mean()

    _vol_global_z, _vol_rolling_z, vol_shannon, vol_sampen = calc_rolling_volume_entropy(
        df["Volume"].values, window=60
    )
    df["Vol_Shannon"] = vol_shannon
    df["Vol_SampEn"]  = vol_sampen

    print("[3/4] Fitting GMM regimes ...")
    feat_p = df[["WPE", "SPE_Z"]].dropna()
    labels_p, clf_p = fit_predict_regime(feat_p.values)
    df.loc[feat_p.index, "RegimeName"] = pd.array(labels_p).map(
        lambda x: REGIME_NAMES.get(x, "?"))

    feat_v = df[["Vol_Shannon", "Vol_SampEn"]].dropna()
    labels_v, clf_v = fit_predict_volume_regime(feat_v.values)
    from skills.ds_skill import VOLUME_REGIME_NAMES
    df.loc[feat_v.index, "VolRegimeName"] = pd.array(labels_v).map(
        lambda x: VOLUME_REGIME_NAMES.get(x, "?"))

    return df, clf_p, clf_v


# ══════════════════════════════════════════════════════════════════════════════
def plot_market_structure(df: pd.DataFrame):
    print("[4a] Plotting market_structure.png ...")
    fig, axes = plt.subplots(
        2, 1, figsize=(16, 6), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.04}
    )
    fig.patch.set_facecolor(DARK_BG)
    for ax in axes:
        style_ax(ax)

    regime_bg = {"Deterministic": "#5c0000", "Transitional": "#3d3000", "Stochastic": "#003d00"}

    # shade regime bands
    plot_df = df.dropna(subset=["RegimeName"])
    prev_r, x0 = None, plot_df.index[0]
    for idx, row in plot_df.iterrows():
        r = row["RegimeName"]
        if r != prev_r:
            if prev_r is not None:
                for ax in axes:
                    ax.axvspan(x0, idx, facecolor=regime_bg.get(prev_r, "#111"),
                               alpha=0.55, linewidth=0)
            x0, prev_r = idx, r
    if prev_r:
        for ax in axes:
            ax.axvspan(x0, plot_df.index[-1], facecolor=regime_bg.get(prev_r, "#111"),
                       alpha=0.55, linewidth=0)

    # price + SMA20
    axes[0].plot(df.index, df["Close"], color="#FFFFFF", linewidth=0.9,
                 alpha=0.9, label="VNIndex")
    axes[0].plot(df.index, df["SMA20"], color="#FFD700", linewidth=1.0,
                 linestyle="--", alpha=0.7, label="SMA20")
    axes[0].set_ylabel("VNIndex Price")
    axes[0].set_title("VNIndex Structure State (Full GMM Regime)", pad=8, fontsize=12)

    # custom legend
    handles = [
        plt.Line2D([0], [0], color="#FFFFFF", lw=1.2, label="VNIndex"),
        plt.Line2D([0], [0], color="#FFD700", lw=1, ls="--", label="SMA20"),
        plt.Line2D([0], [0], color="#FF6347", lw=1.5, label="WPE (Entropy)"),
        mpatches.Patch(facecolor="#3d9c3d", label="Stochastic (Normal Market)"),
        mpatches.Patch(facecolor="#9c8a00", label="Transitional (Mixed Structure)"),
        mpatches.Patch(facecolor="#9c0000", label="Deterministic (High Coordination)"),
    ]
    axes[0].legend(handles=handles, loc="upper left", fontsize=8,
                   facecolor="#1a1a1a", labelcolor="white", framealpha=0.85,
                   ncol=3)

    # WPE subplot
    axes[1].plot(df.index, df["WPE"], color="#FF6347", linewidth=0.8)
    axes[1].set_ylabel("WPE Entropy")
    axes[1].set_ylim(0.3, 1.05)

    plt.tight_layout()
    path = os.path.join(OUT, "market_structure.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"      Saved: {path}")


# ══════════════════════════════════════════════════════════════════════════════
def plot_price_phase_space(df: pd.DataFrame, clf):
    print("[4b] Plotting price_phase_space.png ...")
    feat = df[["WPE", "SPE_Z", "RegimeName"]].dropna()

    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor(DARK_BG)
    style_ax(ax)

    for regime, color in PRICE_PAL.items():
        sub = feat[feat["RegimeName"] == regime]
        ax.scatter(sub["WPE"], sub["SPE_Z"], c=color, s=8, alpha=0.45,
                   label=regime, zorder=3)

    # GMM ellipses
    for i in range(clf.gmm.n_components):
        sem_label = clf._cluster_to_regime.get(i, i)
        regime_name = REGIME_NAMES.get(sem_label, "?")
        color = PRICE_PAL.get(regime_name, "#FFFFFF")
        mean = clf.gmm.means_[i]
        cov  = clf.gmm.covariances_[i]
        draw_ellipse(ax, mean, cov, color)

    ax.set_xlabel("WPE (Weighted Permutation Entropy)", fontsize=11)
    ax.set_ylabel("SPE_Z (Standardized Price Sample Entropy)", fontsize=11)
    ax.set_title("Price Regime (Raw Full GMM — WPE × SPE_Z Phase Space)", fontsize=12, pad=10)
    ax.legend(title="Price Regime", facecolor="#1a1a1a", labelcolor="white",
              title_fontsize=9, fontsize=9, framealpha=0.85)

    plt.tight_layout()
    path = os.path.join(OUT, "price_phase_space.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"      Saved: {path}")


# ══════════════════════════════════════════════════════════════════════════════
def plot_volume_phase_space(df: pd.DataFrame, clf_v):
    print("[4c] Plotting volume_phase_space.png ...")
    from skills.ds_skill import VOLUME_REGIME_NAMES
    feat = df[["Vol_Shannon", "Vol_SampEn", "VolRegimeName"]].dropna()

    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor(DARK_BG)
    style_ax(ax)

    for regime, color in VOL_PAL.items():
        sub = feat[feat["VolRegimeName"] == regime]
        ax.scatter(sub["Vol_Shannon"], sub["Vol_SampEn"], c=color, s=8,
                   alpha=0.45, label=regime, zorder=3)

    # GMM ellipses
    for i in range(clf_v.gmm.n_components):
        sem_label = clf_v._cluster_to_regime.get(i, i)
        regime_name = VOLUME_REGIME_NAMES.get(sem_label, "?")
        color = VOL_PAL.get(regime_name, "#FFFFFF")
        mean = clf_v.gmm.means_[i]
        cov  = clf_v.gmm.covariances_[i]
        draw_ellipse(ax, mean, cov, color)

    ax.set_xlabel("Shannon Entropy (Concentration)", fontsize=11)
    ax.set_ylabel("Sample Entropy (Impulse Regularity)", fontsize=11)
    ax.set_title("Volume Regime (Raw Full GMM — Shannon × SampEn Phase Space)", fontsize=12, pad=10)
    ax.legend(title="Volume Regime", facecolor="#1a1a1a", labelcolor="white",
              title_fontsize=9, fontsize=9, framealpha=0.85)

    plt.tight_layout()
    path = os.path.join(OUT, "volume_phase_space.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"      Saved: {path}")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    df, clf_p, clf_v = load_and_compute()
    plot_market_structure(df)
    plot_price_phase_space(df, clf_p)
    plot_volume_phase_space(df, clf_v)
    print("\nDone. All 3 images saved to docs/images/")
