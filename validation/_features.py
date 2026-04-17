"""
Shared feature pipeline for Case A validation (T1, T2, T3).

This is a SCIENTIFIC requirement, not just a refactor: every Case A test must
operate on identical feature definitions to make cross-test comparisons valid.
The recipe mirrors the production hysteresis pipeline used by the dashboard
and `scripts/calibrate_hysteresis.py`:

    log_returns = log(Close[t] / Close[t-1])
    WPE         = rolling weighted permutation entropy (m=3, tau=1, window=22)
    SampEn      = rolling sample entropy on price (window=60)
    SPE_Z       = rolling-Z of SampEn (window=504)            <-- NOT global

Provides two market loaders so T2 cross-market can fetch SPX and BTC alongside
the VNINDEX vnstock path.
"""
from __future__ import annotations

import os
import sys
from typing import Iterable, List

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.data_skill import get_latest_market_data
from skills.quant_skill import (
    calc_rolling_wpe,
    calc_rolling_price_sample_entropy,
    cal_spe_z_rolling,
)
from skills.ds_skill import (
    EntropyPhaseSpaceClassifier,
    HysteresisGMMWrapper,
    HYSTERESIS_DELTA_HARD,
    HYSTERESIS_DELTA_SOFT,
    HYSTERESIS_T_PERSIST,
)

# Pinned hyperparameters — must match the production pipeline.
WPE_M:        int = 3
WPE_TAU:      int = 1
WPE_WINDOW:   int = 22
SAMPEN_WIN:   int = 60
SPE_Z_WIN:    int = 504
TRADING_DAYS: int = 252

DEFAULT_HYSTERESIS = dict(
    delta_hard=HYSTERESIS_DELTA_HARD,
    delta_soft=HYSTERESIS_DELTA_SOFT,
    t_persist=HYSTERESIS_T_PERSIST,
)


# ==============================================================================
# MARKET DATA LOADERS
# ==============================================================================
def load_ohlcv(
    market: str,
    ticker: str,
    source: str,
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """
    Fetch OHLCV for one market. `source` in {"vnstock", "yfinance"}.
    Returns DataFrame with DatetimeIndex and at least a "Close" column.
    """
    if source == "vnstock":
        df = get_latest_market_data(ticker=ticker, start_date=start, end_date=end)
        if df is None or df.empty:
            raise RuntimeError(f"vnstock returned empty data for {ticker}")
    elif source == "yfinance":
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ImportError(
                "yfinance not installed. Run: pip install yfinance"
            ) from exc
        raw = yf.download(
            ticker, start=start, end=end, progress=False, auto_adjust=True
        )
        if raw.empty:
            raise RuntimeError(f"yfinance returned empty data for {ticker}")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index)
        df.index.name = "Date"
        df = df.sort_index().dropna(subset=["Close"])
    else:
        raise ValueError(f"Unknown source: {source!r}")

    if end is not None:
        df = df[df.index <= pd.Timestamp(end)]
    df = df[df.index >= pd.Timestamp(start)]
    return df


# ==============================================================================
# FEATURE PIPELINE
# ==============================================================================
def build_plane1_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the Plane-1 feature matrix [WPE, SPE_Z] used by the hysteresis
    classifier in production. Mirrors `_build_features` in
    `scripts/calibrate_hysteresis.py` exactly.
    """
    log_returns = np.log(df["Close"] / df["Close"].shift(1)).values
    wpe, _ = calc_rolling_wpe(
        log_returns, m=WPE_M, tau=WPE_TAU, window=WPE_WINDOW
    )
    sampen = calc_rolling_price_sample_entropy(
        df["Close"].values, window=SAMPEN_WIN
    )
    spe_z = cal_spe_z_rolling(sampen, window=SPE_Z_WIN)
    feat = pd.DataFrame(
        {"WPE": wpe, "SPE_Z": spe_z}, index=df.index
    ).dropna()
    return feat


# ==============================================================================
# REGIME-FLIP HELPERS
# ==============================================================================
def fit_classifier_and_filter(
    feat: pd.DataFrame,
    hysteresis_kwargs: dict | None = None,
    random_state: int = 42,
) -> dict:
    """
    Fit Plane-1 GMM on the supplied feature matrix and apply the hysteresis
    post-filter. Returns a dict with raw + filtered labels (as pd.Series
    indexed by `feat.index`) plus the underlying classifier and wrapper for
    downstream inspection.
    """
    hysteresis_kwargs = {**DEFAULT_HYSTERESIS, **(hysteresis_kwargs or {})}

    clf = EntropyPhaseSpaceClassifier(n_components=3, random_state=random_state)
    raw_labels = clf.fit_predict(feat.values)

    wrapper = HysteresisGMMWrapper(clf, **hysteresis_kwargs)
    filt_labels = wrapper.transform(feat.values)

    return {
        "classifier": clf,
        "wrapper": wrapper,
        "raw_labels": pd.Series(raw_labels, index=feat.index, name="raw"),
        "filtered_labels": pd.Series(
            filt_labels, index=feat.index, name="filtered"
        ),
        "hysteresis_kwargs": hysteresis_kwargs,
    }


def flip_dates(labels: pd.Series) -> pd.DatetimeIndex:
    """Return the timestamps where `labels` changes from the prior bar."""
    arr = labels.astype(int).values
    if len(arr) < 2:
        return pd.DatetimeIndex([])
    changed = np.flatnonzero(np.diff(arr) != 0) + 1   # index of the new label
    return labels.index[changed]


def flip_rate_per_year(labels: pd.Series) -> float:
    """Annualized flip count assuming 252 trading days per year."""
    n = len(labels)
    if n < 2:
        return 0.0
    flips = int((np.diff(labels.astype(int).values) != 0).sum())
    return flips * TRADING_DAYS / n


# ==============================================================================
# CONVENIENCE: END-TO-END FOR ONE MARKET
# ==============================================================================
def run_full_pipeline(
    market: str,
    ticker: str,
    source: str,
    start: str,
    end: str | None = None,
    hysteresis_kwargs: dict | None = None,
    random_state: int = 42,
) -> dict:
    """
    Load OHLCV -> build Plane-1 features -> fit GMM -> apply hysteresis.
    Returns the same dict as `fit_classifier_and_filter` plus the OHLCV
    DataFrame and the feature matrix.
    """
    df = load_ohlcv(market, ticker, source, start, end)
    feat = build_plane1_features(df)
    if len(feat) < SPE_Z_WIN:
        raise RuntimeError(
            f"{market}: only {len(feat)} bars after rolling SPE_Z; "
            f"need >= {SPE_Z_WIN}."
        )
    out = fit_classifier_and_filter(feat, hysteresis_kwargs, random_state)
    out["ohlcv"] = df
    out["features"] = feat
    out["market"] = market
    out["ticker"] = ticker
    out["start"] = start
    out["end"] = end
    return out


# ==============================================================================
# SMOKE TEST
# ==============================================================================
if __name__ == "__main__":
    print("[validation/_features] smoke test on VNINDEX 2020-01-01 ->")
    out = run_full_pipeline(
        market="VNINDEX",
        ticker="VNINDEX",
        source="vnstock",
        start="2020-01-01",
    )
    raw_fpy = flip_rate_per_year(out["raw_labels"])
    filt_fpy = flip_rate_per_year(out["filtered_labels"])
    print(f"  bars         : {len(out['features'])}")
    print(f"  raw flips/yr : {raw_fpy:.2f}")
    print(f"  filt flips/yr: {filt_fpy:.2f}")
    print(f"  filt flips n : {len(flip_dates(out['filtered_labels']))}")
