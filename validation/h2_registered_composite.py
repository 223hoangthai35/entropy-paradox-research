"""Score the REGISTERED H2 composite (MS_index) on the registered-scale panel.

Pre-registration b130b0f (2026-04-18) registered:
    MS_index = 0.4*circuit_breaker + 0.3*(1 - institutional_share) + 0.3*(1 - size)
with circuit_breaker in {0,1} and institutional_share in [0,1]. The size term is
under-specified ("1 - log(market_cap_usd)"); implemented here as 1 minus the
min-max-normalized log10 market cap (documented resolution choice). Retail share
(1 - institutional_share) is the cascade RPS point set. Circuit-breaker dummies
and market caps are author-assembled (per-stock daily price limits; approximate
total market capitalization mid-window, USD) — classification table embedded
below and frozen with the output for transparency.

Reported for transparency alongside the RPS-single-variable supersession
(h2_rps_validation.json): the composite was superseded for construct reasons
(qualitative weights, incompatible units), not because it fails.

Output: validation/results_v2/h2_registered_composite.json
"""
import json
import os
import sys

import numpy as np
from scipy import stats

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RES = os.path.join(os.path.dirname(__file__), "results_v2")

# (circuit_breaker/per-stock daily price limit dummy, approx market cap USD tn, source note)
PANEL = {
    "VNINDEX": (1, 0.25, "HOSE +/-7% daily limit; ~USD 250bn"),
    "BVB":     (1, 0.065, "BVB +/-15% static limit; ~USD 65bn"),
    "KOSPI":   (1, 2.0,  "KRX +/-30% daily limit; ~USD 2.0tn"),
    "NIFTY":   (1, 5.0,  "NSE 10-20% stock bands + index circuit breakers; ~USD 5tn"),
    "SPX":     (0, 50.0, "no per-stock daily hard limit (LULD pauses only); ~USD 50tn"),
    "FTSE":    (0, 2.4,  "no daily price limits; ~USD 2.4tn"),
    "NIKKEI":  (1, 6.5,  "TSE daily price limits by price band; ~USD 6.5tn"),
    "BTC":     (0, 1.5,  "no limits, 24/7; ~USD 1.5tn network value"),
}

RPS = {"VNINDEX": 0.90, "BVB": 0.225, "KOSPI": 0.45, "NIFTY": 0.40,
       "SPX": 0.275, "FTSE": 0.20, "NIKKEI": 0.18, "BTC": 0.55}


def main() -> int:
    h2 = json.load(open(os.path.join(RES, "h2_eta_squared.json"), encoding="utf-8"))["per_market"]
    ms = list(PANEL)
    logcap = np.log10([PANEL[m][1] * 1e12 for m in ms])
    size_norm = (logcap - logcap.min()) / (logcap.max() - logcap.min())
    ms_index = {m: 0.4 * PANEL[m][0] + 0.3 * RPS[m] + 0.3 * (1 - size_norm[i])
                for i, m in enumerate(ms)}
    out = {"spec": ("Registered MS_index (b130b0f) scored on the registered-scale n=8 panel. "
                    "Size term resolved as 1 - minmax(log10 cap). Author-assembled CB/cap table "
                    "embedded; RPS = cascade point set."),
           "classification": {m: {"circuit_breaker": PANEL[m][0], "cap_usd_tn": PANEL[m][1],
                                  "note": PANEL[m][2], "MS_index": round(ms_index[m], 4)}
                              for m in ms},
           "tests": {}}
    for lbl in ("raw", "filtered"):
        H = [h2[m][lbl]["H_stat"] for m in ms]
        x = [ms_index[m] for m in ms]
        r, p = stats.spearmanr(H, x)
        out["tests"][lbl] = {"rho_H_MSindex": float(r), "p": float(p),
                             "registered_gates": {"rho_gt_0.5": bool(r > 0.5),
                                                  "reject_if_p_gt_0.10": bool(p > 0.10)}}
        print(f"{lbl:>8}: rho(H, MS_index) = {r:+.3f} (p = {p:.4f})")
    for m in ms:
        print(f"  {m:<8} MS={ms_index[m]:.3f}  (CB={PANEL[m][0]}, RPS={RPS[m]:.3f}, "
              f"size_norm={size_norm[list(PANEL).index(m)]:.3f})")
    path = os.path.join(RES, "h2_registered_composite.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=float)
    print("JSON:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
