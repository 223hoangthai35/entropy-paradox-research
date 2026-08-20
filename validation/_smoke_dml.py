"""Smoke test for h1_dml.py on VNINDEX only."""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation._features import run_full_pipeline
from validation.h1_direction.h1_dml import build_dml_dataset, fit_linear_dml, fit_causal_forest_dml, PRIMARY_HORIZON
import numpy as np

print("Loading VNINDEX...")
t0 = time.time()
out = run_full_pipeline(market="VNINDEX", ticker="VNINDEX", source="vnstock",
                         start="2018-01-01", end="2026-04-17")
print(f"  bars: {len(out['raw_labels'])} (loaded in {time.time()-t0:.1f}s)")

df = build_dml_dataset(out["ohlcv"], out["raw_labels"], horizon=PRIMARY_HORIZON)
print(f"  DML obs: {len(df)} (Det={int(df['T'].sum())}, Sto={int((1-df['T']).sum())})")
print(f"  Controls ({len([c for c in df.columns if c not in ('fwd_vol','T','regime')])}): "
      f"{[c for c in df.columns if c not in ('fwd_vol','T','regime')]}")

print("\nFitting LinearDML...")
rng = np.random.default_rng(42)
t0 = time.time()
lin_res = fit_linear_dml(df, rng)
print(f"  Time: {time.time()-t0:.1f}s")
print(f"  Result: ATE = {lin_res['ate']:+.4f} CI [{lin_res['ci_lo']:+.4f}, {lin_res['ci_hi']:+.4f}] -> {lin_res['direction_verdict']}")
print(f"  Status: {lin_res['fit_status']}")

print("\nFitting CausalForestDML...")
t0 = time.time()
cf_res = fit_causal_forest_dml(df, rng)
print(f"  Time: {time.time()-t0:.1f}s")
print(f"  Result: ATE = {cf_res['ate']:+.4f} CI [{cf_res['ci_lo']:+.4f}, {cf_res['ci_hi']:+.4f}] -> {cf_res['direction_verdict']}")
print(f"  Status: {cf_res['fit_status']}")
