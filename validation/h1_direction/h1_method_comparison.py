"""
H1 method comparison — DML vs Cliff's delta + Newey-West HAC side-by-side.

Reads:
  validation/results_v2/{MARKET}_v2_results.json   (Cliff's delta + NW from cross_market_v2.py)
  validation/results_v2/h1_dml.json                (LinearDML + CausalForestDML from h1_dml.py)

Per market, reports:
  - Cliff's delta with circular-block bootstrap 95% CI
  - Newey-West HAC beta (Det vs Sto) with t-stat, two-sided p
  - LinearDML ATE with 95% CI
  - CausalForestDML ATE with 95% CI
  - Direction-label agreement across the 4 methods
  - CI overlap diagnostic

Decision diagnostics:
  - Markets where Cliff's CI fails to exclude zero but DML CI clears:
    NEW INSIGHT (controls absorbed nuisance variance)
  - Markets where Cliff's CI clears zero but DML CI fails:
    NEW INSIGHT (effect was confounded with lagged variables)
  - Markets where all four methods agree on direction:
    CONFIRMATORY (DML adds methodological label, no new finding)

Output: validation/results_v2/h1_method_comparison.json + console summary
"""
from __future__ import annotations

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(_VALIDATION, "results_v2")
DML_PATH = os.path.join(OUTPUT_DIR, "h1_dml.json")

MARKETS = ["VNINDEX", "BVB", "KOSPI", "NIFTY", "SPX", "FTSE", "NIKKEI", "BTC"]


def _ci_clears_zero(lo: float, hi: float) -> str:
    """Return Paradox / Inverted / n.s. based on whether 95% CI excludes zero."""
    try:
        if lo > 0:
            return "Paradox"
        if hi < 0:
            return "Inverted"
        return "n.s."
    except (TypeError, ValueError):
        return "SKIP"


def _classify_insight(cliff_verdict: str, dml_verdict: str) -> str:
    """Classify whether DML adds new insight relative to Cliff's delta."""
    if cliff_verdict == dml_verdict:
        return "AGREE"
    if cliff_verdict == "n.s." and dml_verdict in ("Paradox", "Inverted"):
        return "DML_TIGHTER (controls absorbed nuisance)"
    if cliff_verdict in ("Paradox", "Inverted") and dml_verdict == "n.s.":
        return "DML_LOOSER (effect confounded with lags)"
    if cliff_verdict in ("Paradox", "Inverted") and dml_verdict in ("Paradox", "Inverted") and cliff_verdict != dml_verdict:
        return "DIRECTION_FLIP"
    return "OTHER"


def main() -> int:
    print("=" * 70)
    print("  H1 METHOD COMPARISON: Cliff's delta + Newey-West vs DML")
    print("=" * 70)

    # Load DML results
    if not os.path.exists(DML_PATH):
        print(f"  ERROR: DML output not found: {DML_PATH}")
        print(f"  Run h1_dml.py first")
        return 1
    with open(DML_PATH, "r", encoding="utf-8") as f:
        dml_payload = json.load(f)
    dml_results = dml_payload["results"]

    # Per-market comparison
    rows = []
    for m in MARKETS:
        v2_path = os.path.join(OUTPUT_DIR, f"{m}_v2_results.json")
        if not os.path.exists(v2_path):
            print(f"  [SKIP] {m}: v2 results missing")
            continue
        with open(v2_path, "r", encoding="utf-8") as f:
            v2 = json.load(f)
        if m not in dml_results:
            print(f"  [SKIP] {m}: DML result missing")
            continue
        dml = dml_results[m]

        # Extract Cliff's delta + Newey-West from v2
        cliff_delta = v2.get("primary_cliffs_delta", float("nan"))
        cliff_lo = v2.get("primary_delta_ci_lo", float("nan"))
        cliff_hi = v2.get("primary_delta_ci_hi", float("nan"))
        cliff_verdict_paper = v2.get("direction_verdict_formal", "SKIP")
        cliff_verdict_recompute = _ci_clears_zero(cliff_lo, cliff_hi)
        nw_beta = v2.get("primary_nw_beta", float("nan"))
        nw_t = v2.get("primary_nw_tstat", float("nan"))
        nw_p = v2.get("primary_nw_p_two", float("nan"))

        # Extract DML
        lin = dml["linear_dml"]
        cf = dml["causal_forest_dml"]

        # Insight classification (use Cliff's bootstrap CI as baseline)
        lin_insight = _classify_insight(cliff_verdict_paper, lin.get("direction_verdict", "SKIP"))
        cf_insight = _classify_insight(cliff_verdict_paper, cf.get("direction_verdict", "SKIP"))

        rows.append({
            "market": m,
            "n_dml_obs": dml["n_dml_obs"],
            "n_det": dml["n_det"],
            "n_sto": dml["n_sto"],
            # Cliff's
            "cliff_delta": cliff_delta,
            "cliff_ci_lo": cliff_lo,
            "cliff_ci_hi": cliff_hi,
            "cliff_verdict": cliff_verdict_paper,
            # Newey-West
            "nw_beta": nw_beta,
            "nw_tstat": nw_t,
            "nw_p_two": nw_p,
            # LinearDML
            "lin_dml_ate": lin.get("ate"),
            "lin_dml_ci_lo": lin.get("ci_lo"),
            "lin_dml_ci_hi": lin.get("ci_hi"),
            "lin_dml_verdict": lin.get("direction_verdict"),
            "lin_dml_insight": lin_insight,
            # CausalForestDML
            "cf_dml_ate": cf.get("ate"),
            "cf_dml_ci_lo": cf.get("ci_lo"),
            "cf_dml_ci_hi": cf.get("ci_hi"),
            "cf_dml_verdict": cf.get("direction_verdict"),
            "cf_dml_insight": cf_insight,
        })

    # Console summary
    print(f"\n  Per-market direction labels (4 methods):\n")
    print(f"  {'market':<8}  {'Cliff δ':<9}  {'NW β/t':<14}  {'LinDML ATE':<14}  {'CF-DML ATE':<14}  {'verdicts (Cliff/NWp/LinDML/CF)':<35}")
    for r in rows:
        nw_str = f"{r['nw_beta']:+.2f}/{r['nw_tstat']:+.2f}"
        lin_str = f"{r['lin_dml_ate']:+.3f}±{(r['lin_dml_ci_hi']-r['lin_dml_ci_lo'])/2:.2f}"
        cf_str  = f"{r['cf_dml_ate']:+.3f}±{(r['cf_dml_ci_hi']-r['cf_dml_ci_lo'])/2:.2f}"
        nw_verdict = "sig" if (not _is_nan(r['nw_p_two']) and r['nw_p_two'] < 0.05) else "n.s."
        verdicts = f"{r['cliff_verdict'][:7]:<7}/{nw_verdict:<5}/{r['lin_dml_verdict']:<8}/{r['cf_dml_verdict']:<8}"
        print(f"  {r['market']:<8}  {r['cliff_delta']:+.3f}    {nw_str:<14}  {lin_str:<14}  {cf_str:<14}  {verdicts}")

    # Insight summary
    print(f"\n  Insight classification (LinearDML vs Cliff's δ):")
    for r in rows:
        marker = "✓" if "AGREE" in r["lin_dml_insight"] else "★"
        print(f"  {marker} {r['market']:<8}  Lin: {r['lin_dml_insight']:<45}  CF: {r['cf_dml_insight']}")

    # Aggregate statistics
    n_agree_lin = sum(1 for r in rows if "AGREE" in r["lin_dml_insight"])
    n_tighter_lin = sum(1 for r in rows if "DML_TIGHTER" in r["lin_dml_insight"])
    n_looser_lin = sum(1 for r in rows if "DML_LOOSER" in r["lin_dml_insight"])
    n_flip_lin = sum(1 for r in rows if "DIRECTION_FLIP" in r["lin_dml_insight"])
    n_agree_cf = sum(1 for r in rows if "AGREE" in r["cf_dml_insight"])

    print(f"\n  Aggregate (LinearDML vs Cliff's δ):")
    print(f"    AGREE:           {n_agree_lin}/8")
    print(f"    DML_TIGHTER:     {n_tighter_lin}/8 (controls absorbed nuisance)")
    print(f"    DML_LOOSER:      {n_looser_lin}/8 (effect confounded with lags)")
    print(f"    DIRECTION_FLIP:  {n_flip_lin}/8")
    print(f"\n  Aggregate (CausalForestDML vs Cliff's δ):")
    print(f"    AGREE:           {n_agree_cf}/8")

    # Outcome class assessment per A.9.3 rubric
    n_disagree_lin = 8 - n_agree_lin
    if n_flip_lin > 0 or n_tighter_lin >= 3 or n_looser_lin >= 3:
        outcome = "Class I (Strong insight)"
    elif n_disagree_lin >= 1:
        outcome = "Class II (Moderate insight)"
    elif n_disagree_lin == 0:
        outcome = "Class III (Marginal insight)"
    else:
        outcome = "Class IV (Null insight)"

    print(f"\n  Provisional outcome class: {outcome}")
    print(f"  (User reviews and confirms)")

    payload = {
        "spec": "H1 method comparison: DML vs Cliff's delta + Newey-West HAC",
        "n_markets": len(rows),
        "rows": rows,
        "aggregate": {
            "agree_lin": n_agree_lin,
            "tighter_lin": n_tighter_lin,
            "looser_lin": n_looser_lin,
            "flip_lin": n_flip_lin,
            "agree_cf": n_agree_cf,
        },
        "provisional_outcome_class": outcome,
    }
    out_path = os.path.join(OUTPUT_DIR, "h1_method_comparison.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)
    print(f"\n  JSON: {out_path}")
    return 0


def _is_nan(x) -> bool:
    try:
        return x != x
    except Exception:
        return True


if __name__ == "__main__":
    sys.exit(main())
