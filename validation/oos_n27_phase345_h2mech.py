"""
oos-n27-rigor PHASES 3–5 — H2 new estimators, mechanism, stability, H3/H4.
Full n=27 panel, both windows, all inputs from the frozen snapshot.

PHASE 3 (H2): per-market KW-H/η² + block-bootstrap SE; JT tier-ordered test
  (permutation 20k); EIV-WLS meta-regression on log10(η²+ε) with the n27
  cascade RPS prior (ε-sensitivity {1e-5,1e-4,1e-3}); legacy Spearman +
  cascade-style MC as the comparison column.
PHASE 4 (mechanism): clr(p_det,p_tra,p_sto) + EIV for p_sto/p_tra vs RPS;
  legacy Spearman; raw-SampEn battery (mean/std/median/iqr/p95/p05 × RPS).
PHASE 5: ARI label stability repro↔extended; H3 tier-mean p_tra ordering;
  H4 label-shuffle (10k) + block-permutation {5,10,20} (2000).

Output: results_v2/oos_n27/phase345_results.json
Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/oos_n27_phase345_h2mech.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import flip_rate_per_year, SAMPEN_WIN, SPE_Z_WIN
from validation.h2_eta_squared import compute_kw_h_and_eta
from validation.markets_n27 import CASCADE_N27
from validation.link_b_raw_sampen_test import cascade_point
from validation.oos_2026q2_h2_alt_estimators import (
    aligned_arrays, bootstrap_eta, wls_slope, weighted_kendall, jonckheere,
)
from validation.rigor_composition_clr_eiv import clr
from validation.cross_market_v2 import _circular_block_indices
from skills.quant_skill import calc_rolling_price_sample_entropy

from validation.oos_n27_common import (
    REPRO_END, OOS_END, OOS_DIR, pipeline_from_snapshot, market_seed,
)

N_BOOT = 2000
N_MC = 10_000
N_PERM = 10_000
EPS_LIST = [1e-5, 1e-4, 1e-3]
EPS_MAIN = 1e-4
BLOCK = 20
SHARE_FLOOR = 1e-3
RNG_SEED = 42
WINDOWS = {"repro": REPRO_END, "extended": OOS_END}


def sample_rps(spec: dict, rng: np.random.Generator) -> float:
    t = spec["type"]
    if t == "point":
        return float(spec["value"])
    if t == "uniform":
        return float(rng.uniform(spec["low"], spec["high"]))
    if t == "beta":
        a = spec["kappa"] * spec["mean"]
        b = spec["kappa"] * (1 - spec["mean"])
        return float(rng.beta(a, b))
    raise ValueError(t)


def perm_spearman(x: np.ndarray, y: np.ndarray, seed: int = RNG_SEED) -> tuple[float, float]:
    rho, _ = spearmanr(x, y)
    rng = np.random.default_rng(seed)
    null = np.empty(N_PERM)
    for i in range(N_PERM):
        null[i], _ = spearmanr(x, rng.permutation(y))
    return float(rho), float(np.mean(np.abs(null) >= abs(rho)))


def eiv_mc(y_boot: dict[str, np.ndarray], rps_spec: dict[str, dict],
           transform, seed: int = RNG_SEED) -> dict:
    names = list(y_boot.keys())
    yb = {m: transform(y_boot[m]) for m in names}
    var = np.array([np.var(yb[m]) for m in names])
    w = 1.0 / np.maximum(var, 1e-6)
    w = w / w.sum()
    rng = np.random.default_rng(seed)
    betas = np.empty(N_MC)
    taus = np.empty(N_MC)
    for i in range(N_MC):
        x = np.array([sample_rps(rps_spec[m], rng) for m in names])
        y = np.array([yb[m][rng.integers(len(yb[m]))] for m in names])
        betas[i] = wls_slope(x, y, w)
        taus[i] = weighted_kendall(x, y, w)
    def s(a):
        return {"mean": float(a.mean()), "p025": float(np.percentile(a, 2.5)),
                "p975": float(np.percentile(a, 97.5)),
                "P_gt_0": float(np.mean(a > 0)), "P_lt_0": float(np.mean(a < 0))}
    return {"beta": s(betas), "tau_w": s(taus)}


def shares_boot(labels: pd.Series, seed: int) -> tuple[np.ndarray, np.ndarray]:
    arr = labels.astype(int).to_numpy()
    point = np.array([(arr == k).mean() for k in (0, 1, 2)])
    idx = _circular_block_indices(len(arr), BLOCK, N_BOOT,
                                  np.random.default_rng(seed))
    boot = np.stack([(arr[idx] == k).mean(axis=1) for k in (0, 1, 2)], axis=1)
    return point, np.apply_along_axis(clr, 1, boot)


def raw_sampen_stats(ohlcv: pd.DataFrame) -> dict:
    s = calc_rolling_price_sample_entropy(ohlcv["Close"].values, window=SAMPEN_WIN)
    s = s[~np.isnan(s)][SPE_Z_WIN:]
    return {"mean": float(np.mean(s)), "std": float(np.std(s)),
            "median": float(np.median(s)),
            "iqr": float(np.percentile(s, 75) - np.percentile(s, 25)),
            "p95": float(np.percentile(s, 95)), "p05": float(np.percentile(s, 5))}


def main() -> int:
    with open(os.path.join(OOS_DIR, "phase0_manifest.json"), encoding="utf-8") as f:
        recs = [r for r in json.load(f)["records"] if r.get("gate_ok")]
    names = [r["market"] for r in recs]
    source_of = {r["market"]: r["source"] for r in recs}
    tier_of = {r["market"]: r["tier_rank"] for r in recs}
    rps_spec = {m: CASCADE_N27[m] for m in names}
    rps_point = {m: cascade_point(CASCADE_N27[m]) for m in names}

    print("=" * 74)
    print(f"  oos-n27-rigor PHASES 3–5 ({len(names)} markets × 2 windows)")
    print("=" * 74)
    t0 = time.time()
    res: dict = {"spec": "phases 3-5: H2 JT+EIV, mechanism clr+EIV+SampEn, "
                         "ARI, H3 tier-mean, H4 shuffle",
                 "rps_spec_source": "markets_n27.CASCADE_N27 (code source of truth)",
                 "windows": {}, "label_stability": {}}

    piped: dict[tuple, dict] = {}
    for win, end in WINDOWS.items():
        print(f"\n--- window [{win}] → {end} ---")
        eta_boot: dict[str, dict[str, np.ndarray]] = {"raw": {}, "filt": {}}
        per_m: dict[str, dict] = {}
        for m in names:
            out = pipeline_from_snapshot(m, end, source_of[m])
            piped[(m, win)] = out
            entry: dict = {"tier_rank": tier_of[m], "rps_point": rps_point[m]}
            for lab_key, series in [("raw", out["raw_labels"]),
                                    ("filt", out["filtered_labels"])]:
                lab, fwd = aligned_arrays(out["ohlcv"], series)
                entry[f"kw_{lab_key}"] = compute_kw_h_and_eta(out["ohlcv"], series)
                eta_boot[lab_key][m] = bootstrap_eta(lab, fwd, seed=market_seed(m))
            p_pt, clr_b = shares_boot(out["filtered_labels"], market_seed(m))
            entry["shares_filtered"] = p_pt.tolist()
            entry["clr_boot_sto"] = clr_b[:, 2]
            entry["clr_boot_tra"] = clr_b[:, 1]
            entry["sampen"] = raw_sampen_stats(out["ohlcv"])
            entry["flip_rate_filtered"] = flip_rate_per_year(out["filtered_labels"])
            per_m[m] = entry
        print(f"  per-market stats done ({(time.time()-t0)/60:.1f}m)")

        tiers = np.array([tier_of[m] for m in names], dtype=float)
        rps_arr = np.array([rps_point[m] for m in names])
        block: dict = {"per_market": {
            m: {k: v for k, v in per_m[m].items()
                if not isinstance(v, np.ndarray)} for m in names}}

        # ---- PHASE 3: H2 ----
        for lab_key in ["raw", "filt"]:
            H = np.array([per_m[m][f"kw_{lab_key}"]["H_stat"] for m in names])
            eta = np.array([per_m[m][f"kw_{lab_key}"]["eta_sq"] for m in names])
            rho_t, p_t = spearmanr(H, tiers)
            rho_r, p_r = perm_spearman(H, rps_arr)
            jt = jonckheere(eta, tiers)
            eiv_by_eps = {}
            for eps in EPS_LIST:
                eiv_by_eps[str(eps)] = eiv_mc(
                    eta_boot[lab_key], rps_spec,
                    transform=lambda a, e=eps: np.log10(a + e))
            block[f"h2_{lab_key}"] = {
                "rho_H_tier": float(rho_t), "p_H_tier": float(p_t),
                "rho_H_rps": rho_r, "p_H_rps_perm": p_r,
                "jt_tier_eta": jt,
                "eiv": eiv_by_eps[str(EPS_MAIN)],
                "eiv_eps_sensitivity": {e: eiv_by_eps[e]["beta"]["P_gt_0"]
                                        for e in eiv_by_eps},
            }
            e_main = block[f"h2_{lab_key}"]["eiv"]
            print(f"  [H2 {lab_key}] ρ(H,tier)={rho_t:+.3f} (p={p_t:.4f})  "
                  f"JT p={jt['p_one_sided']:.4f}  "
                  f"EIV P(β>0)={e_main['beta']['P_gt_0']*100:.1f}% "
                  f"[{e_main['beta']['p025']:+.2f},{e_main['beta']['p975']:+.2f}]")

        # ---- PHASE 4: mechanism ----
        for comp, key, want in [("clr_sto", "clr_boot_sto", "P_lt_0"),
                                ("clr_tra", "clr_boot_tra", "P_gt_0")]:
            yb = {m: per_m[m][key] for m in names}
            mc = eiv_mc(yb, rps_spec, transform=lambda a: a)
            x_pt = np.array([np.median(per_m[m][key]) for m in names])
            rho_l, p_l = perm_spearman(x_pt, rps_arr)
            block[f"mech_{comp}"] = {"eiv_beta": mc["beta"],
                                     "P_correct_sign": mc["beta"][want],
                                     "legacy_spearman": {"rho": rho_l, "p_perm": p_l}}
            print(f"  [mech {comp}] EIV β={mc['beta']['mean']:+.3f} "
                  f"[{mc['beta']['p025']:+.3f},{mc['beta']['p975']:+.3f}] "
                  f"P(sign)={mc['beta'][want]*100:.1f}%  "
                  f"legacy ρ={rho_l:+.3f} p={p_l:.4f}")
        p_sto_pt = np.array([per_m[m]["shares_filtered"][2] for m in names])
        rho_s, p_s = perm_spearman(p_sto_pt, rps_arr)
        block["mech_p_sto_legacy"] = {"rho": rho_s, "p_perm": p_s}
        for feat in ["mean", "std", "median", "iqr", "p95", "p05"]:
            x = np.array([per_m[m]["sampen"][feat] for m in names])
            rho_f, p_f = perm_spearman(x, rps_arr)
            block[f"sampen_{feat}"] = {"rho": rho_f, "p_perm": p_f}
        print(f"  [mech legacy] ρ(p_sto,RPS)={rho_s:+.3f} p={p_s:.4f}  "
              f"SampEn p95 ρ={block['sampen_p95']['rho']:+.3f} "
              f"p={block['sampen_p95']['p_perm']:.4f}")

        # ---- PHASE 5a: H3 tier-mean ordering ----
        p_tra_pt = np.array([per_m[m]["shares_filtered"][1] for m in names])
        tm = {}
        for t in sorted(set(tier_of.values())):
            mask = tiers == t
            tm[int(t)] = float(p_tra_pt[mask].mean())
        msci = [tm.get(4), tm.get(3), tm.get(1)]   # Frontier, Emerging, Developed
        block["h3_tier_mean_p_tra"] = {
            "by_tier_rank": tm,
            "msci_monotone_frontier_lt_emerging_lt_developed":
                bool(msci[0] < msci[1] < msci[2]) if all(v is not None for v in msci) else None,
        }
        print(f"  [H3] tier-mean p_tra: {tm}  monotone(F<E<D)="
              f"{block['h3_tier_mean_p_tra']['msci_monotone_frontier_lt_emerging_lt_developed']}")

        res["windows"][win] = block

    # ---- PHASE 5b: ARI stability ----
    print("\n--- label stability (repro ↔ extended) ---")
    for m in names:
        a, b = piped[(m, "repro")], piped[(m, "extended")]
        d = {}
        for key, lab in [("raw", "raw_labels"), ("filt", "filtered_labels")]:
            common = a[lab].index.intersection(b[lab].index)
            v1 = a[lab].loc[common].astype(int).to_numpy()
            v2 = b[lab].loc[common].astype(int).to_numpy()
            d[f"agree_{key}"] = float((v1 == v2).mean())
            d[f"ari_{key}"] = float(adjusted_rand_score(v1, v2))
        res["label_stability"][m] = d
        if d["ari_filt"] < 0.5:
            print(f"  ! UNSTABLE {m:<9} ARI raw/filt = {d['ari_raw']:+.2f}/{d['ari_filt']:+.2f}")
    stable = sum(1 for d in res["label_stability"].values() if d["ari_filt"] >= 0.8)
    print(f"  ARI_filt ≥0.8: {stable}/{len(names)}")

    # ---- PHASE 5c: H4 (both windows) ----
    from validation.hysteresis_cross_market_v2 import _block_shuffle_p
    from validation.shuffle_test import run_shuffle_test
    print("\n--- H4 shuffle (label 10k + block {5,10,20}) ---")
    h4: dict = {}
    for win in WINDOWS:
        worst_label_p, worst_block_p = 0.0, 0.0
        per = {}
        for m in names:
            filt = piped[(m, win)]["filtered_labels"]
            common = filt[filt.index >= "2020-01-01"]
            shuf = run_shuffle_test(common, market=m)
            arr = common.astype(int).to_numpy()
            bp = {b: _block_shuffle_p(arr, b, 2000, RNG_SEED + b)["p_value"]
                  for b in (5, 10, 20)}
            per[m] = {"p_label": float(shuf.p_value), "p_block": bp}
            worst_label_p = max(worst_label_p, shuf.p_value)
            worst_block_p = max(worst_block_p, max(bp.values()))
        h4[win] = {"per_market": per, "worst_p_label": worst_label_p,
                   "worst_p_block": worst_block_p}
        print(f"  [{win}] worst p_label={worst_label_p:.4f}  "
              f"worst p_block={worst_block_p:.4f}")
    res["h4"] = h4

    res["elapsed_seconds"] = float(time.time() - t0)
    out_path = os.path.join(OOS_DIR, "phase345_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, default=float)
    print(f"\n  JSON: {out_path}   total {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
