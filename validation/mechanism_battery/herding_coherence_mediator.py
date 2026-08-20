"""Is trend coherence the channel through which retail participation raises
regime informativeness?

The paper's behavioural reading is that correlated retail order flow produces
episodes of coherent, same-direction price movement, that such episodes compress
ordinal-pattern complexity, and that a market alternating sharply between
coherent and incoherent states is one whose three-state entropy partition
separates forward volatility well. Until now that chain has been argued rather
than measured: RPS is a single cross-sectional scalar and no order-flow
correlation is observed anywhere in the design.

Coherence itself, however, is measurable from the index series already in hand.
This script computes four model-free coherence statistics per market and asks
the three questions a mediation claim has to answer:

  (1) does coherence rise with retail participation?          rho(C, RPS)
  (2) does coherence rise with regime informativeness?         rho(C, H)
  (3) does controlling for coherence attenuate the headline?   partial rho(H, RPS | C)

Attenuation in (3), together with (1) and (2), is what would license calling
coherence the channel. No attenuation would say the RPS-H association runs
through something other than trend coherence -- which is equally informative and
must be reported either way.

Coherence statistics (all on daily log returns, all model-free):
  VR(q)      Lo-MacKinlay variance ratio at q = 5, 10, 20. VR > 1 means returns
             are positively autocorrelated at that horizon: trends persist.
  AR(1)      first-order return autocorrelation.
  run_len    mean length of same-sign return runs, in days.
  run_share  fraction of observations inside a same-sign run of 3 days or more.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
from scipy import stats

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(_VALIDATION))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from validation._features import load_ohlcv  # noqa: E402
from validation.h1_direction.h1_dml import START, END  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

R = os.path.join(_VALIDATION, "results_v2")
OUT_JSON = os.path.join(R, "n27_experiment", "herding_coherence_mediator.json")

eta = json.load(io.open(os.path.join(R, "n27_experiment",
                                     "h2_eta_squared_n27.json"), encoding="utf-8"))
RPS = eta["rps_point_estimates"]
PER = eta["per_market"]
CAT = {c["name"]: c["category"] for c in MARKETS_N27}


def variance_ratio(r: np.ndarray, q: int) -> float:
    """Lo-MacKinlay VR(q): var of q-day sums over q * var of 1-day, overlapping."""
    r = r - r.mean()
    n = len(r)
    if n <= q + 1:
        return np.nan
    v1 = np.sum(r ** 2) / (n - 1)
    agg = np.convolve(r, np.ones(q), mode="valid")
    m = q * (n - q + 1) * (1 - q / n)
    vq = np.sum(agg ** 2) / m if m > 0 else np.nan
    return float(vq / (q * v1)) if v1 else np.nan


def run_stats(r: np.ndarray) -> tuple[float, float]:
    """Mean same-sign run length, and share of observations in runs >= 3."""
    s = np.sign(r)
    s = s[s != 0]
    if len(s) < 2:
        return np.nan, np.nan
    brk = np.flatnonzero(np.diff(s) != 0) + 1
    lens = np.diff(np.concatenate([[0], brk, [len(s)]]))
    return float(lens.mean()), float(lens[lens >= 3].sum() / len(s))


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
        r = np.log(c / c.shift(1)).dropna().values
        rl, rs = run_stats(r)
        per[name] = {
            "category": CAT.get(name), "rps": RPS[name], "n_obs": int(len(r)),
            "H_raw": PER[name]["raw"]["H_stat"],
            "H_filt": PER[name]["filtered"]["H_stat"],
            "VR5": variance_ratio(r, 5), "VR10": variance_ratio(r, 10),
            "VR20": variance_ratio(r, 20), "AR1": float(np.corrcoef(r[:-1], r[1:])[0, 1]),
            "run_len": rl, "run_share": rs,
        }
        print(f"[{name:9}] VR5={per[name]['VR5']:.3f} VR20={per[name]['VR20']:.3f} "
              f"AR1={per[name]['AR1']:+.3f} run_len={rl:.2f} run_share={rs:.3f}")

    names = sorted(per)
    rps = np.array([per[m]["rps"] for m in names])
    out: dict[str, dict] = {}
    print(f"\n{'=' * 74}\nCOHERENCE AS A CHANNEL  (n = {len(names)})\n{'=' * 74}")
    print(f"{'statistic':10} {'rho(C,RPS)':>18} {'rho(C,H_raw)':>18} "
          f"{'partial rho(H,RPS|C)':>22}")
    for stat in ("VR5", "VR10", "VR20", "AR1", "run_len", "run_share"):
        C = np.array([per[m][stat] for m in names])
        ok = ~np.isnan(C)
        block = {}
        for hn in ("H_raw", "H_filt"):
            H = np.array([per[m][hn] for m in names])
            r1, p1 = stats.spearmanr(C[ok], rps[ok])
            r2, p2 = stats.spearmanr(C[ok], H[ok])
            base_r, base_p = stats.spearmanr(H[ok], rps[ok])
            pr, pp = partial_spearman(H[ok], rps[ok], C[ok])
            block[hn] = {
                "rho_C_RPS": r1, "p_C_RPS": p1,
                "rho_C_H": r2, "p_C_H": p2,
                "rho_H_RPS": base_r, "partial_rho_H_RPS_given_C": pr,
                "p_partial": pp,
                "attenuation": float(base_r - pr),
            }
        out[stat] = block
        b = block["H_raw"]
        print(f"{stat:10} {b['rho_C_RPS']:+9.3f} (p={b['p_C_RPS']:.3f}) "
              f"{b['rho_C_H']:+9.3f} (p={b['p_C_H']:.3f}) "
              f"{b['partial_rho_H_RPS_given_C']:+11.3f} "
              f"(base {b['rho_H_RPS']:.3f}, attenuation {b['attenuation']:+.3f})")

    print("\nReading: a mediation claim needs rho(C,RPS) > 0, rho(C,H) > 0, AND a")
    print("meaningful drop from the base rho to the partial. A partial that does not")
    print("move says the RPS-H association does not run through trend coherence.")

    payload = {
        "spec": "Trend-coherence mediation test for the behavioural reading of the "
                "RPS-informativeness association. Model-free coherence statistics on "
                "daily log returns; Spearman partials.",
        "window": [START, END], "n_markets": len(names),
        "per_market": per, "cross_market": out,
        "elapsed_min": round((time.time() - t0) / 60, 1),
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nJSON: {OUT_JSON}  ({payload['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
