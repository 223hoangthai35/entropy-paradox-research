"""
OOS 2026-Q2 — H2 ALTERNATIVE ESTIMATORS DEMO (exploratory, NOT pre-registered).

Motivation (see outputs/oos-2026q2-extension.md §7b): the cascade wraps RPS
measurement uncertainty around a Spearman of 8 fine ranks of KW-H point
estimates. Bottom-half markets sit at the KW noise floor (η² ≈ 1e-3), so
their ranks are noise and the cascade conclusion statistic P(ρ>0.5) is
fragile (80.9% → 9.6% raw with +2.5 months of data).

Three candidate replacements, all cascade-compatible, demoed on the repro
(2026-04-17) and extended (2026-06-30) windows:

  (A) Cascade-native errors-in-variables meta-regression:
        y_m = log10(η²_m + 1e-4)  with within-market circular-block-bootstrap
        uncertainty;  x_m = RPS with the cascade P1/P2/P3 prior.
        Per MC draw: sample y from each market's bootstrap distribution,
        sample RPS from the cascade, fit precision-weighted WLS.
        Conclusion statistic: posterior-style P(β > 0) and 95% CI on β.
        Noise-floor markets get wide SEs → automatically down-weighted.
  (B) Precision-weighted Kendall τ: same draws, τ_w with pair weights
        w_i·w_j (w = 1/Var_boot). Minimal-change upgrade of the rank test.
  (C) Jonckheere–Terpstra ordered-alternative test at TIER resolution
        (Developed < Crypto < Emerging < Frontier), permutation-exact.
        Matches the resolution of the pre-registered tier claim; no RPS
        draw needed (kept as the granularity benchmark).

Outputs: validation/results_v2/oos_2026q2/h2_alt_estimators.json + console.
Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/oos_2026q2_h2_alt_estimators.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import kruskal

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import run_full_pipeline
from validation.cross_market_v2 import MARKETS, _circular_block_indices
from validation.h2_eta_squared import kw_eta_squared
from validation.h2_cascade import CASCADE, sample_rps_cascade

START = "2018-01-01"
WINDOWS = {"repro": "2026-04-17", "extended": "2026-06-30"}
TIER_RANK = {"VNINDEX": 4, "BVB": 4, "KOSPI": 3, "NIFTY": 3,
             "SPX": 1, "FTSE": 1, "NIKKEI": 1, "BTC": 2}

HORIZON = 20
BLOCK = 20
N_BOOT = 2000
N_MC = 10_000
N_PERM_JT = 20_000
EPS = 1e-4          # floor inside log10(η² + EPS); η² spans ~1e-4..0.08
RNG_SEED = 42

OOS_DIR = os.path.join(os.path.dirname(__file__), "results_v2", "oos_2026q2")
os.makedirs(OOS_DIR, exist_ok=True)


# ------------------------------------------------------------------
# Per-market: aligned (label, fwd_vol) arrays + block-bootstrap η² draws
# ------------------------------------------------------------------
def aligned_arrays(ohlcv: pd.DataFrame, labels: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    close = ohlcv["Close"].astype(float)
    log_ret = np.log(close / close.shift(1))
    fwd = (log_ret.shift(-1).rolling(HORIZON).std()
                  .shift(-(HORIZON - 1)) * np.sqrt(252) * 100.0)
    df = pd.DataFrame({"lab": labels.astype(int),
                       "fwd": fwd.reindex(labels.index)}).dropna()
    return df["lab"].to_numpy(), df["fwd"].to_numpy()


def kw_eta_point(lab: np.ndarray, fwd: np.ndarray) -> float:
    groups = [fwd[lab == k] for k in (0, 1, 2)]
    usable = [g for g in groups if len(g) >= 5]
    if len(usable) < 2:
        return float("nan")
    H, _ = kruskal(*usable)
    return kw_eta_squared(float(H), int(len(lab)), k=3)


def bootstrap_eta(lab: np.ndarray, fwd: np.ndarray, seed: int) -> np.ndarray:
    """Circular block bootstrap of η² (joint label+fwd resampling)."""
    n = len(lab)
    rng = np.random.default_rng(seed)
    idx = _circular_block_indices(n, BLOCK, N_BOOT, rng)      # (N_BOOT, n)
    out = np.full(N_BOOT, np.nan)
    for b in range(N_BOOT):
        lb, fb = lab[idx[b]], fwd[idx[b]]
        groups = [fb[lb == k] for k in (0, 1, 2)]
        usable = [g for g in groups if len(g) >= 5]
        if len(usable) < 2:
            continue
        H, _ = kruskal(*usable)
        out[b] = kw_eta_squared(float(H), n, k=3)
    return out[~np.isnan(out)]


# ------------------------------------------------------------------
# Cross-market estimators
# ------------------------------------------------------------------
def wls_slope(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    xm = np.sum(w * x) / np.sum(w)
    ym = np.sum(w * y) / np.sum(w)
    den = np.sum(w * (x - xm) ** 2)
    return float(np.sum(w * (x - xm) * (y - ym)) / den) if den > 0 else float("nan")


def weighted_kendall(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    num = den = 0.0
    n = len(x)
    for i in range(n):
        for j in range(i + 1, n):
            ww = w[i] * w[j]
            num += ww * np.sign(x[i] - x[j]) * np.sign(y[i] - y[j])
            den += ww
    return float(num / den) if den > 0 else float("nan")


def jonckheere(values: np.ndarray, tiers: np.ndarray,
               n_perm: int = N_PERM_JT, seed: int = RNG_SEED) -> dict:
    """JT statistic for ordered alternative (higher tier_rank → higher value),
    permutation p (one-sided)."""
    order = sorted(set(tiers))

    def jt(v: np.ndarray) -> float:
        s = 0.0
        for a_i in range(len(order)):
            for b_i in range(a_i + 1, len(order)):
                lo, hi = v[tiers == order[a_i]], v[tiers == order[b_i]]
                for xv in lo:
                    s += np.sum(hi > xv) + 0.5 * np.sum(hi == xv)
        return s

    obs = jt(values)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    v = values.copy()
    for i in range(n_perm):
        rng.shuffle(v)
        null[i] = jt(v)
    p = float((np.sum(null >= obs) + 1) / (n_perm + 1))
    return {"JT_obs": float(obs), "null_mean": float(null.mean()),
            "null_p95": float(np.percentile(null, 95)), "p_one_sided": p}


def mc_cross_market(y_boot: dict[str, np.ndarray], seed: int = RNG_SEED) -> dict:
    """MC over (RPS cascade draw, bootstrap y draw); WLS slope + weighted τ."""
    names = list(y_boot.keys())
    yb = {m: np.log10(y_boot[m] + EPS) for m in names}
    var = np.array([np.var(yb[m]) for m in names])
    w = 1.0 / np.maximum(var, 1e-6)
    w = w / w.sum()

    rng = np.random.default_rng(seed)
    betas = np.empty(N_MC)
    taus = np.empty(N_MC)
    for i in range(N_MC):
        x = np.array([sample_rps_cascade(m, rng) for m in names])
        y = np.array([yb[m][rng.integers(len(yb[m]))] for m in names])
        betas[i] = wls_slope(x, y, w)
        taus[i] = weighted_kendall(x, y, w)

    def summ(a: np.ndarray) -> dict:
        return {"mean": float(a.mean()), "sd": float(a.std(ddof=1)),
                "p025": float(np.percentile(a, 2.5)),
                "p975": float(np.percentile(a, 97.5)),
                "P_gt_0": float(np.mean(a > 0))}

    return {"weights": {m: float(wi) for m, wi in zip(names, w)},
            "beta_wls": summ(betas), "tau_weighted": summ(taus)}


# ------------------------------------------------------------------
def main() -> int:
    t0 = time.time()
    results: dict = {"spec": ("H2 alternative estimators demo: (A) cascade EIV "
                              "meta-regression on log10(eta2+1e-4), (B) precision-"
                              "weighted Kendall tau, (C) tier-level Jonckheere-"
                              "Terpstra. Exploratory, not pre-registered."),
                     "eps": EPS, "n_boot": N_BOOT, "n_mc": N_MC,
                     "windows": {}}

    for win, end in WINDOWS.items():
        print("=" * 74)
        print(f"  WINDOW [{win}]  {START} → {end}")
        print("=" * 74)
        eta_point: dict[str, dict[str, float]] = {}
        eta_boot: dict[str, dict[str, np.ndarray]] = {"raw": {}, "filt": {}}
        for i, cfg in enumerate(MARKETS):
            name = cfg["name"]
            out = run_full_pipeline(market=name, ticker=cfg["ticker"],
                                    source=cfg["source"], start=START, end=end)
            row = {}
            for lab_key, series in [("raw", out["raw_labels"]),
                                    ("filt", out["filtered_labels"])]:
                lab, fwd = aligned_arrays(out["ohlcv"], series)
                row[lab_key] = kw_eta_point(lab, fwd)
                eta_boot[lab_key][name] = bootstrap_eta(lab, fwd, seed=RNG_SEED + i)
            eta_point[name] = row
            print(f"  {name:<8} η²_raw={row['raw']:.5f}  η²_filt={row['filt']:.5f}  "
                  f"boot_n={len(eta_boot['filt'][name])}")

        win_res: dict = {"end": end, "eta_point": eta_point, "tests": {}}
        tiers = np.array([TIER_RANK[c["name"]] for c in MARKETS])
        for lab_key in ["raw", "filt"]:
            mc = mc_cross_market(eta_boot[lab_key])
            vals = np.array([eta_point[c["name"]][lab_key] for c in MARKETS])
            jt = jonckheere(vals, tiers)
            win_res["tests"][lab_key] = {"cascade_eiv": mc, "jt_tier": jt}
            b, t = mc["beta_wls"], mc["tau_weighted"]
            print(f"\n  [{lab_key}] (A) EIV-WLS β: mean={b['mean']:+.3f} "
                  f"95%CI[{b['p025']:+.3f},{b['p975']:+.3f}]  P(β>0)={b['P_gt_0']*100:.1f}%")
            print(f"  [{lab_key}] (B) weighted τ: mean={t['mean']:+.3f} "
                  f"95%CI[{t['p025']:+.3f},{t['p975']:+.3f}]  P(τ>0)={t['P_gt_0']*100:.1f}%")
            print(f"  [{lab_key}] (C) JT tier-ordered: JT={jt['JT_obs']:.1f} "
                  f"(null mean {jt['null_mean']:.1f}, p95 {jt['null_p95']:.1f})  "
                  f"p={jt['p_one_sided']:.4f}")
        results["windows"][win] = win_res

    out_path = os.path.join(OOS_DIR, "h2_alt_estimators.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\nJSON: {out_path}")
    print(f"total elapsed: {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
