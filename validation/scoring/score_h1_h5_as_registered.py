"""Score H1-H5 against the frozen pre-registration, verbatim.

The manuscript has, over successive revisions, restated several hypotheses in
terms that are more defensible than the ones registered on 2026-04-18 -- H1 as
"direction heterogeneity", H3 as an ordering of Transitional band widths. This
script ignores those restatements. It applies the registered predictions and the
registered falsification conditions exactly as written, to the current data, and
reports PASS or REJECT for each.

Registered predictions and falsification conditions
---------------------------------------------------
H1  Frontier: KW-H significant (p < 0.05) AND mean(Det fwd vol) > mean(Sto).
    Developed: relationship weakens -- H < 20 OR mean(Sto) >= mean(Det).
    REJECT if any frontier H < 20, or any frontier direction inverted, or any
    developed market has H > 50 with the frontier direction.

H2  Spearman rho(H, MS_index) > 0.5, where
    MS = 0.4*circuit_breaker + 0.3*(1 - institutional_share) + 0.3*(1 - log cap).
    REJECT if p > 0.10.

H3  Frontier p(Transitional) > 0.55; developed p(Transitional) < 0.50;
    difference > 10 percentage points.
    REJECT if any frontier p_tra < 0.45, or any developed p_tra > 0.60.

H4  Every market: observed filtered flip rate below the 5th percentile of the
    shuffled null (10,000 permutations, p < 0.01).
    REJECT if any market's flip rate falls inside the null 5th-95th band.

H5  p(Transitional) spread across configurations A/B/C < 5 pp per market.
    REJECT if any market's spread exceeds 7 pp.

Anything the current archive cannot supply is reported as UNTESTABLE rather than
silently skipped.
"""
from __future__ import annotations

import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(_VALIDATION, "results_v2")
OUT_JSON = os.path.join(R, "scoring/h1_h5_as_registered.json")

GREEN, RED, GREY = "PASS", "REJECT", "UNTESTABLE"


def load(*parts):
    p = os.path.join(R, *parts)
    if not os.path.exists(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def fmt(v, nd=3):
    return "n/a" if v is None else f"{v:.{nd}f}"


report: dict = {"registered_commit_date": "2026-04-18", "hypotheses": {}}


# ---------------------------------------------------------------- H1
def score_h1():
    ls = load("n27_experiment", "h1_location_vs_scale.json")
    cm = load("cross_market_v2.json")
    hy = load("h3_h4_h5/hysteresis_robustness_v2.json")
    if ls is None:
        return {"verdict": GREY, "reason": "h1_location_vs_scale.json missing"}
    cat = {}
    if hy:
        for blk in hy["markets"]:
            cat[blk["market"]] = blk["category"]
    per = ls["per_market"]
    panel = [m for m in per if m in cat] or list(per)

    rows, breaches = [], []
    for m in sorted(panel):
        f = per[m]["filtered"]
        c = cat.get(m, "?")
        H, p = f["H"], f["p"]
        det_gt_sto = f["mean_det"] > f["mean_sto"]
        row = {"market": m, "category": c, "H_filt": H, "p": p,
               "mean_det": f["mean_det"], "mean_sto": f["mean_sto"],
               "direction": "Det>Sto" if det_gt_sto else "Sto>=Det"}
        if c == "Frontier":
            if H < 20:
                breaches.append(f"{m} (Frontier) H = {H:.1f} < 20")
            if not det_gt_sto:
                breaches.append(f"{m} (Frontier) direction inverted")
            row["registered_expectation"] = "H>=20 and Det>Sto"
            row["meets"] = bool(H >= 20 and det_gt_sto)
        elif c == "Developed":
            if H > 50 and det_gt_sto:
                breaches.append(f"{m} (Developed) H = {H:.1f} > 50 with Det>Sto")
            row["registered_expectation"] = "H<20 or Sto>=Det"
            row["meets"] = bool(H < 20 or not det_gt_sto)
        else:
            row["registered_expectation"] = "not specified"
            row["meets"] = None
        rows.append(row)
    return {"verdict": RED if breaches else GREEN, "breaches": breaches,
            "per_market": rows,
            "note": "Scored on filtered labels, the canonical deployment track; "
                    "means are the marginal Det/Sto forward-vol means the "
                    "registration names, not the covariate-adjusted DML contrast."}


# ---------------------------------------------------------------- H2
def score_h2():
    rc = load("h2_magnitude/h2_registered_composite.json")
    if rc is None:
        return {"verdict": GREY, "reason": "h2_registered_composite.json missing"}
    t = rc["tests"]
    out = {"per_track": {}}
    verdicts = []
    for track in ("raw", "filtered"):
        b = t[track]
        rho, p = b["rho_H_MSindex"], b["p"]
        ok = rho > 0.5 and p <= 0.10
        out["per_track"][track] = {"rho": rho, "p": p,
                                   "gate_rho_gt_0.5": rho > 0.5,
                                   "gate_p_le_0.10": p <= 0.10,
                                   "verdict": GREEN if ok else RED}
        verdicts.append(ok)
    out["verdict"] = GREEN if all(verdicts) else (
        "PASS (one track)" if any(verdicts) else RED)
    out["note"] = ("Scored on the registered composite itself, on the "
                   "registered-scale eight-market panel -- not on the RPS "
                   "single-variable substitution the paper reports as primary.")
    return out


# ---------------------------------------------------------------- H3
def score_h3():
    import pandas as pd
    f = os.path.join(R, "h3_h4_h5/hysteresis_summary_v2.csv")
    if not os.path.exists(f):
        return {"verdict": GREY, "reason": "hysteresis_summary_v2.csv missing"}
    rows, breaches = [], []
    front, dev = [], []
    for _, a in pd.read_csv(f).iterrows():
        m, c, p_tra = a["market"], a["category"], float(a["p_tra"])
        rows.append({"market": m, "category": c, "p_tra": p_tra})
        if c == "Frontier":
            front.append(p_tra)
            if p_tra < 0.45:
                breaches.append(f"{m} (Frontier) p_tra = {p_tra:.3f} < 0.45")
        elif c == "Developed":
            dev.append(p_tra)
            if p_tra > 0.60:
                breaches.append(f"{m} (Developed) p_tra = {p_tra:.3f} > 0.60")
    gap = (sum(front) / len(front) - sum(dev) / len(dev)) if front and dev else None
    pred = {
        "frontier_all_gt_0.55": all(x > 0.55 for x in front) if front else None,
        "developed_all_lt_0.50": all(x < 0.50 for x in dev) if dev else None,
        "mean_gap_pp": None if gap is None else round(gap * 100, 1),
        "gap_gt_10pp": None if gap is None else gap > 0.10,
    }
    return {"verdict": RED if breaches else GREEN, "breaches": breaches,
            "registered_predictions_met": pred, "per_market": rows,
            "note": "Registered H3 is a LEVEL prediction on p(Transitional) with "
                    "fixed thresholds, not the band-width ordering the manuscript "
                    "reports. Falsification turns only on the 0.45 / 0.60 bounds; "
                    "the 0.55 / 0.50 / 10pp clauses are the point predictions."}


# ---------------------------------------------------------------- H4
def score_h4():
    import pandas as pd
    f = os.path.join(R, "h3_h4_h5/h4_block_permutation.csv")
    if not os.path.exists(f):
        return {"verdict": GREY, "reason": "h4_block_permutation.csv missing"}
    rows, breaches = [], []
    for _, r in pd.read_csv(f).iterrows():
        obs = float(r["shuffle_observed"])
        pv = float(r["shuffle_p_block20"])
        null_mean = float(r["shuffle_null_mean_block20"])
        rows.append({"market": r["market"], "category": r["category"],
                     "observed": obs, "null_mean_block20": null_mean,
                     "p_block20": pv, "p_label_shuffle": float(r["shuffle_p_label"])})
        # Registered condition: the observed rate must sit BELOW the null 5th
        # percentile. p = 0 at every block size means no permutation reached it.
        if pv >= 0.01 or obs >= null_mean:
            breaches.append(f"{r['market']} flip rate {obs:.2f} not decisively "
                            f"below the null (p = {pv:.4f}, null mean {null_mean:.2f})")
    return {"verdict": RED if breaches else GREEN, "breaches": breaches,
            "per_market": rows}


# ---------------------------------------------------------------- H5
def score_h5():
    import pandas as pd
    f = os.path.join(R, "h3_h4_h5/h5_refined.csv")
    if not os.path.exists(f):
        return {"verdict": GREY, "reason": "h5_refined.csv missing"}
    rows, breaches, soft = [], [], []
    for _, a in pd.read_csv(f).iterrows():
        spread = float(a["spread"])
        rows.append({"market": a["market"], "category": a["category"],
                     "p_tra_spread_pp": round(spread * 100, 2)})
        if spread > 0.07:
            breaches.append(f"{a['market']} spread {spread*100:.1f}pp > 7pp")
        elif spread >= 0.05:
            soft.append(f"{a['market']} spread {spread*100:.1f}pp "
                        f"(exceeds the 5pp point prediction, within the 7pp bound)")
    return {"verdict": RED if breaches else GREEN, "breaches": breaches,
            "point_prediction_misses": soft, "per_market": rows}


SCORERS = [("H1", "Direction: frontier significant + Det>Sto; developed weakens", score_h1),
           ("H2", "Microstructure ordering: rho(H, MS_index) > 0.5, p <= 0.10", score_h2),
           ("H3", "Transitional Dominance: frontier p_tra > 0.55, developed < 0.50", score_h3),
           ("H4", "Temporal structure: flip rate below the shuffled-null 5th pct", score_h4),
           ("H5", "Parameter robustness: p_tra spread < 5pp across A/B/C", score_h5)]


def main() -> int:
    print("=" * 78)
    print("H1-H5 SCORED AGAINST THE FROZEN PRE-REGISTRATION (2026-04-18)")
    print("=" * 78)
    for key, title, fn in SCORERS:
        res = fn()
        report["hypotheses"][key] = {"statement": title, **res}
        print(f"\n### {key}  {title}")
        print(f"    VERDICT: {res['verdict']}")
        if res.get("reason"):
            print(f"    reason: {res['reason']}")
        for b in res.get("breaches", []):
            print(f"    BREACH: {b}")
        for s in res.get("point_prediction_misses", []):
            print(f"    miss:   {s}")
        if key == "H2" and "per_track" in res:
            for tr, b in res["per_track"].items():
                print(f"    {tr:9} rho = {fmt(b['rho'])}  p = {fmt(b['p'], 4)}  "
                      f"[rho>0.5 {b['gate_rho_gt_0.5']}, p<=0.10 {b['gate_p_le_0.10']}]")
        if key == "H3" and res.get("registered_predictions_met"):
            for k, v in res["registered_predictions_met"].items():
                print(f"    {k}: {v}")
        for row in res.get("per_market", [])[:30]:
            print("      " + ", ".join(f"{k}={fmt(v) if isinstance(v, float) else v}"
                                       for k, v in row.items()))

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nJSON: {OUT_JSON}")
    verdicts = {k: v["verdict"] for k, v in report["hypotheses"].items()}
    print("SUMMARY:", verdicts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
