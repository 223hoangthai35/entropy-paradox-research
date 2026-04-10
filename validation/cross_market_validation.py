"""
Cross-Market Validation -- Financial Entropy Agent
Tests whether the Entropy Paradox (low WPE = high future volatility) generalises
beyond VNINDEX to S&P 500 and Bitcoin.

Method:
    1. Load 5 years of OHLCV for VNINDEX (vnstock), S&P 500 and Bitcoin (yfinance).
    2. Compute WPE + SPE_Z -> fit Full-Covariance GMM -> regime labels.
    3. Compute forward realised vol (20d) and forward max drawdown (10d).
    4. Kruskal-Wallis test: do regime labels discriminate forward vol?
    5. Entropy Paradox check: Deterministic mean vol > Stochastic mean vol?
    6. Drawdown hit rates at >3% / >5% / >7% by regime (lift ratio vs base rate).
    7. 2x3 subplot: boxplots + phase-space scatter per market.
    8. Summary table across all three markets.

Run: python validation/cross_market_validation.py
"""

import sys
import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # Windows: avoid Tk/Qt GUI issues
import matplotlib.pyplot as plt
from scipy.stats import kruskal

warnings.filterwarnings("ignore")

# --- Project root on path ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.data_skill import get_latest_market_data
from skills.quant_skill import (
    calc_rolling_wpe,
    calc_rolling_price_sample_entropy,
    calc_spe_z,
)
from skills.ds_skill import fit_predict_regime, REGIME_NAMES

# ==============================================================================
# CONFIG
# ==============================================================================
MARKETS = [
    {"name": "VNINDEX",  "ticker": "VNINDEX", "source": "vnstock"},
    {"name": "S&P 500",  "ticker": "^GSPC",   "source": "yfinance"},
    {"name": "Bitcoin",  "ticker": "BTC-USD",  "source": "yfinance"},
]

START_DATE = "2019-01-01"
OUTPUT_DIR = os.path.dirname(__file__)

# Immutable research constants (mirror CLAUDE.md)
WPE_M      = 3
WPE_TAU    = 1
WPE_WINDOW = 22
SPE_WINDOW = 60
SPE_M      = 2
SPE_R      = 0.2

REGIME_PALETTE = {
    "Stochastic":   "#2ecc71",
    "Transitional": "#f39c12",
    "Deterministic":"#e74c3c",
}
REGIME_ORDER = ["Stochastic", "Transitional", "Deterministic"]


# ==============================================================================
# STEP 1: LOAD DATA
# ==============================================================================
def load_market(cfg: dict) -> pd.DataFrame:
    """Load OHLCV for one market config entry."""
    name   = cfg["name"]
    ticker = cfg["ticker"]
    source = cfg["source"]

    print(f"  Loading {name} ({ticker}) via {source} from {START_DATE} ...")

    if source == "vnstock":
        df = get_latest_market_data(ticker=ticker, start_date=START_DATE)
        if df is None or df.empty:
            raise RuntimeError(f"vnstock returned empty data for {ticker}")

    elif source == "yfinance":
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("yfinance not installed. Run: pip install yfinance")

        raw = yf.download(ticker, start=START_DATE, progress=False, auto_adjust=True)
        if raw.empty:
            raise RuntimeError(f"yfinance returned empty data for {ticker}")

        # Flatten MultiIndex columns if present
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index)
        df.index.name = "Date"
        df = df.sort_index().dropna(subset=["Close"])
    else:
        raise ValueError(f"Unknown source: {source}")

    print(f"    {len(df)} rows  [{df.index[0].date()} -- {df.index[-1].date()}]")
    return df


# ==============================================================================
# STEP 2: COMPUTE ALL METRICS FOR ONE MARKET
# ==============================================================================
def compute_all(df: pd.DataFrame, market_name: str) -> pd.DataFrame:
    """Compute WPE, SPE_Z, regime labels, forward vol, forward max drawdown."""
    close = df["Close"].values
    log_rets = np.log(np.where(close[:-1] > 0, close[1:] / close[:-1], 1.0))
    log_rets = np.concatenate([[0.0], log_rets])  # length == len(df)

    # --- WPE ---
    wpe_arr, _ = calc_rolling_wpe(log_rets, m=WPE_M, tau=WPE_TAU, window=WPE_WINDOW)
    df = df.copy()
    df["WPE"] = wpe_arr

    # --- SPE_Z ---
    spe_raw = calc_rolling_price_sample_entropy(
        close, window=SPE_WINDOW, m=SPE_M, r_factor=SPE_R
    )
    df["SPE_Z"] = calc_spe_z(spe_raw)

    # --- GMM Regime Labels ---
    feat_df = df[["WPE", "SPE_Z"]].dropna()
    if len(feat_df) < 60:
        raise RuntimeError(f"{market_name}: not enough non-NaN rows for GMM ({len(feat_df)})")
    labels, _ = fit_predict_regime(feat_df.values)
    df["RegimeLabel"] = np.nan
    df.loc[feat_df.index, "RegimeLabel"] = labels
    df["RegimeName"] = df["RegimeLabel"].map(REGIME_NAMES)

    # --- Forward Realised Volatility (20d annualised) ---
    lr_series = pd.Series(log_rets, index=df.index)
    df["FwdVol20d"] = (
        lr_series.shift(-1).rolling(20).std().shift(-19) * np.sqrt(252) * 100
    )

    # --- Forward Max Drawdown (10d) ---
    close_s = pd.Series(close, index=df.index)
    rolling_max = close_s.rolling(10).max().shift(-9)
    df["FwdMaxDD10d"] = ((close_s - rolling_max) / close_s * 100).clip(upper=0).abs()

    return df


# ==============================================================================
# STEP 3: KRUSKAL-WALLIS + ENTROPY PARADOX
# ==============================================================================
def validate_regimes(df: pd.DataFrame, market_name: str) -> dict:
    """
    Returns a result dict with:
      H, p_value, paradox_holds (bool as string), det_mean, sto_mean
    """
    groups = {}
    for regime in REGIME_ORDER:
        vals = df[df["RegimeName"] == regime]["FwdVol20d"].dropna().values
        if len(vals) >= 5:
            groups[regime] = vals

    if len(groups) < 2:
        print(f"  [WARN] {market_name}: fewer than 2 populated regimes — skipping KW test.")
        return {"H": float("nan"), "p_value": float("nan"), "paradox_holds": "SKIP",
                "det_mean": float("nan"), "sto_mean": float("nan")}

    stat, p_value = kruskal(*groups.values())
    det_mean = groups.get("Deterministic", np.array([float("nan")])).mean()
    sto_mean = groups.get("Stochastic",    np.array([float("nan")])).mean()
    paradox  = det_mean > sto_mean

    print(f"  {market_name}: H={stat:.2f}  p={p_value:.4f}  "
          f"Det={det_mean:.2f}%  Sto={sto_mean:.2f}%  "
          f"Paradox={'YES' if paradox else 'NO'}")

    return {
        "H": stat, "p_value": p_value,
        "paradox_holds": "YES" if paradox else "NO",
        "det_mean": det_mean, "sto_mean": sto_mean,
    }


# ==============================================================================
# STEP 4: DRAWDOWN HIT RATES
# ==============================================================================
def validate_hitrate(df: pd.DataFrame, market_name: str) -> pd.DataFrame:
    """
    For each regime: fraction of days where forward max drawdown exceeds threshold.
    Returns a DataFrame of hit rates and lift ratios vs base rate.
    """
    thresholds = [3.0, 5.0, 7.0]
    rows = []
    base_n = df["FwdMaxDD10d"].dropna()

    for regime in REGIME_ORDER:
        sub = df[df["RegimeName"] == regime]["FwdMaxDD10d"].dropna()
        if len(sub) == 0:
            continue
        row = {"Market": market_name, "Regime": regime, "N": len(sub)}
        for thr in thresholds:
            hit  = (sub > thr).mean()
            base = (base_n > thr).mean()
            lift = hit / base if base > 0 else float("nan")
            row[f"Hit>{thr}%"] = f"{hit*100:.1f}%"
            row[f"Lift>{thr}%"] = f"{lift:.2f}x"
        rows.append(row)

    return pd.DataFrame(rows)


# ==============================================================================
# STEP 5: PLOTTING
# ==============================================================================
def plot_comparison(all_dfs: list[pd.DataFrame], market_names: list[str]) -> None:
    """2xN figure: top row = boxplots, bottom row = phase space scatter."""
    n = len(all_dfs)
    fig, axes = plt.subplots(2, n, figsize=(6 * n, 10), squeeze=False)
    fig.suptitle("Cross-Market Entropy Paradox Validation", fontsize=15, y=1.01)

    for col, (df, name) in enumerate(zip(all_dfs, market_names)):
        ax_box = axes[0, col]
        ax_sct = axes[1, col]

        # --- Boxplot: FwdVol20d by regime ---
        present = [r for r in REGIME_ORDER if r in df["RegimeName"].unique()]
        plot_data = [df[df["RegimeName"] == r]["FwdVol20d"].dropna().values for r in present]

        bp = ax_box.boxplot(plot_data, labels=present, patch_artist=True, showfliers=False)
        for patch, label in zip(bp["boxes"], present):
            patch.set_facecolor(REGIME_PALETTE.get(label, "#999999"))
            patch.set_alpha(0.75)

        ax_box.set_title(f"{name}\nFwd 20d Vol by Regime")
        ax_box.set_ylabel("Annualised Vol (%)")
        ax_box.grid(axis="y", alpha=0.3)

        # --- Scatter: WPE vs SPE_Z coloured by regime ---
        for regime in present:
            sub = df[df["RegimeName"] == regime].dropna(subset=["WPE", "SPE_Z"])
            ax_sct.scatter(
                sub["WPE"], sub["SPE_Z"],
                c=REGIME_PALETTE.get(regime, "gray"),
                label=regime, alpha=0.3, s=8,
            )
        ax_sct.set_xlabel("WPE")
        ax_sct.set_ylabel("SPE_Z")
        ax_sct.set_title(f"{name}\nEntropy Phase Space")
        ax_sct.legend(markerscale=2, fontsize=8)
        ax_sct.grid(alpha=0.2)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "cross_market_validation.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\nPlot saved: {out_path}")


# ==============================================================================
# STEP 6: SUMMARY TABLE
# ==============================================================================
def print_summary_table(results: list[dict], hitrate_dfs: list[pd.DataFrame]) -> None:
    print("\n" + "=" * 70)
    print("CROSS-MARKET VALIDATION SUMMARY")
    print("=" * 70)
    print(f"{'Market':<12} {'H-stat':>8} {'p-value':>10} {'Paradox':>9} "
          f"{'Det mean%':>10} {'Sto mean%':>10}")
    print("-" * 70)
    for r in results:
        h   = f"{r['H']:.2f}"   if not np.isnan(r['H'])        else "N/A"
        p   = f"{r['p_value']:.4f}" if not np.isnan(r['p_value']) else "N/A"
        det = f"{r['det_mean']:.2f}%" if not np.isnan(r['det_mean']) else "N/A"
        sto = f"{r['sto_mean']:.2f}%" if not np.isnan(r['sto_mean']) else "N/A"
        print(f"{r['market']:<12} {h:>8} {p:>10} {r['paradox_holds']:>9} {det:>10} {sto:>10}")

    print("\n--- Drawdown Hit Rates (forward 10-day max drawdown) ---")
    if hitrate_dfs:
        combined = pd.concat(hitrate_dfs, ignore_index=True)
        print(combined.to_string(index=False))

    print("\n--- Interpretation ---")
    for r in results:
        market = r["market"]
        if r["paradox_holds"] == "YES":
            if not np.isnan(r["p_value"]) and r["p_value"] < 0.05:
                verdict = "PASS -- Entropy Paradox holds AND regimes are statistically discriminative."
            else:
                verdict = "PARTIAL -- Paradox direction correct, but not statistically significant."
        elif r["paradox_holds"] == "SKIP":
            verdict = "SKIP -- Insufficient data or regime diversity."
        else:
            verdict = "FAIL -- Paradox does not generalise to this market (investigate further)."
        print(f"  {market}: {verdict}")
    print("=" * 70)


# ==============================================================================
# MAIN
# ==============================================================================
def run_cross_market_validation() -> None:
    print("=" * 70)
    print("CROSS-MARKET ENTROPY PARADOX VALIDATION")
    print(f"Markets: {[m['name'] for m in MARKETS]}")
    print(f"Start  : {START_DATE}")
    print("=" * 70)

    all_dfs      = []
    market_names = []
    kw_results   = []
    hitrate_dfs  = []

    for cfg in MARKETS:
        name = cfg["name"]
        print(f"\n[{name}]")
        try:
            df = load_market(cfg)
            df = compute_all(df, name)
        except Exception as e:
            print(f"  [ERROR] Could not process {name}: {e}")
            continue

        res = validate_regimes(df, name)
        res["market"] = name
        kw_results.append(res)

        hr_df = validate_hitrate(df, name)
        hitrate_dfs.append(hr_df)

        all_dfs.append(df)
        market_names.append(name)

    if len(all_dfs) >= 1:
        plot_comparison(all_dfs, market_names)

    print_summary_table(kw_results, hitrate_dfs)


if __name__ == "__main__":
    run_cross_market_validation()
