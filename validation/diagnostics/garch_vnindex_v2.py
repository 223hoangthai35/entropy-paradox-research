"""
Paper v1 V2 (GARCH benchmarking) — redo on VNINDEX under the v2.1 feature
recipe and the canonical 2020-01-01 -> 2026-04-17 post-COVID window.

This is the §12.2 appendix of paper v2.1: an exploratory robustness redo of
the original `validation/garch_forecast_eval.py` (frozen at v1.0-paper).
The original used the v7.0 pipeline (`get_latest_market_data` + global
SPE_Z, no hysteresis); this script uses `validation._features.run_full_pipeline`
so the OHLCV preprocessing is identical to the rest of v2.1's panel.

The test itself is regime-agnostic — GARCH(1,1) and Rolling22 do not consume
the regime labels. Inclusion in §12 is purely to refresh the v1 V2 numbers
under v2.1's window.

Method:
  1. run_full_pipeline("VNINDEX") -> ohlcv DataFrame, 2020-01-01 -> 2026-04-17.
  2. Rolling 504-day train, 1-step-ahead forecast.
       GARCH(1,1) via arch.arch_model (mean=Zero, vol=Garch, p=1, q=1, Normal).
       Rolling22 baseline = std of last 22 log returns.
  3. QLIKE = mean(u - log(u) - 1) where u = r_t^2 / sigma_hat_t^2 (Patton 2011).
     MSE   = mean((sigma_hat_t - |r_t|)^2).
     Pearson(sigma_hat, |r|).

Outputs (validation/results_v2/):
  - garch_vnindex_v2.json  : single-row metrics dict.
  - garch_vnindex_v2.png   : sigma forecast vs |r| + cumulative QLIKE advantage.

Run:
  python validation/garch_vnindex_v2.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from arch import arch_model

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from validation._features import run_full_pipeline


MARKET = "VNINDEX"
TICKER = "VNINDEX"
SOURCE = "vnstock"
START  = "2020-01-01"
END    = "2026-06-30"

TRAIN_WINDOW = 504
ROLL_BENCH   = 22

OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def qlike(realized_sq: np.ndarray, forecast_sq: np.ndarray) -> float:
    forecast_sq = np.clip(forecast_sq, 1e-12, None)
    ratio = np.clip(realized_sq / forecast_sq, 1e-12, None)
    return float(np.mean(ratio - np.log(ratio) - 1))


def run_rolling_forecast(log_rets_pct: pd.Series) -> pd.DataFrame:
    n = len(log_rets_pct)
    rows: list[dict] = []
    for t in range(TRAIN_WINDOW, n - 1):
        train = log_rets_pct.iloc[t - TRAIN_WINDOW: t]
        actual_return = log_rets_pct.iloc[t]
        try:
            am = arch_model(train, mean="Zero", vol="Garch", p=1, q=1, dist="Normal")
            res = am.fit(disp="off", options={"maxiter": 300})
            fc = res.forecast(horizon=1)
            sigma_forecast = float(fc.variance.iloc[-1, 0] ** 0.5)
        except Exception:
            continue
        rows.append({
            "date":              log_rets_pct.index[t],
            "actual_return":     float(actual_return),
            "actual_sq_return":  float(actual_return ** 2),
            "sigma_forecast":    sigma_forecast,
            "sigma_sq_forecast": sigma_forecast ** 2,
        })
        if len(rows) % 200 == 0:
            print(f"  ... {len(rows)} forecasts")
    return pd.DataFrame(rows).set_index("date")


def add_benchmark(res_df: pd.DataFrame, log_rets_pct: pd.Series) -> pd.DataFrame:
    rolling_std = log_rets_pct.rolling(ROLL_BENCH).std()
    res_df["benchmark_sigma"] = rolling_std.reindex(res_df.index).values
    res_df = res_df.dropna(subset=["benchmark_sigma"]).copy()
    res_df["benchmark_sigma"] = res_df["benchmark_sigma"].clip(lower=1e-8)
    return res_df


def evaluate(res_df: pd.DataFrame) -> dict:
    r2 = res_df["actual_sq_return"].values
    g2 = res_df["sigma_sq_forecast"].values
    b2 = res_df["benchmark_sigma"].values ** 2
    qlike_garch = qlike(r2, g2)
    qlike_bench = qlike(r2, b2)
    mse_garch = float(np.mean((np.sqrt(g2) - np.abs(res_df["actual_return"].values)) ** 2))
    mse_bench = float(np.mean((np.sqrt(b2) - np.abs(res_df["actual_return"].values)) ** 2))
    pearson_garch = float(res_df["sigma_forecast"].corr(res_df["actual_return"].abs()))
    pearson_bench = float(res_df["benchmark_sigma"].corr(res_df["actual_return"].abs()))
    advantage_pp = (qlike_bench - qlike_garch) / qlike_bench * 100.0 if qlike_bench != 0 else float("nan")
    return {
        "qlike_garch":       qlike_garch,
        "qlike_roll22":      qlike_bench,
        "qlike_advantage_pp": float(advantage_pp),
        "mse_garch":         mse_garch,
        "mse_roll22":        mse_bench,
        "pearson_garch":     pearson_garch,
        "pearson_roll22":    pearson_bench,
    }


def plot_results(res_df: pd.DataFrame, metrics: dict, out_path: str) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    axes[0].plot(res_df.index, res_df["actual_return"].abs(),
                 alpha=0.30, color="#888888", linewidth=0.7, label="|Actual return| (%)")
    axes[0].plot(res_df.index, res_df["sigma_forecast"],
                 color="#d35400", linewidth=1.0, label="GARCH(1,1) σ̂")
    axes[0].plot(res_df.index, res_df["benchmark_sigma"],
                 color="#2980b9", linewidth=0.9, alpha=0.7, label="Rolling-22 σ̂")
    axes[0].legend(loc="upper right", fontsize=9)
    axes[0].set_ylabel("Volatility (% / day)")
    axes[0].set_title(f"VNINDEX out-of-sample σ̂ forecast — train={TRAIN_WINDOW}d, window {START} → {END}")
    axes[0].grid(alpha=0.25)

    g2 = res_df["sigma_sq_forecast"].values.clip(1e-12)
    b2 = (res_df["benchmark_sigma"].values ** 2).clip(1e-12)
    r2 = res_df["actual_sq_return"].values

    def pointwise_q(r2_arr, s2_arr):
        ratio = np.clip(r2_arr / s2_arr, 1e-12, None)
        return ratio - np.log(ratio) - 1

    cum = (pointwise_q(r2, b2) - pointwise_q(r2, g2)).cumsum()
    axes[1].plot(res_df.index, cum, color="#27ae60", linewidth=1.1)
    axes[1].axhline(0.0, color="#555", linestyle="--", alpha=0.5, linewidth=0.8)
    axes[1].fill_between(res_df.index, cum, 0, where=(cum > 0), alpha=0.18, color="#27ae60")
    axes[1].fill_between(res_df.index, cum, 0, where=(cum < 0), alpha=0.18, color="#c0392b")
    axes[1].set_ylabel("Cumulative QLIKE advantage")
    axes[1].set_title(
        f"GARCH advantage over Rolling-22 (positive = GARCH lower QLIKE) | "
        f"QLIKE_GARCH={metrics['qlike_garch']:.4f}  Roll22={metrics['qlike_roll22']:.4f}  "
        f"adv={metrics['qlike_advantage_pp']:+.2f}%"
    )
    axes[1].grid(alpha=0.25)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def main() -> None:
    print(f"[1/4] Loading {MARKET} via run_full_pipeline ({START} → {END})")
    pipe = run_full_pipeline(MARKET, TICKER, SOURCE, start=START, end=END)
    ohlcv = pipe["ohlcv"]
    log_rets_pct = (np.log(ohlcv["Close"] / ohlcv["Close"].shift(1)).dropna() * 100.0)
    print(f"      bars {len(log_rets_pct)}  [{log_rets_pct.index[0].date()} → {log_rets_pct.index[-1].date()}]")

    print(f"[2/4] Rolling GARCH(1,1) forecast (train={TRAIN_WINDOW}d, step=1)")
    res_df = run_rolling_forecast(log_rets_pct)
    res_df = add_benchmark(res_df, log_rets_pct)
    print(f"      n_forecast = {len(res_df)}")

    print("[3/4] Computing QLIKE / MSE / Pearson")
    metrics = evaluate(res_df)
    out = {
        "market":       MARKET,
        "window":       f"{START} → {END}",
        "train_window": TRAIN_WINDOW,
        "n_forecast":   int(len(res_df)),
        **metrics,
    }
    print(json.dumps(out, indent=2))

    json_path = os.path.join(OUTPUT_DIR, "diagnostics/garch_vnindex_v2.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"      JSON saved: {json_path}")

    print("[4/4] Plotting")
    png_path = os.path.join(OUTPUT_DIR, "diagnostics/garch_vnindex_v2.png")
    plot_results(res_df, metrics, png_path)
    print(f"      PNG saved: {png_path}")


if __name__ == "__main__":
    main()
