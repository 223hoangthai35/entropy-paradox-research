"""
Verify cal_spe_z_global and cal_spe_z_rolling are NOT aliased — they
must produce demonstrably different outputs on the same input.

Run:
    python -m pytest tests/test_spe_z_global_vs_rolling.py -v
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.quant_skill import cal_spe_z_global, cal_spe_z_rolling


def test_outputs_differ_on_drifting_series():
    """A non-stationary series must produce different rolling vs global Z."""
    n = 1500
    rng = np.random.default_rng(42)
    # Step change after rolling window — local distribution has zero variance,
    # global distribution is bimodal: rolling Z behavior diverges from global.
    arr = np.concatenate([
        rng.normal(0.0, 1.0, 600),
        rng.normal(10.0, 1.0, 900),
    ])

    g = cal_spe_z_global(arr)
    r = cal_spe_z_rolling(arr, window=504)

    valid_mask = np.isfinite(g) & np.isfinite(r)
    diffs = np.abs(g[valid_mask] - r[valid_mask])
    assert diffs.max() > 1.0, (
        f"Rolling and global Z must differ on a non-stationary series; "
        f"max abs diff = {diffs.max():.4f}"
    )


def test_global_uses_full_distribution():
    """Global Z at any index uses the full series mean/std — including future."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    g = cal_spe_z_global(arr)

    full_mean = float(np.mean(arr))
    full_std = float(np.std(arr))
    expected = (arr - full_mean) / full_std
    assert np.allclose(g, expected, atol=1e-9)


def test_rolling_window_size_respected():
    """Smaller windows produce different results than larger windows."""
    rng = np.random.default_rng(11)
    arr = rng.standard_normal(1000) + np.linspace(0, 2, 1000)
    z_short = cal_spe_z_rolling(arr, window=60)
    z_long = cal_spe_z_rolling(arr, window=504)

    last_short = z_short[-1]
    last_long = z_long[-1]
    assert np.isfinite(last_short) and np.isfinite(last_long)
    assert abs(last_short - last_long) > 0.05


if __name__ == "__main__":
    tests = [
        test_outputs_differ_on_drifting_series,
        test_global_uses_full_distribution,
        test_rolling_window_size_respected,
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
