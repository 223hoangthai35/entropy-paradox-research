"""
Unit tests for cal_spe_z_rolling — verify NO look-ahead bias.

Run:
    python -m pytest tests/test_spe_z_rolling.py -v
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.quant_skill import cal_spe_z_rolling


def test_rolling_no_lookahead():
    """Z-score at index t must depend ONLY on samples [t-window+1, t]."""
    rng = np.random.default_rng(123)
    full = rng.standard_normal(800)
    window = 504

    full_z = cal_spe_z_rolling(full, window=window)

    pivot = window + 50
    truncated = full[: pivot + 1].copy()
    trunc_z = cal_spe_z_rolling(truncated, window=window)

    assert np.isfinite(full_z[pivot]) and np.isfinite(trunc_z[pivot])
    assert abs(full_z[pivot] - trunc_z[pivot]) < 1e-9, (
        f"Look-ahead detected: rolling Z at t={pivot} differs when future "
        f"samples are present ({full_z[pivot]:.6f}) vs absent ({trunc_z[pivot]:.6f})."
    )


def test_rolling_nan_prefix():
    """First (window-1) entries must be NaN — insufficient history."""
    rng = np.random.default_rng(0)
    arr = rng.standard_normal(1000)
    window = 504

    z = cal_spe_z_rolling(arr, window=window)

    assert np.all(np.isnan(z[: window - 1])), (
        "Rolling Z must be NaN before the first full window."
    )
    assert np.isfinite(z[window - 1]), "First valid index should be window-1."


def test_rolling_zero_centered():
    """Mean of valid rolling Z should hover around zero on stationary input."""
    rng = np.random.default_rng(7)
    arr = rng.standard_normal(2000)
    z = cal_spe_z_rolling(arr, window=504)
    valid = z[np.isfinite(z)]
    assert len(valid) > 0
    # Loose bound — rolling Z is centered per window, aggregated mean ~ 0
    assert abs(float(valid.mean())) < 0.1


def test_rolling_unit_variance_local():
    """Within each rolling window, the Z-score has unit variance by construction."""
    arr = np.linspace(0, 100, 1000) + np.random.default_rng(1).standard_normal(1000) * 5.0
    window = 504
    z = cal_spe_z_rolling(arr, window=window)

    s = pd.Series(arr)
    # Re-derive from definition for an arbitrary index
    t = 800
    mu = s.iloc[t - window + 1 : t + 1].mean()
    sd = s.iloc[t - window + 1 : t + 1].std()
    expected = (arr[t] - mu) / sd
    assert abs(z[t] - expected) < 1e-9


if __name__ == "__main__":
    tests = [
        test_rolling_no_lookahead,
        test_rolling_nan_prefix,
        test_rolling_zero_centered,
        test_rolling_unit_variance_local,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed.")
