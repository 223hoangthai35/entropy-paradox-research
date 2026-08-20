"""
Shared infrastructure for the oos-n27-rigor campaign (plan:
research/outputs/.plans/oos-n27-rigor.md, approved 2026-07-09).

- All inputs are read from the frozen data snapshot written by phase 0
  (results_v2/oos_n27/data_snapshot/) — never from live APIs after phase 0.
  This is the BVB.RO-revision lesson institutionalized.
- Pipeline math is the canonical one: build_plane1_features +
  fit_classifier_and_filter from validation._features (identical to
  run_full_pipeline minus the fetch).
- Seeds derive from zlib.crc32 (PYTHONHASHSEED-independent).
"""
from __future__ import annotations

import hashlib
import os
import zlib

import pandas as pd

from validation._features import build_plane1_features, fit_classifier_and_filter, SPE_Z_WIN

START = "2018-01-01"
REPRO_END = "2026-04-17"
OOS_END = "2026-06-30"
RNG_SEED = 42

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OOS_DIR = os.path.join(_VALIDATION, "results_v2", "oos_n27")
SNAP_DIR = os.path.join(OOS_DIR, "data_snapshot")
LABELS_DIR = os.path.join(OOS_DIR, "labels")
for d in (OOS_DIR, SNAP_DIR, LABELS_DIR):
    os.makedirs(d, exist_ok=True)


def market_seed(name: str) -> int:
    return RNG_SEED + zlib.crc32(name.encode()) % 1000


def snapshot_path(name: str) -> str:
    return os.path.join(SNAP_DIR, f"{name}.csv")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_snapshot(name: str) -> pd.DataFrame:
    df = pd.read_csv(snapshot_path(name), index_col=0, parse_dates=True)
    df.index.name = "Date"
    return df


_PIPE_CACHE: dict[tuple, dict] = {}

# load_ohlcv's yfinance branch fetches with an EXCLUSIVE end date (yfinance
# semantics), so every frozen yfinance run actually ends the bar BEFORE the
# nominal END. vnstock and tvdatafeed are inclusive. Replicating this is
# required for byte-level repro of the frozen archive (n8 frozen date_range:
# VNINDEX →2026-04-17, all yfinance markets →2026-04-16).
END_EXCLUSIVE_SOURCES = {"yfinance"}


def pipeline_from_snapshot(name: str, end: str, source: str = "yfinance") -> dict:
    """Canonical pipeline on the frozen snapshot, cached per (market, end)."""
    key = (name, end, source)
    if key in _PIPE_CACHE:
        return _PIPE_CACHE[key]
    df = load_snapshot(name)
    if source in END_EXCLUSIVE_SOURCES:
        df = df[(df.index >= pd.Timestamp(START)) & (df.index < pd.Timestamp(end))]
    else:
        df = df[(df.index >= pd.Timestamp(START)) & (df.index <= pd.Timestamp(end))]
    feat = build_plane1_features(df)
    if len(feat) < SPE_Z_WIN:
        raise RuntimeError(f"{name}: only {len(feat)} labelable bars (< {SPE_Z_WIN})")
    out = fit_classifier_and_filter(feat, hysteresis_kwargs=None, random_state=RNG_SEED)
    out.update({"ohlcv": df, "features": feat, "market": name, "end": end})
    _PIPE_CACHE[key] = out
    return out


def save_labels(name: str, window: str, out: dict) -> str:
    """Persist label series so later phases share identical labels."""
    path = os.path.join(LABELS_DIR, f"{name}_{window}.csv")
    pd.DataFrame({"raw": out["raw_labels"].astype(int),
                  "filt": out["filtered_labels"].astype(int)}).to_csv(path)
    return path
