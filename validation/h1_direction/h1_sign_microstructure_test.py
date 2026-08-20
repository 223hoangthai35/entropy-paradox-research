"""Formal panel-level H1 test: does the D-S direction track microstructure? (referee item A5)

Tests, at n=27 on the committed CF-DML estimates:
  (a) Spearman rho(ATE, RPS) with permutation p (two-sided)   — continuous version
  (b) Spearman rho(sign(ATE), RPS) with permutation p          — sign version
  (c) Fisher exact test on sign x retail-block (RPS>=median vs <median)
  (d) same three against tier_rank
Reads validation/results_v2/n27_experiment/h1_dml_cpcv_n27.json (frozen).

Output: validation/results_v2/h1_sign_microstructure_test.json
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

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))
from validation.markets_n27 import MARKETS_N27  # noqa: E402

SEED = 42
N_PERM = 100_000
RES = os.path.join(_VALIDATION, "results_v2")

RPS_VALUES = json.load(open(os.path.join(
    RES, "n27_experiment", "h2_cascade_n27_full_classification.json"),
    encoding="utf-8"))["all_p1_reference"]["rps_values"]
TIER_RANK = {c["name"]: c["tier_rank"] for c in MARKETS_N27}


def perm_spearman(x, y, rng):
    obs, _ = stats.spearmanr(x, y)
    y = np.asarray(y, dtype=float)
    count = 0
    for _ in range(N_PERM):
        r, _ = stats.spearmanr(x, rng.permutation(y))
        if abs(r) >= abs(obs) - 1e-12:
            count += 1
    return float(obs), (count + 1) / (N_PERM + 1)


def main() -> int:
    d = json.load(open(os.path.join(RES, "n27_experiment", "h1_dml_cpcv_n27.json"),
                       encoding="utf-8"))["results"]
    ms, ates = [], []
    for m, e in d.items():
        cf = e.get("causal_forest_dml") or {}
        if cf.get("fit_status") == "ok":
            ms.append(m); ates.append(cf["ate"])
    ates = np.array(ates)
    signs = np.sign(ates)
    rps = np.array([RPS_VALUES[m] for m in ms])
    tier = np.array([TIER_RANK[m] for m in ms], dtype=float)
    rng = np.random.default_rng(SEED)

    out = {"spec": ("Panel-level H1 direction-vs-microstructure tests on the committed n=27 "
                    f"CF-DML ATEs; permutation p ({N_PERM} shuffles, seed {SEED}), two-sided. "
                    "Fisher exact on sign x median-split blocks."),
           "n": len(ms), "tests": {}}

    for pred_name, pred in (("RPS", rps), ("tier_rank", tier)):
        r_ate, p_ate = perm_spearman(ates, pred, rng)
        r_sgn, p_sgn = perm_spearman(signs, pred, rng)
        hi = pred >= np.median(pred)
        table = [[int(((signs > 0) & hi).sum()), int(((signs > 0) & ~hi).sum())],
                 [int(((signs <= 0) & hi).sum()), int(((signs <= 0) & ~hi).sum())]]
        _, p_fisher = stats.fisher_exact(table)
        out["tests"][pred_name] = {
            "rho_ATE": r_ate, "p_perm_ATE": p_ate,
            "rho_sign": r_sgn, "p_perm_sign": p_sgn,
            "fisher_table_[pos/neg]x[hi/lo]": table, "p_fisher": float(p_fisher)}
        print(f"{pred_name:>9}: rho(ATE)={r_ate:+.3f} p={p_ate:.4f} | "
              f"rho(sign)={r_sgn:+.3f} p={p_sgn:.4f} | Fisher p={p_fisher:.4f} {table}")

    path = os.path.join(RES, "h1_direction/h1_sign_microstructure_test.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=float)
    print("JSON:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
