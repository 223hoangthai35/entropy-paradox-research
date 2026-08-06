"""
Cross-Market Entropy Paradox — V2 Combined, H1 Scientifically Refined.

ORIGINAL (pre-registered b130b0f, 2026-04-18). Kruskal-Wallis omnibus on
3 regime groups x forward 20d realized vol, with Paradox/Inverted direction
assigned by simple mean ordering. 8-market panel (VN, PSEI, KOSPI, NIFTY,
SPX, FTSE, NIKKEI, BTC).

REFACTOR (post-hoc, 2026-04-19). Adds the scientific machinery H1 needs to
withstand sceptical review. Four axes, additive (legacy columns preserved):

  Axis #1  PRIMARY CONTRAST: one-sided Mann-Whitney U (alternative='greater')
    for mean(fwd_vol | Deterministic) > mean(fwd_vol | Stochastic), with
    Cliff's delta effect size and circular-block bootstrap 95% CI. Tests
    the paradox claim directly rather than via a 3-way omnibus.
  Axis #2  SUPPLEMENTARY: retains KW omnibus; adds epsilon-squared effect
    size; Dunn's post-hoc pairwise with Holm step-down; BH-FDR across the
    8-market panel at each forward horizon.
  Axis #3  ROBUSTNESS PANEL: re-runs the primary contrast at forward-vol
    horizons {5, 10, 20, 40, 60}d to confirm 20d is not cherry-picked.
  Axis #4  INFERENCE CORRECTION: circular block bootstrap (block=20) for
    CIs, block-cyclic rotation for one-sided p under null, and Newey-West
    HAC t-stat at lag=20 for the mean difference. All three accommodate
    the 19-bar overlap in adjacent 20d forward-vol observations.

The pre-reg claim is evaluated on the ARCHIVED outputs under
validation/results_v2/prereg_b130b0f/ (read-only). A regression assertion
at end-of-main checks legacy H_stat / p_value / direction columns in the
new CSV match the archive to 4 decimal places --- the refactor is
additive, not altering.

Pinned (DO NOT override):
    WPE m=3 tau=1 window=22, SampEn win=60, SPE_Z rolling win=504,
    GMM k=3 full-cov, random_state=42.

H2 microstructure specification (2026-04-19): superseded the composite
MS_index (pre-reg b130b0f, weights 0.4/0.3/0.3) with Retail Participation
Share (RPS) as a single-variable ex-ante proxy. See h2_rps_validation.py
and paper_artifacts/rps_rationale.md. The composite formula is not
computed here; its pre-reg output is preserved under
validation/results_v2/prereg_b130b0f/.

Outputs:
    validation/results_v2/<MARKET>_v2_results.json         (extended)
    validation/results_v2/cross_market_summary_v2.csv      (legacy cols + refined + rps)
    validation/results_v2/cross_market_h1_horizons.csv     (horizon sweep)
    validation/results_v2/cross_market_h1_horizons.png     (heatmap)
    validation/results_v2/cross_market_validation_v2.png   (boxplots)
    validation/results_v2/h_vs_rps_v2.png                  (H vs RPS scatter)

Run:
    python validation/cross_market_v2.py
"""
from __future__ import annotations

import json
import os
import sys
import zlib
import time
import warnings
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy.stats import kruskal, spearmanr, mannwhitneyu, rankdata, norm

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import run_full_pipeline, SPE_Z_WIN
from validation._regression_guard import guard as _reg_guard
from skills.ds_skill import REGIME_NAMES

# ==============================================================================
# PRE-REGISTERED MARKET PANEL
# ==============================================================================
MARKETS: list[dict[str, Any]] = [
    {"name": "VNINDEX", "ticker": "VNINDEX", "source": "vnstock",  "category": "Frontier"},
    {"name": "BVB",     "ticker": "BVB:BET",  "source": "tvdatafeed", "category": "Frontier"},
    {"name": "KOSPI",   "ticker": "^KS11",   "source": "yfinance", "category": "Emerging"},
    {"name": "NIFTY",   "ticker": "^NSEI",   "source": "yfinance", "category": "Emerging"},
    {"name": "SPX",     "ticker": "^GSPC",   "source": "yfinance", "category": "Developed"},
    {"name": "FTSE",    "ticker": "^FTSE",   "source": "yfinance", "category": "Developed"},
    {"name": "NIKKEI",  "ticker": "^N225",   "source": "yfinance", "category": "Developed"},
    {"name": "BTC",     "ticker": "BTC-USD", "source": "yfinance", "category": "Crypto"},
]

START = "2018-01-01"
END   = "2026-06-30"

# Retail Participation Share (RPS) — single-variable microstructure proxy.
# Ex-ante, publicly sourced. See h2_rps_validation.py and
# paper_artifacts/rps_rationale.md for full sources.
RPS_VALUE = {
    "VNINDEX": 0.90,
    "BVB":     0.225,    # P2 Uniform[0.20, 0.25] midpoint (BVB IR + ASF Romania monthly market reports)
    "KOSPI":   0.45,     # KRX 2026 direct turnover-by-investor-type (cascade verification, App D.3)
    "NIFTY":   0.40,
    "SPX":     0.275,    # P2 Uniform[0.18, 0.37] midpoint
    "FTSE":    0.20,     # P2 Uniform[0.15, 0.25] midpoint
    "NIKKEI":  0.18,
    "BTC":     0.55,
}

REGIME_ORDER = ["Deterministic", "Transitional", "Stochastic"]
REGIME_PALETTE = {
    "Deterministic": "#e74c3c",
    "Transitional":  "#f39c12",
    "Stochastic":    "#2ecc71",
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results_v2")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================================================
# REFINEMENT CONSTANTS (post-hoc)
# ==============================================================================
HORIZONS = [5, 10, 20, 40, 60]     # fwd-vol horizons (days); 20 = legacy/pre-reg
PRIMARY_HORIZON = 20
BLOCK = 20                         # matches fwd-vol window for overlap
N_BOOT = 2000                      # circular block bootstrap draws
N_PERM = 2000                      # block-rotation permutations
RNG_SEED = 42
NW_LAG = 20
ALPHA = 0.05

ARCHIVE_DIR = os.path.join(OUTPUT_DIR, "prereg_b130b0f")


# ==============================================================================
# FORWARD METRICS (parametrised horizon)
# ==============================================================================
def compute_forward_metrics(ohlcv: pd.DataFrame, horizon: int = 20) -> pd.DataFrame:
    """Forward realized vol (h-day annualized %) and forward max drawdown (10d, %)."""
    close = ohlcv["Close"].astype(float)
    log_ret = np.log(close / close.shift(1))
    fwd_vol = (log_ret.shift(-1).rolling(horizon).std().shift(-(horizon - 1))
               * np.sqrt(252) * 100.0)
    rolling_max = close.rolling(10).max().shift(-9)
    fwd_dd = ((close - rolling_max) / close * 100.0).clip(upper=0).abs()
    return pd.DataFrame({f"FwdVol{horizon}d": fwd_vol, "FwdMaxDD10d": fwd_dd})


def _rps(market: str) -> float:
    return float(RPS_VALUE[market])


# ==============================================================================
# STATISTICAL HELPERS (post-hoc axes)
# ==============================================================================
def _cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """Cliff's delta via Mann-Whitney U: delta = 2*U / (n_x*n_y) - 1.
    Range [-1, 1]. Positive means x tends to exceed y."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    pooled = np.concatenate([x, y])
    ranks = rankdata(pooled)
    R1 = ranks[:len(x)].sum()
    U = R1 - len(x) * (len(x) + 1) / 2.0
    return float(2.0 * U / (len(x) * len(y)) - 1.0)


def _kw_epsilon_sq(H: float, n: int, k: int = 3) -> float:
    """Epsilon-squared effect size for Kruskal-Wallis. Range [0, 1]."""
    if n <= k:
        return float("nan")
    val = (H - k + 1.0) / (n - k)
    return float(max(val, 0.0))


def _dunn_holm(groups: dict[str, np.ndarray]) -> dict[tuple[str, str], tuple[float, float, float]]:
    """Dunn's test with tie correction and Holm step-down.
    Returns {(grp_i, grp_j): (z, p_raw_two_sided, p_holm)}."""
    names = list(groups.keys())
    sizes = [len(groups[n]) for n in names]
    pooled = np.concatenate([groups[n] for n in names])
    ranks = rankdata(pooled)
    mean_ranks = {}
    offset = 0
    for n, s in zip(names, sizes):
        mean_ranks[n] = ranks[offset:offset + s].mean() if s > 0 else float("nan")
        offset += s
    N = sum(sizes)
    _, counts = np.unique(pooled, return_counts=True)
    T = float(np.sum(counts.astype(float) ** 3 - counts))
    tie_corr = 1.0 - T / (N ** 3 - N) if N > 1 else 1.0
    pairs = [(i, j) for i in range(len(names)) for j in range(i + 1, len(names))]
    raw: dict[tuple[str, str], tuple[float, float]] = {}
    for i, j in pairs:
        if sizes[i] == 0 or sizes[j] == 0:
            raw[(names[i], names[j])] = (float("nan"), float("nan"))
            continue
        se = np.sqrt((N * (N + 1) / 12.0) * tie_corr * (1.0 / sizes[i] + 1.0 / sizes[j]))
        z = (mean_ranks[names[i]] - mean_ranks[names[j]]) / se if se > 0 else float("nan")
        p_two = 2.0 * (1.0 - norm.cdf(abs(z))) if not np.isnan(z) else float("nan")
        raw[(names[i], names[j])] = (float(z), float(p_two))
    # Holm step-down on raw two-sided p-values
    pair_keys = list(raw.keys())
    p_vals = np.array([raw[k][1] for k in pair_keys], dtype=float)
    m = len(p_vals)
    order = np.argsort(np.where(np.isnan(p_vals), 1.0, p_vals))
    p_holm = np.empty(m)
    running_max = 0.0
    for k, idx in enumerate(order):
        adj = (m - k) * p_vals[idx]
        running_max = max(running_max, adj)
        p_holm[idx] = min(running_max, 1.0) if not np.isnan(adj) else float("nan")
    out: dict[tuple[str, str], tuple[float, float, float]] = {}
    for k, pair in enumerate(pair_keys):
        z, p_two = raw[pair]
        out[pair] = (z, p_two, float(p_holm[k]))
    return out


def _bh_fdr(p_vals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR q-values."""
    p = np.asarray(p_vals, dtype=float)
    m = len(p)
    valid = ~np.isnan(p)
    q = np.full(m, np.nan)
    if valid.sum() == 0:
        return q
    pv = p[valid]
    order = np.argsort(pv)
    sorted_p = pv[order]
    mv = len(sorted_p)
    q_sorted = sorted_p * mv / (np.arange(mv) + 1)
    for i in range(mv - 2, -1, -1):
        q_sorted[i] = min(q_sorted[i], q_sorted[i + 1])
    q_sorted = np.clip(q_sorted, 0.0, 1.0)
    unsorted = np.empty(mv)
    unsorted[order] = q_sorted
    q[valid] = unsorted
    return q


def _circular_block_indices(n: int, block: int, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    """Return (n_boot, n) matrix of circular block-bootstrap indices."""
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    offsets = np.arange(block)[None, None, :]
    idx = (starts[:, :, None] + offsets) % n
    return idx.reshape(n_boot, -1)[:, :n]


def _block_bootstrap_delta_ci(labels: np.ndarray, fwd_vol: np.ndarray,
                              det_label: str, sto_label: str,
                              block: int, n_boot: int, rng: np.random.Generator,
                              alpha: float = 0.05
                              ) -> tuple[float, float, np.ndarray]:
    """95% CI for Cliff's delta(Det, Sto) under circular block bootstrap.
    Returns (lo, hi, full boot array)."""
    n = len(labels)
    idx_mat = _circular_block_indices(n, block, n_boot, rng)
    boot_deltas = np.empty(n_boot)
    for b in range(n_boot):
        idx = idx_mat[b]
        l = labels[idx]
        v = fwd_vol[idx]
        det = v[l == det_label]
        sto = v[l == sto_label]
        if len(det) < 2 or len(sto) < 2:
            boot_deltas[b] = np.nan
            continue
        boot_deltas[b] = _cliffs_delta(det, sto)
    lo = float(np.nanpercentile(boot_deltas, 100 * alpha / 2))
    hi = float(np.nanpercentile(boot_deltas, 100 * (1 - alpha / 2)))
    return lo, hi, boot_deltas


def _block_rotation_p_one_sided(labels: np.ndarray, fwd_vol: np.ndarray,
                                det_label: str, sto_label: str,
                                block: int, n_perm: int, rng: np.random.Generator
                                ) -> float:
    """One-sided p-value for H0: delta(Det, Sto) <= 0 under block-cyclic rotation.
    Rotates the label sequence by random shift in multiples of `block` to
    preserve within-block autocorrelation while breaking label/fwd_vol linkage."""
    n = len(labels)
    det_obs = fwd_vol[labels == det_label]
    sto_obs = fwd_vol[labels == sto_label]
    if len(det_obs) < 2 or len(sto_obs) < 2:
        return float("nan")
    delta_obs = _cliffs_delta(det_obs, sto_obs)
    # Shifts restricted to multiples of `block`, minimum 1 block, max n-1
    max_k = max(1, n // block - 1)
    shifts = rng.integers(1, max_k + 1, size=n_perm) * block
    ge = 0
    for s in shifts:
        rotated = np.roll(labels, s)
        det_r = fwd_vol[rotated == det_label]
        sto_r = fwd_vol[rotated == sto_label]
        if len(det_r) < 2 or len(sto_r) < 2:
            continue
        d = _cliffs_delta(det_r, sto_r)
        if d >= delta_obs:
            ge += 1
    return float((ge + 1) / (n_perm + 1))   # +1 smoothing


def _newey_west_tstat(fwd_vol: np.ndarray, labels: np.ndarray,
                      det_label: str, sto_label: str,
                      tra_label: str, lag: int = 20
                      ) -> tuple[float, float, float, float]:
    """OLS fwd_vol_t = alpha + beta_Det * I(Det) + beta_Tra * I(Tra) + u_t with
    Sto as reference. Returns (beta_Det_vs_Sto, se_nw, t_nw, p_two)."""
    mask = ~np.isnan(fwd_vol)
    y = fwd_vol[mask]
    lab = labels[mask]
    n = len(y)
    if n < 3 * lag:
        return (float("nan"),) * 4
    X = np.column_stack([
        np.ones(n),
        (lab == det_label).astype(float),
        (lab == tra_label).astype(float),
    ])
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return (float("nan"),) * 4
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    u = X * resid[:, None]
    S = (u.T @ u) / n
    for L in range(1, lag + 1):
        w = 1.0 - L / (lag + 1.0)
        Gamma = (u[L:].T @ u[:-L]) / n
        S = S + w * (Gamma + Gamma.T)
    var = n * XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(var), 0.0))
    t = beta[1] / se[1] if se[1] > 0 else float("nan")
    p_two = 2.0 * (1.0 - norm.cdf(abs(t))) if not np.isnan(t) else float("nan")
    return float(beta[1]), float(se[1]), float(t), float(p_two)


def _formal_direction_verdict(delta: float, ci_lo: float, ci_hi: float) -> str:
    """Paradox if CI entirely > 0; Inverted if CI entirely < 0; else n.s."""
    if any(np.isnan([delta, ci_lo, ci_hi])):
        return "SKIP"
    if ci_lo > 0.0:
        return "Paradox"
    if ci_hi < 0.0:
        return "Inverted"
    return "n.s."


# ==============================================================================
# PER-MARKET ANALYSIS (includes all 4 axes)
# ==============================================================================
def analyze_market(cfg: dict[str, Any]) -> Optional[dict[str, Any]]:
    name = cfg["name"]
    print(f"\n[{name}] {cfg['ticker']} via {cfg['source']}")
    rng = np.random.default_rng(RNG_SEED + zlib.crc32((name).encode()) % 1000)

    t0 = time.time()
    try:
        out = run_full_pipeline(
            market=name, ticker=cfg["ticker"], source=cfg["source"],
            start=START, end=END,
        )
    except Exception as e:
        print(f"  [SKIP] pipeline failed: {type(e).__name__}: {e}")
        return None

    ohlcv = out["ohlcv"]
    raw_labels: pd.Series = out["raw_labels"]
    filt_labels: pd.Series = out["filtered_labels"]

    if len(raw_labels) < SPE_Z_WIN:
        print(f"  [SKIP] insufficient labelable bars: {len(raw_labels)} < {SPE_Z_WIN}")
        return None

    # Compute fwd vol at all horizons; join to labels
    labels_arr = raw_labels.astype(int).map(REGIME_NAMES).values
    filt_labels_arr = filt_labels.astype(int).map(REGIME_NAMES).values
    horizon_frames = {}
    horizon_frames_filt = {}
    for h in HORIZONS:
        fwd = compute_forward_metrics(ohlcv, horizon=h)
        df = pd.DataFrame({"RegimeName": labels_arr}, index=raw_labels.index)
        horizon_frames[h] = df.join(fwd, how="left")
        df_filt = pd.DataFrame({"RegimeName": filt_labels_arr}, index=filt_labels.index)
        horizon_frames_filt[h] = df_filt.join(fwd, how="left")

    # ------------------------------------------------------------------
    # Axis #2 (legacy KW) + legacy direction at PRIMARY_HORIZON (=20)
    # ------------------------------------------------------------------
    df20 = horizon_frames[PRIMARY_HORIZON]
    fwd_col = f"FwdVol{PRIMARY_HORIZON}d"
    groups = {r: df20.loc[df20["RegimeName"] == r, fwd_col].dropna().values
              for r in REGIME_ORDER}
    usable = {r: v for r, v in groups.items() if len(v) >= 5}
    if len(usable) < 2:
        H_stat, p_kw = float("nan"), float("nan")
    else:
        H_stat, p_kw = kruskal(*usable.values())

    n_kw_total = int(sum(len(v) for v in groups.values()))
    eps_sq = _kw_epsilon_sq(H_stat, n_kw_total, k=3) if not np.isnan(H_stat) else float("nan")

    means = {r: float(np.nanmean(groups[r])) if len(groups[r]) else float("nan")
             for r in REGIME_ORDER}
    medians = {r: float(np.nanmedian(groups[r])) if len(groups[r]) else float("nan")
               for r in REGIME_ORDER}

    # Legacy descriptive direction (preserved, used in regression assertion)
    det_mean, sto_mean = means["Deterministic"], means["Stochastic"]
    if np.isnan(det_mean) or np.isnan(sto_mean):
        direction_legacy = "SKIP"
    elif det_mean > sto_mean:
        direction_legacy = "Paradox"
    else:
        direction_legacy = "Inverted"

    # Dunn's post-hoc (Holm-adjusted)
    dunn = _dunn_holm(groups)

    # ------------------------------------------------------------------
    # Axis #1 + #3 + #4: primary contrast at each horizon
    # ------------------------------------------------------------------
    horizon_rows = []
    for h in HORIZONS:
        dfh = horizon_frames[h]
        col = f"FwdVol{h}d"
        # Align labels and fwd_vol (drop rows with NaN fwd_vol)
        valid = dfh[col].notna()
        labels_h = dfh.loc[valid, "RegimeName"].values
        fwd_h = dfh.loc[valid, col].values
        det_h = fwd_h[labels_h == "Deterministic"]
        sto_h = fwd_h[labels_h == "Stochastic"]
        if len(det_h) < 5 or len(sto_h) < 5:
            horizon_rows.append({
                "horizon_days": h, "n_det": int(len(det_h)), "n_sto": int(len(sto_h)),
                "mean_det": float("nan"), "mean_sto": float("nan"),
                "cliffs_delta": float("nan"),
                "delta_ci_lo": float("nan"), "delta_ci_hi": float("nan"),
                "U_det_sto": float("nan"), "p_mw_1sided": float("nan"),
                "p_blockperm_1sided": float("nan"),
                "nw_beta": float("nan"), "nw_se": float("nan"),
                "nw_tstat": float("nan"), "nw_p_two": float("nan"),
                "direction_verdict_formal": "SKIP",
            })
            continue
        # Mann-Whitney one-sided (Det > Sto)
        U, p_mw = mannwhitneyu(det_h, sto_h, alternative="greater")
        delta = _cliffs_delta(det_h, sto_h)
        ci_lo, ci_hi, _ = _block_bootstrap_delta_ci(
            labels_h, fwd_h, "Deterministic", "Stochastic",
            block=BLOCK, n_boot=N_BOOT, rng=rng, alpha=ALPHA,
        )
        p_perm = _block_rotation_p_one_sided(
            labels_h, fwd_h, "Deterministic", "Stochastic",
            block=BLOCK, n_perm=N_PERM, rng=rng,
        )
        nw_beta, nw_se, nw_t, nw_p = _newey_west_tstat(
            fwd_h, labels_h, "Deterministic", "Stochastic", "Transitional",
            lag=NW_LAG,
        )
        verdict = _formal_direction_verdict(delta, ci_lo, ci_hi)
        horizon_rows.append({
            "horizon_days": h,
            "n_det": int(len(det_h)), "n_sto": int(len(sto_h)),
            "mean_det": float(det_h.mean()), "mean_sto": float(sto_h.mean()),
            "cliffs_delta": float(delta),
            "delta_ci_lo": float(ci_lo), "delta_ci_hi": float(ci_hi),
            "U_det_sto": float(U), "p_mw_1sided": float(p_mw),
            "p_blockperm_1sided": float(p_perm),
            "nw_beta": float(nw_beta), "nw_se": float(nw_se),
            "nw_tstat": float(nw_t), "nw_p_two": float(nw_p),
            "direction_verdict_formal": verdict,
        })

    # Cross-horizon consistency at this market
    verdicts = [r["direction_verdict_formal"] for r in horizon_rows]
    unique_verdicts = set(verdicts) - {"SKIP"}
    if len(unique_verdicts) == 1:
        across = f"consistent:{next(iter(unique_verdicts))}"
    elif len(unique_verdicts) == 0:
        across = "SKIP"
    else:
        parts = [f"{r['horizon_days']}d:{r['direction_verdict_formal']}" for r in horizon_rows]
        across = "mixed|" + ";".join(parts)

    # Primary row fields (=20d contrast)
    primary = next(r for r in horizon_rows if r["horizon_days"] == PRIMARY_HORIZON)

    # Regime shares (from 20d frame)
    n_total = len(df20)
    share = {r: float((df20["RegimeName"] == r).sum() / n_total) if n_total else float("nan")
             for r in REGIME_ORDER}

    # Drawdown lifts (from 20d frame)
    base_dd = df20["FwdMaxDD10d"].dropna()
    base_rates = {thr: float((base_dd > thr).mean()) if len(base_dd) else float("nan")
                  for thr in [3.0, 5.0, 7.0]}
    lifts: dict[str, dict[str, float]] = {}
    for r in REGIME_ORDER:
        sub = df20.loc[df20["RegimeName"] == r, "FwdMaxDD10d"].dropna()
        if len(sub) == 0:
            lifts[r] = {f"lift_{thr}pct": float("nan") for thr in [3.0, 5.0, 7.0]}
            continue
        row = {}
        for thr in [3.0, 5.0, 7.0]:
            hit = float((sub > thr).mean())
            base = base_rates[thr]
            row[f"lift_{thr}pct"] = hit / base if base and base > 0 else float("nan")
        lifts[r] = row

    # ------------------------------------------------------------------
    # FILTERED-LABELS PARALLEL: same statistics computed from
    # `out["filtered_labels"]` (post-hysteresis Schmitt-trigger output)
    # so paper §9.6 can compare raw-GMM vs hysteresis side-by-side. All
    # legacy columns above remain raw-GMM (regression assertion intact).
    # ------------------------------------------------------------------
    df20_filt = horizon_frames_filt[PRIMARY_HORIZON]
    groups_f = {r: df20_filt.loc[df20_filt["RegimeName"] == r, fwd_col].dropna().values
                for r in REGIME_ORDER}
    usable_f = {r: v for r, v in groups_f.items() if len(v) >= 5}
    if len(usable_f) < 2:
        H_stat_f, p_kw_f = float("nan"), float("nan")
    else:
        H_stat_f, p_kw_f = kruskal(*usable_f.values())
    means_f = {r: float(np.nanmean(groups_f[r])) if len(groups_f[r]) else float("nan")
               for r in REGIME_ORDER}
    det_f, sto_f = means_f["Deterministic"], means_f["Stochastic"]
    if np.isnan(det_f) or np.isnan(sto_f):
        direction_filtered = "SKIP"
    elif det_f > sto_f:
        direction_filtered = "Paradox"
    else:
        direction_filtered = "Inverted"

    # Primary-horizon contrast on filtered labels
    df20_filt_valid = df20_filt[df20_filt[fwd_col].notna()]
    labels_f_h = df20_filt_valid["RegimeName"].values
    fwd_f_h = df20_filt_valid[fwd_col].values
    det_h_f = fwd_f_h[labels_f_h == "Deterministic"]
    sto_h_f = fwd_f_h[labels_f_h == "Stochastic"]
    if len(det_h_f) >= 5 and len(sto_h_f) >= 5:
        U_f, p_mw_f = mannwhitneyu(det_h_f, sto_h_f, alternative="greater")
        delta_f = _cliffs_delta(det_h_f, sto_h_f)
        ci_lo_f, ci_hi_f, _ = _block_bootstrap_delta_ci(
            labels_f_h, fwd_f_h, "Deterministic", "Stochastic",
            block=BLOCK, n_boot=N_BOOT, rng=np.random.default_rng(RNG_SEED + zlib.crc32((name + "_filt").encode()) % 1000),
            alpha=ALPHA,
        )
        verdict_f = _formal_direction_verdict(delta_f, ci_lo_f, ci_hi_f)
    else:
        U_f, p_mw_f = float("nan"), float("nan")
        delta_f, ci_lo_f, ci_hi_f = float("nan"), float("nan"), float("nan")
        verdict_f = "SKIP"

    # Filtered regime shares (for H3 raw-vs-filtered p_tra in paper §9.6)
    n_total_f = len(df20_filt)
    share_f = {r: float((df20_filt["RegimeName"] == r).sum() / n_total_f) if n_total_f else float("nan")
               for r in REGIME_ORDER}

    elapsed = time.time() - t0
    print(f"  RAW H={H_stat:.2f} delta={primary['cliffs_delta']:.3f} verdict={primary['direction_verdict_formal']}")
    print(f"  FLT H={H_stat_f:.2f} delta={delta_f:.3f} verdict={verdict_f}  ({elapsed:.1f}s)")

    return {
        "market": name,
        "ticker": cfg["ticker"],
        "category": cfg["category"],
        "n_bars": int(n_total),
        "start": str(df20.index[0].date()),
        "end": str(df20.index[-1].date()),
        # Legacy (pre-reg) columns -- must not drift
        "H_stat": float(H_stat),
        "p_value": float(p_kw),
        "direction": direction_legacy,
        "regime_mean_vol": means,
        "regime_median_vol": medians,
        "regime_share": share,
        "base_drawdown_rates": base_rates,
        "lift_by_regime": lifts,
        "rps": _rps(name),
        # Refined (post-hoc) columns
        "kw_epsilon_sq": float(eps_sq),
        "dunn_det_sto_z":   float(dunn[("Deterministic", "Stochastic")][0]),
        "dunn_det_sto_raw": float(dunn[("Deterministic", "Stochastic")][1]),
        "dunn_det_sto_holm":float(dunn[("Deterministic", "Stochastic")][2]),
        "dunn_det_tra_holm":float(dunn[("Deterministic", "Transitional")][2]),
        "dunn_tra_sto_holm":float(dunn[("Transitional",  "Stochastic")][2]),
        "primary_horizon": PRIMARY_HORIZON,
        "primary_U_det_sto":         primary["U_det_sto"],
        "primary_p_mw_1sided":       primary["p_mw_1sided"],
        "primary_cliffs_delta":      primary["cliffs_delta"],
        "primary_delta_ci_lo":       primary["delta_ci_lo"],
        "primary_delta_ci_hi":       primary["delta_ci_hi"],
        "primary_p_blockperm_1s":    primary["p_blockperm_1sided"],
        "primary_nw_beta":           primary["nw_beta"],
        "primary_nw_tstat":          primary["nw_tstat"],
        "primary_nw_p_two":          primary["nw_p_two"],
        "direction_verdict_formal":  primary["direction_verdict_formal"],
        "direction_across_horizons": across,
        "horizons": horizon_rows,
        # Filtered-labels parallel (post-hoc, for §9.6 hysteresis-impact appendix)
        "H_stat_filtered":              float(H_stat_f),
        "p_value_filtered":             float(p_kw_f),
        "direction_filtered":           direction_filtered,
        "regime_mean_vol_filtered":     means_f,
        "regime_share_filtered":        share_f,
        "primary_U_det_sto_filtered":   float(U_f),
        "primary_p_mw_1sided_filtered": float(p_mw_f),
        "primary_cliffs_delta_filtered": float(delta_f),
        "primary_delta_ci_lo_filtered": float(ci_lo_f),
        "primary_delta_ci_hi_filtered": float(ci_hi_f),
        "direction_verdict_formal_filtered": verdict_f,
    }


# ==============================================================================
# OUTPUT: JSON + CSV + PNG
# ==============================================================================
def save_per_market_json(result: dict[str, Any]) -> None:
    path = os.path.join(OUTPUT_DIR, f"{result['market']}_v2_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=float)
    print(f"  saved: {path}")


def build_summary_csv(results: list[dict[str, Any]]) -> pd.DataFrame:
    # Apply BH-FDR across 8 markets at PRIMARY_HORIZON on p_mw_1sided
    p_mw_primary = np.array([r["primary_p_mw_1sided"] for r in results], dtype=float)
    q_bh = _bh_fdr(p_mw_primary)

    # BH-FDR on filtered MW p-values (§9.6 hysteresis-impact comparison)
    p_mw_primary_filt = np.array([r["primary_p_mw_1sided_filtered"] for r in results], dtype=float)
    q_bh_filt = _bh_fdr(p_mw_primary_filt)

    rows = []
    for r, q, q_f in zip(results, q_bh, q_bh_filt):
        rows.append({
            # Legacy (preserved -- regression-asserted against archive)
            "market":           r["market"],
            "category":         r["category"],
            "ticker":           r["ticker"],
            "n_days":           r["n_bars"],
            "date_range":       f"{r['start']}→{r['end']}",
            "H_stat":           round(r["H_stat"], 2) if not np.isnan(r["H_stat"]) else np.nan,
            "p_value":          r["p_value"],
            "det_mean_vol":     round(r["regime_mean_vol"]["Deterministic"], 2),
            "trans_mean_vol":   round(r["regime_mean_vol"]["Transitional"],  2),
            "sto_mean_vol":     round(r["regime_mean_vol"]["Stochastic"],    2),
            "paradox_direction":r["direction"],
            "p_det":            round(r["regime_share"]["Deterministic"], 3),
            "p_tra":            round(r["regime_share"]["Transitional"],  3),
            "p_sto":            round(r["regime_share"]["Stochastic"],    3),
            "lift_det_7pct":    round(r["lift_by_regime"]["Deterministic"]["lift_7.0pct"], 2)
                                if not np.isnan(r["lift_by_regime"]["Deterministic"]["lift_7.0pct"])
                                else np.nan,
            "rps":              round(r["rps"], 3),
            # Refined (post-hoc) columns
            "kw_epsilon_sq":          round(r["kw_epsilon_sq"], 4),
            "dunn_det_sto_holm":      r["dunn_det_sto_holm"],
            "U_det_sto":              r["primary_U_det_sto"],
            "p_det_sto_1sided":       r["primary_p_mw_1sided"],
            "cliffs_delta":           round(r["primary_cliffs_delta"], 4),
            "delta_ci_lo":            round(r["primary_delta_ci_lo"], 4),
            "delta_ci_hi":            round(r["primary_delta_ci_hi"], 4),
            "p_blockperm_1sided":     r["primary_p_blockperm_1s"],
            "bh_fdr_q_20d":           float(q),
            "nw_tstat":               round(r["primary_nw_tstat"], 3),
            "nw_p_two":               r["primary_nw_p_two"],
            "direction_verdict_formal":  r["direction_verdict_formal"],
            "direction_across_horizons": r["direction_across_horizons"],
            # Filtered-labels parallel (post-hoc, §9.6 hysteresis-impact)
            "H_stat_filtered":           round(r["H_stat_filtered"], 2)
                                          if not np.isnan(r["H_stat_filtered"]) else np.nan,
            "p_value_filtered":          r["p_value_filtered"],
            "paradox_direction_filtered": r["direction_filtered"],
            "det_mean_vol_filtered":     round(r["regime_mean_vol_filtered"]["Deterministic"], 2),
            "sto_mean_vol_filtered":     round(r["regime_mean_vol_filtered"]["Stochastic"], 2),
            "p_det_filtered":            round(r["regime_share_filtered"]["Deterministic"], 3),
            "p_tra_filtered":            round(r["regime_share_filtered"]["Transitional"], 3),
            "p_sto_filtered":            round(r["regime_share_filtered"]["Stochastic"], 3),
            "cliffs_delta_filtered":     round(r["primary_cliffs_delta_filtered"], 4),
            "delta_ci_lo_filtered":      round(r["primary_delta_ci_lo_filtered"], 4),
            "delta_ci_hi_filtered":      round(r["primary_delta_ci_hi_filtered"], 4),
            "p_det_sto_1sided_filtered": r["primary_p_mw_1sided_filtered"],
            "bh_fdr_q_20d_filtered":     float(q_f),
            "direction_verdict_formal_filtered": r["direction_verdict_formal_filtered"],
        })
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "cross_market_summary_v2.csv")
    df.to_csv(path, index=False)
    print(f"\nSummary CSV: {path}")
    return df


def build_horizons_csv(results: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    # BH-FDR per horizon across markets
    by_h: dict[int, list[tuple[int, float]]] = {h: [] for h in HORIZONS}
    for mi, r in enumerate(results):
        for hrow in r["horizons"]:
            by_h[hrow["horizon_days"]].append((mi, hrow["p_mw_1sided"]))
    q_map: dict[tuple[int, int], float] = {}
    for h, entries in by_h.items():
        p_arr = np.array([e[1] for e in entries], dtype=float)
        q_arr = _bh_fdr(p_arr)
        for (mi, _), q in zip(entries, q_arr):
            q_map[(mi, h)] = float(q)

    for mi, r in enumerate(results):
        for hrow in r["horizons"]:
            q = q_map.get((mi, hrow["horizon_days"]), float("nan"))
            rows.append({
                "market": r["market"],
                "category": r["category"],
                "horizon_days": hrow["horizon_days"],
                "n_det": hrow["n_det"], "n_sto": hrow["n_sto"],
                "mean_det": round(hrow["mean_det"], 3),
                "mean_sto": round(hrow["mean_sto"], 3),
                "cliffs_delta": round(hrow["cliffs_delta"], 4),
                "delta_ci_lo": round(hrow["delta_ci_lo"], 4),
                "delta_ci_hi": round(hrow["delta_ci_hi"], 4),
                "U_det_sto": hrow["U_det_sto"],
                "p_mw_1sided": hrow["p_mw_1sided"],
                "p_blockperm_1sided": hrow["p_blockperm_1sided"],
                "bh_fdr_q": q,
                "nw_tstat": round(hrow["nw_tstat"], 3),
                "nw_p_two": hrow["nw_p_two"],
                "direction_verdict_formal": hrow["direction_verdict_formal"],
            })
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "cross_market_h1_horizons.csv")
    df.to_csv(path, index=False)
    print(f"Horizons CSV: {path}")
    return df


def plot_horizon_heatmap(horizons_df: pd.DataFrame, market_order: list[str]) -> None:
    """Heatmap of Cliff's delta across (market x horizon)."""
    pivot = horizons_df.pivot(index="market", columns="horizon_days", values="cliffs_delta")
    pivot = pivot.reindex(index=market_order, columns=HORIZONS)
    sig_pivot = horizons_df.pivot(index="market", columns="horizon_days",
                                  values="direction_verdict_formal")
    sig_pivot = sig_pivot.reindex(index=market_order, columns=HORIZONS)

    fig, ax = plt.subplots(figsize=(8, 6))
    vmax = float(np.nanmax(np.abs(pivot.values)))
    im = ax.imshow(pivot.values, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(HORIZONS))); ax.set_xticklabels([f"{h}d" for h in HORIZONS])
    ax.set_yticks(range(len(market_order))); ax.set_yticklabels(market_order)
    ax.set_xlabel("Forward-vol horizon")
    ax.set_title("Cliff's δ (Det vs Sto) across markets & horizons\n"
                 "★ = CI excludes 0 (Paradox / Inverted); blank = n.s.")
    for i, m in enumerate(market_order):
        for j, h in enumerate(HORIZONS):
            val = pivot.values[i, j]
            verdict = sig_pivot.values[i, j]
            if np.isnan(val):
                continue
            mark = "★" if verdict in ("Paradox", "Inverted") else ""
            ax.text(j, i, f"{val:+.2f}{mark}", ha="center", va="center",
                    fontsize=8, color="black" if abs(val) < 0.6 * vmax else "white")
    fig.colorbar(im, ax=ax, label="Cliff's δ")
    plt.tight_layout()
    out = os.path.join(OUTPUT_DIR, "cross_market_h1_horizons.png")
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Horizon heatmap: {out}")


def plot_boxplots(results_with_dfs: list[tuple[dict, pd.DataFrame]]) -> None:
    n = len(results_with_dfs)
    if n == 0:
        return
    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4.5, rows * 4.2), squeeze=False)
    for idx, (meta, df) in enumerate(results_with_dfs):
        ax = axes[idx // cols][idx % cols]
        present = [r for r in REGIME_ORDER if r in df["RegimeName"].unique()]
        data = [df.loc[df["RegimeName"] == r, "FwdVol20d"].dropna().values for r in present]
        bp = ax.boxplot(data, tick_labels=present, patch_artist=True, showfliers=False)
        for patch, lbl in zip(bp["boxes"], present):
            patch.set_facecolor(REGIME_PALETTE[lbl]); patch.set_alpha(0.7)
        H = meta["H_stat"]
        verdict = meta["direction_verdict_formal"]
        ax.set_title(f"{meta['market']} ({meta['category']})\nH={H:.1f}  δ={meta['primary_cliffs_delta']:.2f}  {verdict}")
        ax.set_ylabel("Fwd 20d Vol (%)"); ax.grid(axis="y", alpha=0.3)
        ax.tick_params(axis="x", rotation=20, labelsize=8)
    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].axis("off")
    fig.suptitle("Cross-Market Entropy Paradox — V2 Combined (rolling SPE_Z) + Formal Verdict",
                 fontsize=13, y=1.00)
    plt.tight_layout()
    out = os.path.join(OUTPUT_DIR, "cross_market_validation_v2.png")
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Figure: {out}")


def plot_h_vs_rps(results: list[dict]) -> None:
    xs = [r["rps"] for r in results]
    ys = [r["H_stat"] for r in results]
    labels = [r["market"] for r in results]
    cats = [r["category"] for r in results]
    cat_colors = {"Frontier": "#c0392b", "Emerging": "#d35400",
                  "Developed": "#2980b9", "Crypto": "#8e44ad"}
    fig, ax = plt.subplots(figsize=(8, 6))
    for x, y, lbl, cat in zip(xs, ys, labels, cats):
        ax.scatter(x, y, color=cat_colors.get(cat, "gray"), s=100, alpha=0.8,
                   edgecolor="black", linewidth=1.0, label=cat)
        ax.annotate(lbl, (x, y), xytext=(5, 5), textcoords="offset points", fontsize=9)
    handles, lbls = ax.get_legend_handles_labels()
    uniq = dict(zip(lbls, handles))
    ax.legend(uniq.values(), uniq.keys(), loc="best")
    rho, p_spear = spearmanr(xs, ys)
    ax.set_xlabel("Retail Participation Share (RPS) — share of trading value")
    ax.set_ylabel("Kruskal–Wallis H (log scale)")
    ax.set_yscale("symlog", linthresh=1.0); ax.grid(alpha=0.3)
    ax.set_title(f"H vs RPS (H2 primary): Spearman ρ = {rho:.2f}  p = {p_spear:.3f}")
    out = os.path.join(OUTPUT_DIR, "h_vs_rps_v2.png")
    plt.tight_layout()
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"H vs RPS: {out}  (Spearman ρ={rho:.2f}, p={p_spear:.3f})")


# ==============================================================================
# REGRESSION ASSERTION (legacy cols vs archived pre-reg)
# ==============================================================================
def assert_legacy_unchanged(new_summary: pd.DataFrame) -> None:
    """Guard the pre-registered legacy columns (see validation/_regression_guard)."""
    _reg_guard(
        new_summary, "cross_market_summary_v2.csv",
        num_cols=["H_stat", "p_value", "det_mean_vol", "sto_mean_vol",
                  "trans_mean_vol"],
        str_cols=["paradox_direction"],
    )
# ==============================================================================
# MAIN
# ==============================================================================
def main() -> None:
    print("=" * 78)
    print("CROSS-MARKET ENTROPY PARADOX — V2 COMBINED, H1 SCIENTIFICALLY REFINED")
    print(f"Pre-registration commit: b130b0f1f2769566eaf548181d6816eb31b1963e")
    print(f"Window: {START} → {END}   n_markets: {len(MARKETS)}")
    print(f"Horizons: {HORIZONS}   BLOCK={BLOCK}  N_BOOT={N_BOOT}  N_PERM={N_PERM}")
    print("=" * 78)

    results: list[dict] = []
    boxplot_pairs: list[tuple[dict, pd.DataFrame]] = []

    for cfg in MARKETS:
        res = analyze_market(cfg)
        if res is None:
            continue
        save_per_market_json(res)
        results.append(res)
        # Reuse cached pipeline for plotting
        out = run_full_pipeline(
            market=res["market"], ticker=cfg["ticker"],
            source=cfg["source"], start=START, end=END,
        )
        labels = out["raw_labels"]
        fwd = compute_forward_metrics(out["ohlcv"], horizon=20)
        df_plot = pd.DataFrame({"Label": labels.astype(int)}, index=labels.index)
        df_plot["RegimeName"] = df_plot["Label"].map(REGIME_NAMES)
        df_plot = df_plot.join(fwd, how="left")
        boxplot_pairs.append((res, df_plot))

    if not results:
        print("\n[FATAL] no markets produced valid results.")
        return

    summary = build_summary_csv(results)
    horizons_df = build_horizons_csv(results)
    plot_boxplots(boxplot_pairs)
    plot_h_vs_rps(results)
    plot_horizon_heatmap(horizons_df, [r["market"] for r in results])

    print("\n" + "=" * 78)
    print("SUMMARY — PHASE 1 CROSS-MARKET RESULTS (legacy + refined)")
    print("=" * 78)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    print(summary[[
        "market", "category", "H_stat", "p_value",
        "kw_epsilon_sq", "cliffs_delta", "delta_ci_lo", "delta_ci_hi",
        "p_det_sto_1sided", "bh_fdr_q_20d",
        "direction_verdict_formal", "direction_across_horizons",
    ]].to_string(index=False))

    print("\n[regression] checking legacy columns against pre-reg archive...")
    assert_legacy_unchanged(summary)

    print("\nDone.")


if __name__ == "__main__":
    main()
