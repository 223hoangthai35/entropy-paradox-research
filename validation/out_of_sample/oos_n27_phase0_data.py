"""
oos-n27-rigor PHASE 0 — data gate + frozen snapshot.

Fetch all 27 markets for 2018-01-01 → 2026-06-30, freeze each to
results_v2/oos_n27/data_snapshot/<MARKET>.csv with SHA256, and evaluate
gate G0 (approved policy: markets that fail are dropped, n−k; NO substitutes).

tvdatafeed markets (KSE100, DSEX, SBITOP) are marked 'tvdatafeed-unavailable'
if the package is not importable in this environment — pending user install
of git+https://github.com/rongardF/tvdatafeed.git; phase 0 can be re-run for
just those markets afterwards (existing snapshots are not refetched unless
--refetch is passed).

Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/oos_n27_phase0_data.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from validation._features import load_ohlcv
from validation.markets_n27 import MARKETS_N27
from validation.out_of_sample.oos_n27_common import (
    START, OOS_END, REPRO_END, OOS_DIR, snapshot_path, sha256_file,
)

MIN_LAST_DATE = pd.Timestamp("2026-06-20")   # allow holidays/low liquidity
MIN_BARS = 1600                              # ~504 floor + usable labeled span
GATE_MIN_MARKETS = 25


def fetch_one(cfg: dict, refetch: bool) -> dict:
    name = cfg["name"]
    path = snapshot_path(name)
    rec: dict = {"market": name, "ticker": cfg["ticker"], "source": cfg["source"],
                 "tier_rank": cfg["tier_rank"], "category": cfg["category"]}
    if os.path.exists(path) and not refetch:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        rec["status"] = "snapshot-exists"
    else:
        try:
            df = load_ohlcv(name, cfg["ticker"], cfg["source"], START, OOS_END)
        except ImportError as e:
            rec.update(status="tvdatafeed-unavailable", error=str(e)[:200])
            return rec
        except Exception as e:
            rec.update(status=f"fetch-failed", error=f"{type(e).__name__}: {str(e)[:200]}")
            return rec
        if df is None or df.empty:
            rec.update(status="fetch-empty")
            return rec
        df.to_csv(path)
        rec["status"] = "fetched"

    rec.update(
        n_bars=int(len(df)),
        first=str(df.index[0].date()), last=str(df.index[-1].date()),
        n_bars_to_repro_end=int((df.index <= pd.Timestamp(REPRO_END)).sum()),
        sha256=sha256_file(path),
    )
    checks = {
        "coverage_end": pd.Timestamp(rec["last"]) >= MIN_LAST_DATE,
        "enough_bars": rec["n_bars"] >= MIN_BARS,
        "covers_old_window": rec["n_bars_to_repro_end"] >= MIN_BARS - 60,
    }
    rec["checks"] = checks
    rec["gate_ok"] = all(checks.values())
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refetch", action="store_true")
    ap.add_argument("--markets", type=str, default="")
    args = ap.parse_args()

    markets = MARKETS_N27
    if args.markets:
        wanted = {m.strip().upper() for m in args.markets.split(",")}
        markets = [m for m in MARKETS_N27 if m["name"].upper() in wanted]

    print("=" * 74)
    print(f"  oos-n27-rigor PHASE 0 — data gate + snapshot ({len(markets)} markets)")
    print("=" * 74)
    t0 = time.time()
    records = []
    for cfg in markets:
        rec = fetch_one(cfg, args.refetch)
        records.append(rec)
        if rec.get("gate_ok"):
            print(f"  OK    {rec['market']:<9} {rec['n_bars']:>5} bars "
                  f"{rec['first']} → {rec['last']}  [{rec['status']}]")
        else:
            why = rec.get("error", "") or json.dumps(rec.get("checks", {}))
            print(f"  FAIL  {rec['market']:<9} [{rec['status']}] {why[:90]}")

    # Merge with an existing manifest (partial re-runs must not clobber it)
    out = os.path.join(OOS_DIR, "phase0_manifest.json")
    if os.path.exists(out) and args.markets:
        with open(out, encoding="utf-8") as f:
            prev = {r["market"]: r for r in json.load(f)["records"]}
        prev.update({r["market"]: r for r in records})
        records = [prev[m["name"]] for m in MARKETS_N27 if m["name"] in prev]

    ok = [r for r in records if r.get("gate_ok")]
    manifest = {
        "spec": "oos-n27-rigor phase 0 snapshot manifest",
        "window": [START, OOS_END],
        "n_attempted": len(records), "n_ok": len(ok),
        "gate_min_markets": GATE_MIN_MARKETS,
        "gate_G0": "PASS" if len(ok) >= GATE_MIN_MARKETS else "REVIEW",
        "records": records,
        "elapsed_seconds": float(time.time() - t0),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)

    print("\n" + "=" * 74)
    print(f"  GATE G0: {manifest['gate_G0']} — {len(ok)}/{len(records)} markets usable "
          f"(min {GATE_MIN_MARKETS}); policy on failures: run n−k, no substitutes")
    print("=" * 74)
    print(f"  manifest: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
