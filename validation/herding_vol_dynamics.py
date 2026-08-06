"""Does retail participation act on VOLATILITY DYNAMICS rather than on trend?

An earlier test rejected the trend-coherence channel: no coherence statistic
(variance ratio, return autocorrelation, run length) correlates with retail
participation, and none attenuates the RPS-informativeness association.

That rejects one mechanism, not the behavioural reading. A second and quite
different channel is available: retail flow may not make prices trend, but may
make a market's VOLATILITY more state-contingent -- calm periods calmer,
stressed periods more stressed, and the transition between them sharper. Under
that reading, a regime label in a retail-heavy market is informative not because
the price path is smoother but because the two volatility states it points at
are further apart and last longer.

This is testable on the same series. Statistics, all on daily log returns and
the 20-day forward realized volatility the paper already uses:

  absret_ac1   first-order autocorrelation of |returns| -- classic volatility
               clustering; higher means volatility states persist
  vol_ac1      AR(1) of log realized volatility -- the same idea measured on the
               outcome variable itself
  vol_of_vol   standard deviation of log realized volatility
  vol_spread   log(p90/p10) of realized volatility -- how far the calm and
               stressed states sit apart
  regime_dur   mean filtered regime duration in days, from the hysteresis output

Same three questions as before: does the statistic rise with RPS, does it rise
with informativeness, and does controlling for it attenuate the headline?
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from validation._features import load_ohlcv  # noqa: E402
from validation.h1_dml import START, END, PRIMARY_HORIZON  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

R = os.path.join(os.path.dirname(__file__), "results_v2")
OUT_JSON = os.path.join(R, "n27_experiment", "herding_vol_dynamics.json")

eta = json.load(io.open(os.path.join(R, "n27_experiment",
                                     "h2_eta_squared_n27.json"), encoding="utf-8"))
RPS, PER = eta["rps_point_estimates"], eta["per_market"]
CAT = {c["name"]: c["category"] for c in MARKETS_N27}

# Mean filtered regime duration, from the already-computed hysteresis output.
DUR = {}
_h5 = os.path.join(R, "n27_experiment", "h5_n27.csv")
if os.path.exists(_h5):
    _d = pd.read_csv(_h5)
    for _, r in _d[_d["config"] == "A_current"].iterrows():
        DUR[r["market"]] = float(r["overall_d"])


def partial_spearman(x, y, z):
    rx, ry, rz = (stats.rankdata(v).astype(float) for v in (x, y, z))
    Z = np.column_stack([np.ones(len(rz)), rz])
    ex = rx - Z @ np.linalg.lstsq(Z, rx, rcond=None)[0]
    ey = ry - Z @ np.linalg.lstsq(Z, ry, rcond=None)[0]
    r = float(np.corrcoef(ex, ey)[0, 1])
    df = len(rx) - 3
    t = r * np.sqrt(df / max(1e-12, 1 - r ** 2))
    return r, float(2 * stats.t.sf(abs(t), df))


def main() -> int:
    t0 = time.time()
    per: dict[str, dict] = {}
    for cfg in MARKETS_N27:
        name = cfg["name"]
        if name not in PER:
            continue
        try:
            df = load_ohlcv(name, cfg["ticker"], cfg["source"], START, END)
        except Exception as e:
            print(f"[{name}] SKIP {type(e).__name__}: {e}")
            continue
        c = df["Close"].astype(float)
        r = np.log(c / c.shift(1)).dropna()
        rv = (r.rolling(PRIMARY_HORIZON).std() * np.sqrt(252) * 100).dropna()
        lrv = np.log(rv[rv > 0])
        a = np.abs(r.values)
        per[name] = {
            "category": CAT.get(name), "rps": RPS[name],
            "H_raw": PER[name]["raw"]["H_stat"],
            "H_filt": PER[name]["filtered"]["H_stat"],
            "absret_ac1": float(np.corrcoef(a[:-1], a[1:])[0, 1]),
            "vol_ac1": float(np.corrcoef(lrv.values[:-1], lrv.values[1:])[0, 1]),
            "vol_of_vol": float(lrv.std(ddof=1)),
            "vol_spread": float(np.log(np.percentile(rv, 90) / np.percentile(rv, 10))),
            "regime_dur": DUR.get(name, np.nan),
        }
        p = per[name]
        print(f"[{name:9}] absret_ac1={p['absret_ac1']:+.3f} vol_ac1={p['vol_ac1']:+.3f} "
              f"vol_of_vol={p['vol_of_vol']:.3f} vol_spread={p['vol_spread']:.3f} "
              f"dur={p['regime_dur']:.1f}")

    names = sorted(per)
    rps = np.array([per[m]["rps"] for m in names])
    out: dict[str, dict] = {}
    print(f"\n{'=' * 78}\nVOLATILITY DYNAMICS AS A CHANNEL  (n = {len(names)})\n{'=' * 78}")
    print(f"{'statistic':12} {'rho(C,RPS)':>19} {'rho(C,H_raw)':>19} "
          f"{'partial(H,RPS|C)':>19}")
    for stat in ("absret_ac1", "vol_ac1", "vol_of_vol", "vol_spread", "regime_dur"):
        C = np.array([per[m][stat] for m in names], float)
        ok = ~np.isnan(C)
        block = {}
        for hn in ("H_raw", "H_filt"):
            H = np.array([per[m][hn] for m in names])
            r1, p1 = stats.spearmanr(C[ok], rps[ok])
            r2, p2 = stats.spearmanr(C[ok], H[ok])
            base, _ = stats.spearmanr(H[ok], rps[ok])
            pr, pp = partial_spearman(H[ok], rps[ok], C[ok])
            block[hn] = {"n": int(ok.sum()),
                         "rho_C_RPS": r1, "p_C_RPS": p1,
                         "rho_C_H": r2, "p_C_H": p2,
                         "rho_H_RPS_base": base,
                         "partial_rho_H_RPS_given_C": pr, "p_partial": pp,
                         "attenuation": float(base - pr)}
        out[stat] = block
        b = block["H_raw"]
        flag = ""
        if b["p_C_RPS"] < 0.10 and b["p_C_H"] < 0.10:
            flag = "  <-- both links live"
        print(f"{stat:12} {b['rho_C_RPS']:+9.3f} (p={b['p_C_RPS']:.3f}) "
              f"{b['rho_C_H']:+9.3f} (p={b['p_C_H']:.3f}) "
              f"{b['partial_rho_H_RPS_given_C']:+9.3f} "
              f"(att {b['attenuation']:+.3f}){flag}")

    payload = {
        "spec": "Volatility-dynamics mediation test: does retail participation act "
                "on the state-contingency of volatility rather than on trend "
                "persistence? Companion to herding_coherence_mediator.",
        "window": [START, END], "horizon": PRIMARY_HORIZON,
        "n_markets": len(names), "per_market": per, "cross_market": out,
        "elapsed_min": round((time.time() - t0) / 60, 1),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nJSON: {OUT_JSON}  ({payload['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
