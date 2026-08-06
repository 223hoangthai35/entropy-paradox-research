"""Two-tier regression guard for the pre-registered legacy columns.

The problem this replaces
------------------------
The original guard compared every run against `results_v2/prereg_b130b0f/`, the
archive frozen at pre-registration (2026-04-18). That archive was computed on a
window ending 2026-04-17, on the BVB.RO exchange-operator stock rather than the
BET index, and on a frontier panel containing PSEI rather than BVB. The analysis
has since moved deliberately on all three axes. The guard therefore fired on
every run -- aborting the script AFTER it had already written its outputs. A
guard that always fails guards nothing, and a referee attempting to reproduce
would meet an AssertionError on a correct run.

The mechanism here
------------------
Two baselines with different jobs, and they must not be conflated.

  CANONICAL (blocking).  Frozen against the current analysis window and
  instrument set. Its job is to catch UNINTENDED drift: a refactor, a library
  upgrade, a seed change that silently moves a number. A mismatch here is a
  defect and aborts the run.

  REGISTRATION (informational, never blocks).  `prereg_b130b0f/`, untouched.
  Its job is to make the distance travelled since pre-registration visible and
  auditable. Differences here are expected -- they are the window extension and
  the instrument correction -- so reporting them is the point, and failing on
  them is not.

Re-freezing the canonical baseline is deliberate and explicit: it requires
REFREEZE_BASELINE=1 in the environment. It can never happen as a side effect of
a normal run, so a moved number can never be absorbed silently.
"""
from __future__ import annotations

import os
import shutil
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(_HERE, "results_v2")

# Registration-era archive: read-only, informational, never blocks.
REGISTRATION_DIR = os.path.join(RESULTS_DIR, "prereg_b130b0f")
REGISTRATION_LABEL = "pre-registration 2026-04-18 (window to 2026-04-17, BVB.RO, PSEI panel)"

# Canonical baseline: the current analysis window and instrument set.
CANONICAL_DIR = os.path.join(RESULTS_DIR, "baseline_canonical")
CANONICAL_LABEL = "canonical (window to 2026-06-30, BVB:BET index)"

TOL = 1e-4
REFREEZE = os.environ.get("REFREEZE_BASELINE", "") == "1"


def _keyed(df: pd.DataFrame, key: str | list[str]) -> pd.DataFrame:
    """Index by `key`, building a composite index when key is several columns.

    Composite keys are built on BOTH sides here rather than by the caller, so a
    baseline CSV written before the key existed still compares correctly.
    """
    if isinstance(key, (list, tuple)):
        d = df.copy()
        d["_key"] = d[list(key)].astype(str).agg("|".join, axis=1)
        return d.set_index("_key")
    return df.set_index(key)


def _cmp(old: pd.DataFrame, new: pd.DataFrame, key: str | list[str],
         num_cols: list[str], str_cols: list[str]) -> list[tuple]:
    o, n = _keyed(old, key), _keyed(new, key)
    common = sorted(set(o.index) & set(n.index))
    out = []
    for m in common:
        for c in num_cols:
            if c not in o.columns or c not in n.columns:
                continue
            ov, nv = float(o.loc[m, c]), float(n.loc[m, c])
            if np.isnan(ov) and np.isnan(nv):
                continue
            if not np.isclose(ov, nv, rtol=0, atol=TOL, equal_nan=False):
                out.append((m, c, ov, nv))
        for c in str_cols:
            if c not in o.columns or c not in n.columns:
                continue
            if str(o.loc[m, c]) != str(n.loc[m, c]):
                out.append((m, c, o.loc[m, c], n.loc[m, c]))
    return out, common, sorted(set(o.index) ^ set(n.index))


def guard(new_df: pd.DataFrame, artifact: str, *, key: str | list[str] = "market",
          num_cols: list[str], str_cols: list[str] | None = None) -> None:
    """Check `new_df` against the canonical baseline; report the registration diff.

    Aborts only on canonical drift. Missing canonical baseline is reported as
    UNGUARDED rather than silently passing, so the gap is visible in the log.
    """
    str_cols = str_cols or []
    print(f"\n[regression] artifact: {artifact}")

    # ---- tier 2: registration-era diff, informational -----------------------
    reg_csv = os.path.join(REGISTRATION_DIR, artifact)
    if os.path.exists(reg_csv):
        try:
            mism, common, only = _cmp(pd.read_csv(reg_csv), new_df, key, num_cols, str_cols)
            if mism or only:
                print(f"  [info] differs from {REGISTRATION_LABEL} "
                      f"-- {len(mism)} value(s) across {len(common)} shared "
                      f"{key}s; {len(only)} {key}(s) present in only one panel.")
                print("         Expected: the window extension and the instrument "
                      "correction are deliberate. Not a failure condition.")
                for m, c, ov, nv in mism[:6]:
                    print(f"           {str(m):10s} {c:22s} registered={ov}  now={nv}")
                if len(mism) > 6:
                    print(f"           ... and {len(mism) - 6} more")
            else:
                print(f"  [info] identical to {REGISTRATION_LABEL}.")
        except Exception as e:
            print(f"  [info] registration diff unavailable ({type(e).__name__}: {e})")

    # ---- tier 1: canonical baseline, blocking -------------------------------
    os.makedirs(CANONICAL_DIR, exist_ok=True)
    can_csv = os.path.join(CANONICAL_DIR, artifact)

    if not os.path.exists(can_csv):
        if REFREEZE:
            new_df.to_csv(can_csv, index=False)
            print(f"  [FROZEN] canonical baseline created: {artifact}")
            print(f"           {CANONICAL_LABEL}")
        else:
            print(f"  [UNGUARDED] no canonical baseline for {artifact}.")
            print(f"              Create it deliberately with REFREEZE_BASELINE=1.")
        return

    mism, common, only = _cmp(pd.read_csv(can_csv), new_df, key, num_cols, str_cols)
    if only:
        print(f"  [note] panel membership differs from the canonical baseline "
              f"by {len(only)} {key}(s): {only}")
    if not mism:
        print(f"  [OK] matches the canonical baseline on {len(common)} {key}s "
              f"across {len(num_cols) + len(str_cols)} columns (atol={TOL}).")
        return

    if REFREEZE:
        shutil.copy2(can_csv, can_csv + ".superseded")
        new_df.to_csv(can_csv, index=False)
        print(f"  [RE-FROZEN] canonical baseline updated ({len(mism)} value(s) moved); "
              f"previous kept as {os.path.basename(can_csv)}.superseded")
        return

    print(f"\n  [REGRESSION FAIL] {len(mism)} value(s) drift from the canonical baseline:")
    for m, c, ov, nv in mism:
        print(f"    {str(m):10s} {c:22s} baseline={ov}  new={nv}")
    raise AssertionError(
        f"{artifact}: values moved against the canonical baseline "
        f"({CANONICAL_LABEL}). If the change is intended -- a new analysis window, "
        f"a corrected instrument, a deliberate specification change -- re-freeze "
        f"with REFREEZE_BASELINE=1 and say so in the changelog. If it is not "
        f"intended, this is the defect the guard exists to catch."
    )
