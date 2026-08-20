"""HAR-RV economic-value test for regime labels (referee item B9).

Per market: expanding-window out-of-sample forecast of forward 20-day realized
variance with
  Model A (benchmark):  HAR — RV_daily, RV_weekly(5), RV_monthly(22)
  Model B (augmented):  HAR + regime dummies (Det, Sto; Trans = base) from the
                        canonical filtered labels
OLS refit every bar on the expanding window; OOS starts at 60% of the sample.
Loss: QLIKE and MSE on realized variance; Diebold–Mariano test on the loss
differential (HAC, lag = 20 to match target overlap). Cross-market question:
does the QLIKE gain scale with RPS?

Honest scope (§4.2, App J.4): labels are full-sample in-sample; this table
measures the economic value of the *measured* regime state, and the
walk-forward-label variant remains the flagged extension.

Output: validation/results_v2/harv_economic_value.json
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))
from validation._features import run_full_pipeline  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

START = "2018-01-01"
END = "2026-06-30"
ANALYSIS_START = "2020-01-01"
FWD_H = 20
OOS_FRAC = 0.60
REFIT_EVERY = 1

RES = os.path.join(_VALIDATION, "results_v2")
RPS_VALUES = json.load(open(os.path.join(
    RES, "n27_experiment", "h2_cascade_n27_full_classification.json"),
    encoding="utf-8"))["all_p1_reference"]["rps_values"]
N8 = ["VNINDEX", "BVB", "KOSPI", "NIFTY", "SPX", "FTSE", "NIKKEI", "BTC"]


def dm_test(l_a: np.ndarray, l_b: np.ndarray, lag: int = FWD_H) -> tuple[float, float]:
    """Diebold–Mariano with Newey–West variance (positive stat => B better)."""
    d = l_a - l_b
    n = len(d)
    dbar = d.mean()
    gamma0 = np.var(d, ddof=0)
    s = gamma0
    for k in range(1, lag + 1):
        cov = np.cov(d[k:], d[:-k], ddof=0)[0, 1]
        s += 2 * (1 - k / (lag + 1)) * cov
    dm = dbar / np.sqrt(s / n)
    p = 2 * (1 - stats.norm.cdf(abs(dm)))
    return float(dm), float(p)


def ols_forecast(X: np.ndarray, y: np.ndarray, x_new: np.ndarray) -> float:
    Xd = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    return float(np.concatenate([[1.0], x_new]) @ beta)


def run_market(cfg) -> dict | None:
    name = cfg["name"]
    try:
        out = run_full_pipeline(market=name, ticker=cfg["ticker"],
                                source=cfg["source"], start=START, end=END)
    except Exception as e:
        print(f"[{name}] SKIP: {type(e).__name__}: {e}")
        return None
    r = np.log(out["ohlcv"]["Close"]).diff()
    rv_d = r ** 2
    rv_w = rv_d.rolling(5).mean()
    rv_m = rv_d.rolling(22).mean()
    target = (r ** 2).rolling(FWD_H).mean().shift(-FWD_H)   # fwd 20d realized variance
    lab = out["filtered_labels"]
    df = pd.DataFrame({"y": target, "d": rv_d, "w": rv_w, "m": rv_m,
                       "det": (lab == 0).astype(float),
                       "sto": (lab == 2).astype(float)}).loc[ANALYSIS_START:].dropna()
    n = len(df)
    i0 = int(n * OOS_FRAC)
    if n - i0 < 100:
        print(f"[{name}] SKIP: OOS too short ({n - i0})")
        return None
    ya = np.empty(n - i0)
    yb = np.empty(n - i0)
    Y = df["y"].to_numpy()
    XA = df[["d", "w", "m"]].to_numpy()
    XB = df[["d", "w", "m", "det", "sto"]].to_numpy()
    for j, t in enumerate(range(i0, n)):
        ya[j] = max(ols_forecast(XA[:t], Y[:t], XA[t]), 1e-10)
        yb[j] = max(ols_forecast(XB[:t], Y[:t], XB[t]), 1e-10)
    yt = np.maximum(Y[i0:], 1e-10)
    qlike_a = np.log(ya) + yt / ya
    qlike_b = np.log(yb) + yt / yb
    mse_a = (ya - yt) ** 2
    mse_b = (yb - yt) ** 2
    dm_q, p_q = dm_test(qlike_a, qlike_b)
    gain_q = float(1 - qlike_b.mean() / qlike_a.mean()) if qlike_a.mean() != 0 else np.nan
    # QLIKE can be negative-mean; report loss-diff mean instead for robustness
    dq = float((qlike_a - qlike_b).mean())
    res = {"n_oos": int(n - i0),
           "qlike_A": float(qlike_a.mean()), "qlike_B": float(qlike_b.mean()),
           "qlike_diff_A_minus_B": dq, "qlike_gain_frac": gain_q,
           "mse_ratio_B_over_A": float(mse_b.mean() / mse_a.mean()),
           "dm_stat_qlike": dm_q, "dm_p_qlike": p_q}
    print(f"[{name}] OOS n={res['n_oos']}  dQLIKE(A−B)={dq:+.4f}  "
          f"MSE B/A={res['mse_ratio_B_over_A']:.3f}  DM={dm_q:+.2f} (p={p_q:.3f})")
    return res


def main() -> int:
    t0 = time.time()
    per_market = {}
    for cfg in MARKETS_N27:
        if cfg["name"] not in N8:
            continue
        res = run_market(cfg)
        if res:
            per_market[cfg["name"]] = res
    ms = list(per_market)
    gains = [per_market[m]["qlike_diff_A_minus_B"] for m in ms]
    rho, p = stats.spearmanr(gains, [RPS_VALUES[m] for m in ms])
    print(f"rho(QLIKE gain, RPS) = {rho:+.3f} (p = {p:.4f}, n = {len(ms)})")
    doc = {"spec": ("HAR-RV economic value: expanding-window OOS (start 60%), OLS refit "
                    "per bar; Model A = HAR(d,w,m), Model B = A + filtered regime dummies "
                    "(Det, Sto; Trans base); QLIKE + MSE on fwd 20d realized variance; "
                    "DM with NW lag 20. In-sample labels — disclosed."),
           "window": [ANALYSIS_START, END], "oos_frac": OOS_FRAC,
           "per_market": per_market,
           "cross_market": {"rho_qlikegain_rps": float(rho), "p": float(p), "n": len(ms)},
           "elapsed_min": round((time.time() - t0) / 60, 1)}
    path = os.path.join(RES, "harv_economic_value.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, default=float)
    print("JSON:", path, f"({doc['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
