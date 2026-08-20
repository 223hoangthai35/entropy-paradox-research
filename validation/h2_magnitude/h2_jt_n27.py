"""Jonckheere-Terpstra ordered-alternative test on the n=27 panel (permutation p).

Ordered alternative: H increases along Developed < Crypto < Emerging < Frontier
(tier_rank 1 < 2 < 3 < 4) — the granularity-matched tier-block test of Sec 4.2.3.
Runs on both H and eta^2, raw and filtered labels, reading the committed
h2_eta_squared_n27.json (must run that script first).

Output: validation/results_v2/n27_experiment/h2_jt_n27.json
"""
import json
import os
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))
from validation.markets_n27 import MARKETS_N27  # noqa: E402

RES = os.path.join(_VALIDATION, "results_v2", "n27_experiment")
N_PERM = 20_000
SEED = 42

TIER_RANK = {c["name"]: c["tier_rank"] for c in MARKETS_N27}


def jt_stat(samples: list[np.ndarray]) -> float:
    t = 0.0
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            for x in samples[i]:
                t += float((samples[j] > x).sum()) + 0.5 * float((samples[j] == x).sum())
    return t


def jt_perm_p(samples: list[np.ndarray], rng: np.random.Generator) -> tuple[float, float]:
    obs = jt_stat(samples)
    pool = np.concatenate(samples)
    sizes = [len(s) for s in samples]
    count = 0
    for _ in range(N_PERM):
        rng.shuffle(pool)
        parts, k = [], 0
        for s in sizes:
            parts.append(pool[k:k + s]); k += s
        if jt_stat(parts) >= obs:
            count += 1
    return obs, (count + 1) / (N_PERM + 1)


def main() -> int:
    with open(os.path.join(RES, "h2_eta_squared_n27.json"), encoding="utf-8") as f:
        pm = json.load(f)["per_market"]
    out = {"spec": ("JT ordered-alternative on n=27, ascending tier_rank "
                    "(Developed 1 < Crypto 2 < Emerging 3 < Frontier 4), "
                    f"permutation p with {N_PERM} shuffles, seed {SEED}"),
           "tests": {}}
    for metric in ("H_stat", "eta_sq"):
        for lbl in ("raw", "filtered"):
            groups: dict[int, list[float]] = {}
            for m, e in pm.items():
                groups.setdefault(TIER_RANK[m], []).append(e[lbl][metric])
            samples = [np.array(groups[k], dtype=float) for k in sorted(groups)]
            rng = np.random.default_rng(SEED)
            obs, p = jt_perm_p(samples, rng)
            key = f"{metric}_{lbl}"
            out["tests"][key] = {"JT": obs, "p_perm_one_sided": p,
                                 "group_sizes": [len(s) for s in samples]}
            print(f"{key:<16} JT={obs:7.1f}  perm-p={p:.4f}")
    path = os.path.join(RES, "h2_jt_n27.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("JSON:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
