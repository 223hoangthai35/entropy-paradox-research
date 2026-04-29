"""
Shuffle Test -- Test 3 of Case A Validation.

H1 (Case A): the post-hysteresis label sequence has temporal structure --
    consecutive bars are NOT exchangeable, so the observed flip rate is much
    lower than what random permutation of the same labels would produce.
H0: the label sequence is indistinguishable from a random permutation of its
    own marginals (i.e. labels could appear in any order).

Method:
  1. Take the post-hysteresis label series.
  2. Compute the observed flip rate (annualized).
  3. Permute the label sequence n=10000 times. Each permutation preserves the
     empirical marginal distribution (counts of each regime) but destroys all
     temporal structure.
  4. p-value = fraction of permutations with flip rate <= observed.
     A small p-value means "almost no random shuffle is as quiet as the
     observed sequence" -> labels are temporally structured.

Theoretical floor: for K equiprobable labels, expected per-bar transition
probability under random permutation is 1 - 1/K = 0.667 for K=3, so the
random null mean should be roughly 0.667 * 252 = 168 flips/yr -- orders of
magnitude above the observed 7.77 flips/yr if the system is structured.

Run:
    python validation/shuffle_test.py
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.extract_flip_dates import get_filtered_labels


N_PERMUTATIONS: int = 10_000
RANDOM_SEED:    int = 42
TRADING_DAYS:   int = 252

P_VALUE_THRESHOLD = 0.01    # T3 PASS iff p-value below this
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
RESULT_PATH = os.path.join(RESULTS_DIR, "shuffle_test_result.json")


@dataclass
class ShuffleTestResult:
    market: str
    start: str
    end: str
    n_bars: int
    label_marginals: Dict[int, float]
    observed_flip_rate: float
    null_mean: float
    null_std: float
    null_p05: float
    null_p95: float
    null_min: float
    null_max: float
    p_value: float
    n_permutations: int
    seed: int
    verdict: str


def _flips_per_year(arr: np.ndarray, n_bars: int) -> float:
    return float((np.diff(arr) != 0).sum()) * TRADING_DAYS / n_bars


def run_shuffle_test(
    labels: pd.Series,
    n_permutations: int = N_PERMUTATIONS,
    seed: int = RANDOM_SEED,
    market: str = "VNINDEX",
    start: str = "2020-01-01",
    end: str = "2026-04-17",
) -> ShuffleTestResult:
    arr = labels.astype(int).values
    n_bars = len(arr)
    if n_bars < 2:
        raise ValueError("Need at least 2 labels.")

    observed_rate = _flips_per_year(arr, n_bars)

    rng = np.random.default_rng(seed)
    null_rates = np.empty(n_permutations, dtype=np.float64)
    work = arr.copy()
    for i in range(n_permutations):
        rng.shuffle(work)
        null_rates[i] = _flips_per_year(work, n_bars)

    p_value = float((null_rates <= observed_rate).mean())
    verdict = "STRUCTURED" if p_value < P_VALUE_THRESHOLD else "NOT_STRUCTURED"

    unique, counts = np.unique(arr, return_counts=True)
    marginals = {int(u): float(c) / n_bars for u, c in zip(unique, counts)}

    return ShuffleTestResult(
        market=market, start=start, end=end,
        n_bars=n_bars,
        label_marginals=marginals,
        observed_flip_rate=observed_rate,
        null_mean=float(null_rates.mean()),
        null_std=float(null_rates.std()),
        null_p05=float(np.percentile(null_rates, 5)),
        null_p95=float(np.percentile(null_rates, 95)),
        null_min=float(null_rates.min()),
        null_max=float(null_rates.max()),
        p_value=p_value,
        n_permutations=n_permutations,
        seed=seed,
        verdict=verdict,
    )


def format_result(r: ShuffleTestResult) -> str:
    margin = ", ".join(f"{k}:{v:.1%}" for k, v in sorted(r.label_marginals.items()))
    lines = [
        "=" * 68,
        f"SHUFFLE TEST -- {r.market} {r.start} -> {r.end}",
        "=" * 68,
        f"Bars analyzed:           {r.n_bars}",
        f"Label marginals:         {margin}",
        f"Permutations:            {r.n_permutations}",
        "",
        f"Observed flip rate:      {r.observed_flip_rate:7.2f} / yr",
        f"Null mean:               {r.null_mean:7.2f} / yr",
        f"Null std:                {r.null_std:7.2f}",
        f"Null 5th-95th pct:       [{r.null_p05:6.2f}, {r.null_p95:6.2f}]",
        f"Null min-max:            [{r.null_min:6.2f}, {r.null_max:6.2f}]",
        f"p-value (one-sided):     {r.p_value:.4f}",
        "",
        f"VERDICT: {r.verdict}  (PASS iff p < {P_VALUE_THRESHOLD})",
    ]
    return "\n".join(lines)


def save_result(r: ShuffleTestResult, path: str = RESULT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "market": r.market, "start": r.start, "end": r.end,
        "n_bars": r.n_bars,
        "label_marginals": r.label_marginals,
        "observed_flip_rate": r.observed_flip_rate,
        "null_mean": r.null_mean,
        "null_std": r.null_std,
        "null_p05": r.null_p05,
        "null_p95": r.null_p95,
        "null_min": r.null_min,
        "null_max": r.null_max,
        "p_value": r.p_value,
        "n_permutations": r.n_permutations,
        "seed": r.seed,
        "p_value_threshold": P_VALUE_THRESHOLD,
        "verdict": r.verdict,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def main() -> int:
    end = "2026-04-17"
    start = "2020-01-01"
    market = "VNINDEX"
    print(f"  Loading filtered label series for {market} ...")
    labels = get_filtered_labels(market=market, start=start, end=end)
    print(f"  Got {len(labels)} labeled bars.")
    result = run_shuffle_test(
        labels, market=market, start=start, end=end
    )
    print(format_result(result))
    save_result(result)
    print(f"\n  Result saved to: {RESULT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
