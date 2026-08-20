"""
H2 KW H statistic + η² effect size on the n=27 expansion panel.

Computes per-market H_raw, H_filt, η²_raw, η²_filt + cross-market Spearman ρ
against tier_rank (MSCI) and against RPS (point estimates from CASCADE_N27;
P3 markets use Beta posterior mean as point estimate for the Spearman test).

For comparison with paper canonical n=8 results:
  Paper: ρ(H_raw, tier) = 0.927 (p=0.001); ρ(H_filt, tier) = 0.890
  Paper: ρ(H_raw, RPS)  = 0.857; ρ(H_filt, RPS)  = 0.905
  Paper: ρ(η²_raw, tier) = 0.964; ρ(η²_raw, RPS) = 0.810

Output: validation/results_v2/n27_experiment/h2_eta_squared_n27.json

Usage:
    python validation/h2_eta_squared_n27.py

Estimated runtime: ~10-15 minutes (data fetch + GMM fit per market; no DML).
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy.stats import kruskal, spearmanr

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from validation._features import run_full_pipeline, SPE_Z_WIN
from skills.ds_skill import REGIME_NAMES
from validation.markets_n27 import MARKETS_N27, CASCADE_N27, panel_summary

START = "2018-01-01"
END = "2026-06-30"
HORIZON = 20
RNG_SEED = 42

OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2", "n27_experiment")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def compute_h_for_market(name: str, ticker: str, source: str) -> dict | None:
    try:
        out = run_full_pipeline(market=name, ticker=ticker, source=source, start=START, end=END)
    except Exception as e:
        print(f"  [SKIP-fetch] {type(e).__name__}: {e}")
        return {"market": name, "skip_reason": f"fetch_failed: {type(e).__name__}: {e}"}

    ohlcv = out["ohlcv"]
    raw_labels = out.get("raw_labels")
    filt_labels = out.get("filtered_labels")
    if raw_labels is None or filt_labels is None or len(filt_labels) < SPE_Z_WIN:
        return {"market": name, "skip_reason": "insufficient_bars"}

    # Forward 20-day realised vol (log returns)
    log_ret = np.log(ohlcv["Close"].astype(float) / ohlcv["Close"].astype(float).shift(1))
    fwd_vol = (log_ret.shift(-1).rolling(HORIZON).std()
                       .shift(-(HORIZON - 1)) * np.sqrt(252) * 100.0)

    # Align raw and filtered labels with fwd_vol
    df_raw = pd.DataFrame({"label": raw_labels.reindex(ohlcv.index), "fwd_vol": fwd_vol}).dropna()
    df_filt = pd.DataFrame({"label": filt_labels.reindex(ohlcv.index), "fwd_vol": fwd_vol}).dropna()

    def kw_eta(df: pd.DataFrame) -> dict:
        groups = [df.loc[df["label"] == k, "fwd_vol"].values for k in (0, 1, 2)]
        groups = [g for g in groups if len(g) > 0]
        if len(groups) < 2:
            return {"H_stat": float("nan"), "eta_sq": float("nan"), "N_obs": int(len(df))}
        kw = kruskal(*groups)
        H = float(kw.statistic)
        N = int(len(df))
        k = len(groups)
        eta = (H - k + 1) / max(N - k, 1)
        eta = max(0.0, eta)
        n_per_regime = {REGIME_NAMES.get(int(lbl), str(int(lbl))): int((df["label"] == lbl).sum())
                        for lbl in (0, 1, 2)}
        return {"H_stat": H, "p_value": float(kw.pvalue), "eta_sq": float(eta),
                "N_obs": N, "n_per_regime": n_per_regime}

    raw_res = kw_eta(df_raw)
    filt_res = kw_eta(df_filt)

    return {"market": name, "raw": raw_res, "filtered": filt_res}


def cross_market_spearman(per_market: dict, markets: list[dict],
                          rps_values: dict[str, float]) -> dict:
    """Compute ρ(H, tier_rank), ρ(H, RPS), ρ(η², tier_rank), ρ(η², RPS) on raw + filtered."""
    out = {}
    for label_src in ("raw", "filtered"):
        H = []
        eta = []
        tiers = []
        rps = []
        for m in markets:
            name = m["name"]
            if name not in per_market or "skip_reason" in per_market[name]:
                continue
            r = per_market[name][label_src]
            if not np.isfinite(r["H_stat"]):
                continue
            H.append(r["H_stat"])
            eta.append(r["eta_sq"])
            tiers.append(m["tier_rank"])
            rps.append(rps_values[name])
        n = len(H)
        if n < 3:
            out[label_src] = {"n": n, "error": "insufficient_markets"}
            continue
        rH_t = spearmanr(H, tiers)
        rE_t = spearmanr(eta, tiers)
        rH_r = spearmanr(H, rps)
        rE_r = spearmanr(eta, rps)
        out[label_src] = {
            "n": n,
            "rho_H_tier":   float(rH_t.statistic),  "p_H_tier":   float(rH_t.pvalue),
            "rho_eta_tier": float(rE_t.statistic),  "p_eta_tier": float(rE_t.pvalue),
            "rho_H_rps":    float(rH_r.statistic),  "p_H_rps":    float(rH_r.pvalue),
            "rho_eta_rps":  float(rE_r.statistic),  "p_eta_rps":  float(rE_r.pvalue),
        }
    return out


def main() -> int:
    print("=" * 70)
    print("  H2 KW H + η² — n=27 EXPANSION PANEL")
    print("=" * 70)
    print(panel_summary())
    print()

    # RPS point estimate per market: P1 = value, P2 = midpoint, P3 = Beta mean
    rps_point = {}
    for name, spec in CASCADE_N27.items():
        if spec["type"] == "point":
            rps_point[name] = spec["value"]
        elif spec["type"] == "uniform":
            rps_point[name] = 0.5 * (spec["low"] + spec["high"])
        elif spec["type"] == "beta":
            rps_point[name] = spec["mean"]

    per_market: dict[str, dict] = {}
    t_start = time.time()
    for cfg in MARKETS_N27:
        name = cfg["name"]
        print(f"\n[{name}] {cfg['ticker']} via {cfg['source']} ({cfg['category']})")
        res = compute_h_for_market(name, cfg["ticker"], cfg["source"])
        if res is None:
            continue
        per_market[name] = res
        if "skip_reason" in res:
            print(f"  [SKIPPED] {res['skip_reason']}")
            continue
        raw = res["raw"]
        filt = res["filtered"]
        print(f"  raw : H={raw['H_stat']:.2f} η²={raw['eta_sq']:.4f} N={raw['N_obs']} (Det={raw['n_per_regime'].get('Deterministic',0)}, Trans={raw['n_per_regime'].get('Transitional',0)}, Sto={raw['n_per_regime'].get('Stochastic',0)})")
        print(f"  filt: H={filt['H_stat']:.2f} η²={filt['eta_sq']:.4f}")

    cross = cross_market_spearman(per_market, MARKETS_N27, rps_point)

    print("\n" + "=" * 70)
    print("  CROSS-MARKET SPEARMAN ρ (n=27)")
    print("=" * 70)
    for label_src in ("raw", "filtered"):
        c = cross.get(label_src, {})
        if "error" in c:
            print(f"  {label_src}: {c['error']} (n={c.get('n', 0)})")
            continue
        print(f"  {label_src} labels (n={c['n']}):")
        print(f"    ρ(H, tier_rank)  = {c['rho_H_tier']:+.4f} (p = {c['p_H_tier']:.4f})")
        print(f"    ρ(η², tier_rank) = {c['rho_eta_tier']:+.4f} (p = {c['p_eta_tier']:.4f})")
        print(f"    ρ(H, RPS)        = {c['rho_H_rps']:+.4f} (p = {c['p_H_rps']:.4f})")
        print(f"    ρ(η², RPS)       = {c['rho_eta_rps']:+.4f} (p = {c['p_eta_rps']:.4f})")

    print()
    print("  Paper canonical n=8 reference:")
    print("    raw  : ρ(H, tier)=0.927 (p=0.001), ρ(H, RPS)=0.857 (p=0.007)")
    print("    raw  : ρ(η², tier)=0.964 (p=0.0001), ρ(η², RPS)=0.810")
    print("    filt : ρ(H, tier)=0.890 (p=0.003), ρ(H, RPS)=0.905")

    payload = {
        "spec": "H2 KW H + η² on n=27 expansion panel",
        "panel": "n27_experiment",
        "n_markets_attempted": len(MARKETS_N27),
        "n_markets_succeeded": sum(1 for r in per_market.values() if "skip_reason" not in r),
        "horizon": HORIZON,
        "rps_point_estimates": rps_point,
        "per_market": per_market,
        "cross_market": cross,
        "elapsed_seconds": float(time.time() - t_start),
        "paper_n8_reference": {
            "raw": {"rho_H_tier": 0.927, "rho_eta_tier": 0.964, "rho_H_rps": 0.857},
            "filtered": {"rho_H_tier": 0.890, "rho_H_rps": 0.905},
        },
    }
    out_path = os.path.join(OUTPUT_DIR, "h2_eta_squared_n27.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\n  JSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
