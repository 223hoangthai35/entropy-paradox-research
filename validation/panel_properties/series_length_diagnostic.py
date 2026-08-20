"""How much of the informativeness spread is a property of the sample, not the market?

The analysis window is identical for all twenty-seven markets, but the usable
series is not: vendor history differs, and crypto trades seven days a week, so
labeled observation counts run from under a thousand to over two thousand. Regime
informativeness is inversely related to that count. This script establishes what
the relationship is and is not, so the manuscript's data section can state it
from a frozen artifact rather than from an assertion.

Series length is a data-availability property, not a market characteristic, so it
does not compete with retail participation as an account of the ordering. What it
can do is contaminate the measurement, and there are three ways it might:

  1. **The mechanical sample-size effect.** Kruskal-Wallis H grows with n at a
     fixed underlying effect, so a longer series should read *higher*, not lower.
     Dividing n out explicitly through the epsilon-squared effect size settles
     this: if the association is mechanical, it disappears under that transform.

  2. **The rotation null.** App F.7 standardizes each market's H against circular
     rotations drawn from offsets in [252, n - 252]. A short series admits fewer
     and more similar rotations, which could under-disperse the null and inflate
     the standardized score. If so, the null's own width tracks series length.

  3. **Full-sample fitting.** A mixture estimated over a longer stretch of history
     describes a more heterogeneous period, so its labels are a worse description
     of any part of it. This is not removable within this design; it is the
     in-sample limitation the paper already states, in measurable form.

The last quantity reported is the one that matters for the paper's claim: the
cross-market ordering with series length held fixed.
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np
from scipy import stats

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(_VALIDATION))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

R = os.path.join(_VALIDATION, "results_v2")
OUT = os.path.join(R, "panel_properties/series_length_diagnostic.json")
CRYPTO = {"BTC", "ETH", "BNB"}


def sp(a, b):
    r, p = stats.spearmanr(a, b)
    return {"rho": float(r), "p": float(p)}


def partial(a, b, ctl):
    """Spearman partial correlation: rank, residualize both on the control's rank."""
    ra, rb, rc = (stats.rankdata(x) for x in (a, b, ctl))
    res = lambda y: y - np.polyval(np.polyfit(rc, y, 1), rc)  # noqa: E731
    return sp(res(ra), res(rb))


def main() -> int:
    cal = json.load(io.open(os.path.join(R, "h2_magnitude/h2_calibrated_kwh.json"),
                            encoding="utf-8"))["per_market"]
    eta = json.load(io.open(os.path.join(R, "n27_experiment",
                                         "h2_eta_squared_n27.json"), encoding="utf-8"))
    RPS, PER = eta["rps_point_estimates"], eta["per_market"]
    ms = [m for m in cal if m in RPS]

    out = {
        "spec": "Series-length diagnostic: is the inverse relation between usable "
                "observation count and regime informativeness a sample-size "
                "artifact, a rotation-null artifact, or a property of full-sample "
                "fitting -- and does the cross-market ordering survive it?",
        "n_markets": len(ms), "tracks": {},
    }

    for tr in ("raw", "filtered"):
        H = np.array([PER[m][tr]["H_stat"] for m in ms])
        N = np.array([cal[m][tr]["n_obs"] for m in ms], float)
        v = np.array([RPS[m] for m in ms])
        sd = np.array([cal[m][tr]["null_sd"] for m in ms])
        z = np.array([cal[m][tr]["z_H"] for m in ms])
        eps = (H - 2) / (N - 3)          # Kruskal-Wallis epsilon-squared, k = 3
        eq = [i for i, m in enumerate(ms) if m not in CRYPTO]

        out["tracks"][tr] = {
            "H_vs_n_obs": sp(H, N),
            "H_vs_n_obs_ex_crypto": sp(H[eq], N[eq]),
            # (1) mechanical: dividing n out should remove it if that is the cause
            "epsilon_sq_vs_n_obs": sp(eps, N),
            "epsilon_sq_vs_RPS": sp(eps, v),
            # (2) rotation null: its width should track n if that is the cause
            "rotation_null_sd_vs_n_obs": sp(sd, N),
            "z_H_vs_n_obs": sp(z, N),
            # (3) what the paper claims, with length held fixed
            "H_vs_RPS": sp(H, v),
            "H_vs_RPS_given_n_obs": partial(H, v, N),
            "H_vs_n_obs_given_RPS": partial(H, N, v),
            "RPS_vs_n_obs": sp(v, N),
            "n_obs_min": int(N.min()), "n_obs_max": int(N.max()),
        }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    for tr, d in out["tracks"].items():
        g = lambda k: f"{d[k]['rho']:+.3f} (p={d[k]['p']:.3f})"  # noqa: E731
        print(f"--- {tr} ---  n_obs {d['n_obs_min']}-{d['n_obs_max']}")
        print(f"  H vs n_obs                  {g('H_vs_n_obs')}"
              f"   ex-crypto {g('H_vs_n_obs_ex_crypto')}")
        print(f"  (1) eps^2 vs n_obs          {g('epsilon_sq_vs_n_obs')}"
              f"   <- dividing n out; strengthens => not mechanical")
        print(f"  (2) rotation null sd vs n   {g('rotation_null_sd_vs_n_obs')}"
              f"   <- flat => not a null-width artifact")
        print(f"  H vs RPS                    {g('H_vs_RPS')}")
        print(f"      | n_obs held fixed      {g('H_vs_RPS_given_n_obs')}")
        print(f"  n_obs vs H | RPS held fixed {g('H_vs_n_obs_given_RPS')}")
        print(f"  RPS vs n_obs                {g('RPS_vs_n_obs')}")
    print(f"\nJSON: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
