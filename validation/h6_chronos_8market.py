"""H6 — Foundation-model head-to-head: Chronos zero-shot embeddings vs. entropy
features (WPE + SPE_Z) on the eight-market panel.

Implements the App H pre-committed protocol of `02_AnonymizedManuscript_v3_4.md`:
  for each market in the canonical 8-market panel, extract Chronos-T5-small
  encoder embeddings on rolling 22-day log-return windows, project to 2D via
  PCA (matching the (WPE, SPE_Z) plane dimensionality), feed through the same
  GMM K=3 + Schmitt-trigger (delta_hard=0.60, delta_soft=0.35, t_persist=8)
  pipeline used by the entropy baseline, and compute the same forward 20-day
  Kruskal-Wallis H statistic.

Comparison axis:
  - H_entropy : KW H statistic from entropy-feature pipeline (existing baseline,
                already cached in cross_market_summary_v2.csv).
  - H_chronos : KW H statistic from Chronos-feature pipeline.

A dual entry under both raw GMM labels and filtered Schmitt-trigger labels is
reported, mirroring the dual-track convention of the paper. Cross-market
Spearman correlation between H_chronos and (a) MSCI tier, (b) all-P1 RPS
reference is also computed for direct comparison with the §4.2.2 / Table 3
entropy baseline.

Model: amazon/chronos-t5-small (46M params, 512-dim encoder hidden state).

Run:
    python validation/h6_chronos_8market.py

Output:
    validation/results_v2/h6_chronos_8market.json
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from scipy.stats import kruskal, spearmanr
from sklearn.decomposition import PCA

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results_v2"
RESULTS_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(HERE.parent))
from validation._features import (  # noqa: E402
    SPE_Z_WIN,
    WPE_WINDOW,
    build_plane1_features,
    fit_classifier_and_filter,
    flip_rate_per_year,
    load_ohlcv,
)
from skills.ds_skill import REGIME_NAMES  # noqa: E402

# ==============================================================================
# PANEL (matches validation/cross_market_v2.py)
# ==============================================================================
MARKETS: list[dict[str, Any]] = [
    {"name": "VNINDEX", "ticker": "VNINDEX", "source": "vnstock",  "category": "Frontier",  "tier": 4, "rps": 0.90},
    {"name": "BVB",     "ticker": "BVB.RO",  "source": "yfinance", "category": "Frontier",  "tier": 4, "rps": 0.225},
    {"name": "KOSPI",   "ticker": "^KS11",   "source": "yfinance", "category": "Emerging",  "tier": 3, "rps": 0.45},
    {"name": "NIFTY",   "ticker": "^NSEI",   "source": "yfinance", "category": "Emerging",  "tier": 3, "rps": 0.40},
    {"name": "SPX",     "ticker": "^GSPC",   "source": "yfinance", "category": "Developed", "tier": 1, "rps": 0.275},
    {"name": "FTSE",    "ticker": "^FTSE",   "source": "yfinance", "category": "Developed", "tier": 1, "rps": 0.20},
    {"name": "NIKKEI",  "ticker": "^N225",   "source": "yfinance", "category": "Developed", "tier": 1, "rps": 0.18},
    {"name": "BTC",     "ticker": "BTC-USD", "source": "yfinance", "category": "Crypto",    "tier": 2, "rps": 0.55},
]

START = "2018-01-01"
END = "2026-04-17"

CHRONOS_MODEL = "amazon/chronos-t5-small"
CHRONOS_WINDOW = WPE_WINDOW  # 22 — match entropy WPE window
PCA_DIMS = 2  # match (WPE, SPE_Z) plane dimensionality
FORWARD_VOL_HORIZON = 20
RANDOM_STATE = 42
BATCH_SIZE = 64


# ==============================================================================
# CHRONOS EMBEDDING EXTRACTION
# ==============================================================================
def load_chronos_pipeline():
    from chronos import ChronosPipeline

    print(f"Loading {CHRONOS_MODEL} on CPU (float32)...")
    t0 = time.time()
    pipe = ChronosPipeline.from_pretrained(
        CHRONOS_MODEL,
        device_map="cpu",
        torch_dtype=torch.float32,
    )
    print(f"  loaded in {time.time() - t0:.1f}s")
    return pipe


def chronos_embed_rolling(
    pipe,
    log_returns: np.ndarray,
    window: int,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract Chronos encoder embeddings on rolling windows of `log_returns`.

    For each timestep t in [window-1, len(log_returns)-1], feed the window
    log_returns[t-window+1 : t+1] (length `window`) to the encoder, mean-pool
    over the sequence dimension, and collect the hidden-state vector.

    Returns:
        embeddings: (T - window + 1, hidden_dim) array
        valid_idx: (T - window + 1,) array of integer indices into log_returns
                   corresponding to each embedding row (the right edge t).
    """
    n = len(log_returns)
    n_windows = n - window + 1
    if n_windows <= 0:
        raise ValueError(f"log_returns too short: n={n}, window={window}")

    # Build the window stack as a list of torch tensors.
    contexts = [
        torch.tensor(log_returns[t - window + 1 : t + 1], dtype=torch.float32)
        for t in range(window - 1, n)
    ]

    embeddings_list: list[np.ndarray] = []
    t_start_total = time.time()
    for i in range(0, n_windows, batch_size):
        batch = contexts[i : i + batch_size]
        # ChronosPipeline.embed accepts list[Tensor] of any lengths and pads internally.
        with torch.no_grad():
            emb_t, _scale = pipe.embed(batch)  # emb_t: (B, S, H)
        # Mean-pool over the time/sequence dimension to a single hidden vector per window.
        emb_pooled = emb_t.mean(dim=1).cpu().numpy()  # (B, H)
        embeddings_list.append(emb_pooled)
        if (i // batch_size) % 4 == 0:
            done = min(i + batch_size, n_windows)
            elapsed = time.time() - t_start_total
            rate = done / max(elapsed, 1e-6)
            eta = (n_windows - done) / max(rate, 1e-6)
            print(f"    batch {done}/{n_windows} ({rate:.1f} win/s, ETA {eta:.0f}s)")

    embeddings = np.concatenate(embeddings_list, axis=0)
    valid_idx = np.arange(window - 1, n)
    return embeddings, valid_idx


# ==============================================================================
# FORWARD-VOL TARGET
# ==============================================================================
def forward_realised_vol(
    log_returns: pd.Series, horizon: int = FORWARD_VOL_HORIZON
) -> pd.Series:
    """Annualised forward `horizon`-day realised volatility (in percent)."""
    rolling_std = (
        log_returns.rolling(horizon).std()
        .shift(-horizon)  # use future window: realised vol over [t+1 .. t+horizon]
    )
    return rolling_std * np.sqrt(252) * 100


# ==============================================================================
# PER-MARKET CHRONOS PIPELINE
# ==============================================================================
def run_market_chronos(market_def: dict[str, Any], pipe) -> dict[str, Any]:
    name = market_def["name"]
    print(f"\n=== {name} ({market_def['ticker']}) ===")
    t0 = time.time()

    # 1. Load OHLCV.
    df = load_ohlcv(name, market_def["ticker"], market_def["source"], START, END)
    print(f"  OHLCV: {len(df)} bars, {df.index.min().date()} -> {df.index.max().date()}")

    # 2. Log returns (daily, on Close).
    log_returns_full = np.log(df["Close"] / df["Close"].shift(1))
    log_returns_full = log_returns_full.dropna()
    log_returns_arr = log_returns_full.values

    # 3. Entropy baseline (already cached but re-run for parity).
    feat_entropy = build_plane1_features(df)
    if len(feat_entropy) < 100:
        raise RuntimeError(f"{name}: too few entropy bars ({len(feat_entropy)})")
    print(f"  entropy bars (post SPE_Z floor): {len(feat_entropy)}")

    # 4. Chronos rolling embeddings on the same log-return series.
    print(f"  Extracting Chronos embeddings (window={CHRONOS_WINDOW}, batch={BATCH_SIZE})...")
    embeddings, valid_idx = chronos_embed_rolling(
        pipe, log_returns_arr, window=CHRONOS_WINDOW, batch_size=BATCH_SIZE
    )
    chronos_full_index = log_returns_full.index[valid_idx]
    print(f"  Chronos embeddings: {embeddings.shape}")

    # 5. PCA to 2D (match (WPE, SPE_Z) plane dimensionality) — fit on full Chronos rows.
    pca = PCA(n_components=PCA_DIMS, random_state=RANDOM_STATE)
    chronos_2d = pca.fit_transform(embeddings)
    explained = pca.explained_variance_ratio_
    print(f"  PCA explained variance ratio: {explained.tolist()} (total {explained.sum():.3f})")

    chronos_feat = pd.DataFrame(
        chronos_2d, index=chronos_full_index, columns=["PC1", "PC2"]
    )

    # 6. Restrict to entropy-labelable bars (same downstream comparison frame).
    common_idx = chronos_feat.index.intersection(feat_entropy.index)
    chronos_feat_aligned = chronos_feat.loc[common_idx]
    feat_entropy_aligned = feat_entropy.loc[common_idx]
    print(f"  aligned bars (intersect): {len(common_idx)}")

    # 7. Fit GMM + Schmitt-trigger on Chronos features (same hyperparameters).
    chronos_out = fit_classifier_and_filter(
        chronos_feat_aligned, random_state=RANDOM_STATE
    )

    # 8. Forward 20d realised vol on common index.
    fv = forward_realised_vol(log_returns_full, horizon=FORWARD_VOL_HORIZON)
    fv_aligned = fv.loc[common_idx].dropna()
    valid = chronos_feat_aligned.index.intersection(fv_aligned.index)
    if len(valid) < 50:
        raise RuntimeError(f"{name}: too few valid forward-vol bars ({len(valid)})")

    raw_labels = chronos_out["raw_labels"].loc[valid].values
    filt_labels = chronos_out["filtered_labels"].loc[valid].values
    fwd_vol = fv_aligned.loc[valid].values

    # 9. KW H statistic on raw + filtered labels.
    def kw_h_and_eta(labels, vol):
        groups = [vol[labels == k] for k in sorted(np.unique(labels))]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) < 2:
            return float("nan"), float("nan")
        h_stat, _p = kruskal(*groups)
        n_total = sum(len(g) for g in groups)
        eta_sq = (h_stat - len(groups) + 1) / (n_total - len(groups))
        eta_sq = max(0.0, eta_sq)
        return float(h_stat), float(eta_sq)

    h_raw, eta_raw = kw_h_and_eta(raw_labels, fwd_vol)
    h_filt, eta_filt = kw_h_and_eta(filt_labels, fwd_vol)

    # 10. Flip rates.
    raw_fpy = flip_rate_per_year(chronos_out["raw_labels"].loc[valid])
    filt_fpy = flip_rate_per_year(chronos_out["filtered_labels"].loc[valid])

    # 11. Regime composition (filtered).
    unique, counts = np.unique(filt_labels, return_counts=True)
    comp = {int(k): float(c / len(filt_labels)) for k, c in zip(unique, counts)}

    elapsed = time.time() - t0
    print(
        f"  H_raw_chronos = {h_raw:.2f} (eta^2 = {eta_raw:.4f}), "
        f"H_filt_chronos = {h_filt:.2f} (eta^2 = {eta_filt:.4f}); "
        f"filt flips/yr = {filt_fpy:.2f}, elapsed {elapsed:.1f}s"
    )

    return {
        "name": name,
        "ticker": market_def["ticker"],
        "category": market_def["category"],
        "tier": market_def["tier"],
        "rps": market_def["rps"],
        "n_bars_aligned": int(len(valid)),
        "pca_explained_variance_ratio": [float(x) for x in explained.tolist()],
        "pca_explained_variance_total": float(explained.sum()),
        "H_raw_chronos": h_raw,
        "eta_sq_raw_chronos": eta_raw,
        "H_filt_chronos": h_filt,
        "eta_sq_filt_chronos": eta_filt,
        "raw_flips_per_year": float(raw_fpy),
        "filt_flips_per_year": float(filt_fpy),
        "regime_composition_filtered": comp,
        "elapsed_seconds": float(elapsed),
    }


# ==============================================================================
# CROSS-MARKET CORRELATIONS
# ==============================================================================
def cross_market_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    h_raw = np.array([r["H_raw_chronos"] for r in rows])
    h_filt = np.array([r["H_filt_chronos"] for r in rows])
    tier = np.array([r["tier"] for r in rows])
    rps = np.array([r["rps"] for r in rows])

    rho_raw_tier, p_raw_tier = spearmanr(h_raw, tier)
    rho_filt_tier, p_filt_tier = spearmanr(h_filt, tier)
    rho_raw_rps, p_raw_rps = spearmanr(h_raw, rps)
    rho_filt_rps, p_filt_rps = spearmanr(h_filt, rps)

    return {
        "rho_H_raw_chronos_tier": float(rho_raw_tier),
        "p_H_raw_chronos_tier": float(p_raw_tier),
        "rho_H_filt_chronos_tier": float(rho_filt_tier),
        "p_H_filt_chronos_tier": float(p_filt_tier),
        "rho_H_raw_chronos_rps": float(rho_raw_rps),
        "p_H_raw_chronos_rps": float(p_raw_rps),
        "rho_H_filt_chronos_rps": float(rho_filt_rps),
        "p_H_filt_chronos_rps": float(p_filt_rps),
    }


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("=" * 78)
    print("H6 — Chronos vs Entropy head-to-head, 8-market panel")
    print("=" * 78)
    print(f"Model            : {CHRONOS_MODEL}")
    print(f"Window           : {CHRONOS_WINDOW} bars")
    print(f"PCA dims         : {PCA_DIMS}")
    print(f"Forward vol horiz: {FORWARD_VOL_HORIZON}")
    print(f"Random state     : {RANDOM_STATE}")
    print(f"Batch size       : {BATCH_SIZE}")
    print()

    pipe = load_chronos_pipeline()

    rows = []
    t_start = time.time()
    for m in MARKETS:
        try:
            row = run_market_chronos(m, pipe)
            rows.append(row)
        except Exception as exc:
            print(f"  !! {m['name']} failed: {exc}")
            rows.append({"name": m["name"], "error": str(exc)})

    summary = cross_market_summary([r for r in rows if "error" not in r])

    out = {
        "model": CHRONOS_MODEL,
        "window": CHRONOS_WINDOW,
        "pca_dims": PCA_DIMS,
        "forward_vol_horizon": FORWARD_VOL_HORIZON,
        "random_state": RANDOM_STATE,
        "batch_size": BATCH_SIZE,
        "n_markets": len(rows),
        "n_markets_ok": sum(1 for r in rows if "error" not in r),
        "per_market": rows,
        "cross_market_correlations": summary,
        "total_elapsed_seconds": float(time.time() - t_start),
    }

    out_path = RESULTS_DIR / "h6_chronos_8market.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"  output     : {out_path}")
    print(f"  total time : {out['total_elapsed_seconds']:.1f}s")
    print()
    print("Cross-market correlations (Chronos features):")
    for k, v in summary.items():
        print(f"  {k:32s} = {v:+.4f}")
    print()
    print("Per-market H comparison (raw / filtered):")
    print(f"  {'market':<10s} {'tier':<5s} {'rps':>6s} {'H_raw':>10s} {'H_filt':>10s} {'eta_raw':>9s} {'eta_filt':>9s}")
    for r in rows:
        if "error" in r:
            print(f"  {r['name']:<10s} ERROR: {r['error']}")
            continue
        print(
            f"  {r['name']:<10s} {r['tier']:<5d} "
            f"{r['rps']:>6.3f} {r['H_raw_chronos']:>10.2f} {r['H_filt_chronos']:>10.2f} "
            f"{r['eta_sq_raw_chronos']:>9.4f} {r['eta_sq_filt_chronos']:>9.4f}"
        )


if __name__ == "__main__":
    main()
