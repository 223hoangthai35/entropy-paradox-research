"""Rotation-calibrated Kruskal-Wallis H for the H2 cross-market tests (referee item A3).

Per market: circularly rotate the label series R times (offset uniform in
[252, n-252] — preserving label marginals, run-length structure, and the
serial dependence of the forward-vol target; destroying only alignment),
recompute KW-H per rotation, and form the calibrated statistic
    z_H = (H_obs - mean(H_null)) / sd(H_null)
plus the placebo percentile. Cross-market tests are then re-run on z_H:
Spearman rho(z_H, RPS) and the JT ordered tier-block test, both panels,
raw and filtered labels.

This applies the App F.6 rotation machinery to the H2 statistic itself:
if per-market H inflation from label persistence x overlapping targets were
driving the cross-market gradient, calibration would flatten it.

Output: validation/results_v2/h2_calibrated_kwh.json
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from validation._features import run_full_pipeline  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

START = "2018-01-01"
END = "2026-06-30"
ANALYSIS_START = "2020-01-01"
N_ROT = 200
SEED = 42
FWD_H = 20

RES = os.path.join(os.path.dirname(__file__), "results_v2")
RPS_VALUES = json.load(open(os.path.join(
    RES, "n27_experiment", "h2_cascade_n27_full_classification.json"),
    encoding="utf-8"))["all_p1_reference"]["rps_values"]
TIER_RANK = {c["name"]: c["tier_rank"] for c in MARKETS_N27}
N8 = ["VNINDEX", "BVB", "KOSPI", "NIFTY", "SPX", "FTSE", "NIKKEI", "BTC"]


def fwd_vol(close: pd.Series) -> pd.Series:
    r = np.log(close).diff()
    fv = r.rolling(FWD_H).std().shift(-FWD_H) * np.sqrt(252) * 100
    return fv


def kw_h(labels: np.ndarray, y: np.ndarray) -> float:
    groups = [y[labels == k] for k in (0, 1, 2)]
    groups = [g for g in groups if len(g) >= 5]
    if len(groups) < 2:
        return np.nan
    return float(stats.kruskal(*groups).statistic)


def jt_stat(samples):
    t = 0.0
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            for x in samples[i]:
                t += float((samples[j] > x).sum()) + 0.5 * float((samples[j] == x).sum())
    return t


def jt_perm_p(samples, n_perm=20_000, seed=SEED):
    rng = np.random.default_rng(seed)
    obs = jt_stat(samples)
    pool = np.concatenate(samples)
    sizes = [len(s) for s in samples]
    count = 0
    for _ in range(n_perm):
        rng.shuffle(pool)
        parts, k = [], 0
        for s in sizes:
            parts.append(pool[k:k + s]); k += s
        if jt_stat(parts) >= obs:
            count += 1
    return obs, (count + 1) / (n_perm + 1)


def main() -> int:
    t0 = time.time()
    per_market = {}
    for cfg in MARKETS_N27:
        name = cfg["name"]
        try:
            out = run_full_pipeline(market=name, ticker=cfg["ticker"],
                                    source=cfg["source"], start=START, end=END)
        except Exception as e:
            print(f"[{name}] SKIP pipeline: {type(e).__name__}: {e}")
            continue
        fv = fwd_vol(out["ohlcv"]["Close"])
        entry = {}
        for lbl_key, series in (("raw", out["raw_labels"]), ("filtered", out["filtered_labels"])):
            df = pd.DataFrame({"lab": series, "fv": fv}).loc[ANALYSIS_START:].dropna()
            labs, y = df["lab"].to_numpy(), df["fv"].to_numpy()
            h_obs = kw_h(labs, y)
            rng = np.random.default_rng(SEED + hash(name) % 1000)
            nulls = []
            n = len(labs)
            for _ in range(N_ROT):
                off = int(rng.integers(252, n - 252))
                nulls.append(kw_h(np.roll(labs, off), y))
            nulls = np.array([x for x in nulls if np.isfinite(x)])
            z = (h_obs - nulls.mean()) / nulls.std(ddof=1)
            pct = float((nulls < h_obs).mean())
            entry[lbl_key] = {"H_obs": h_obs, "null_mean": float(nulls.mean()),
                              "null_sd": float(nulls.std(ddof=1)), "z_H": float(z),
                              "placebo_pctile": pct, "n_obs": int(n),
                              "n_rot_ok": int(len(nulls))}
        per_market[name] = entry
        print(f"[{name}] raw H={entry['raw']['H_obs']:7.2f} null={entry['raw']['null_mean']:6.2f} "
              f"z={entry['raw']['z_H']:+6.2f} | filt H={entry['filtered']['H_obs']:7.2f} "
              f"null={entry['filtered']['null_mean']:6.2f} z={entry['filtered']['z_H']:+6.2f}")

    cross = {}
    for panel_name, ms in (("n8", [m for m in N8 if m in per_market]),
                           ("n27", list(per_market))):
        for lbl in ("raw", "filtered"):
            zs = [per_market[m][lbl]["z_H"] for m in ms]
            rps = [RPS_VALUES[m] for m in ms]
            tr = [TIER_RANK[m] for m in ms]
            r1, p1 = stats.spearmanr(zs, rps)
            r2, p2 = stats.spearmanr(zs, tr)
            groups = {}
            for m in ms:
                groups.setdefault(TIER_RANK[m], []).append(per_market[m][lbl]["z_H"])
            samples = [np.array(groups[k]) for k in sorted(groups)]
            jt_obs, jt_p = jt_perm_p(samples)
            cross[f"{panel_name}_{lbl}"] = {
                "n": len(ms), "rho_zH_rps": float(r1), "p_rps": float(p1),
                "rho_zH_tier": float(r2), "p_tier": float(p2),
                "JT": jt_obs, "JT_perm_p": jt_p}
            print(f"{panel_name} {lbl}: rho(z_H,RPS)={r1:+.3f} (p={p1:.4f}) | "
                  f"rho(z_H,tier)={r2:+.3f} (p={p2:.4f}) | JT p={jt_p:.4f}")

    out_doc = {"spec": ("Rotation-calibrated KW-H (A3): per-market circular-rotation null "
                        f"(R={N_ROT}, offsets in [252, n-252]) -> z_H; cross-market Spearman/JT on z_H. "
                        "Applies the F.6 rotation machinery to the H2 statistic."),
               "window": [ANALYSIS_START, END], "n_rot": N_ROT, "seed": SEED,
               "per_market": per_market, "cross_market": cross,
               "elapsed_min": round((time.time() - t0) / 60, 1)}
    path = os.path.join(RES, "h2_calibrated_kwh.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, indent=2, default=float)
    print("JSON:", path, f"({out_doc['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
