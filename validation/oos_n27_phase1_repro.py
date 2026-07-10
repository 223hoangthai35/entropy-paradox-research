"""
oos-n27-rigor PHASE 1 — pipeline both windows from the frozen snapshot +
replication check against the frozen n27 archive (gate G1).

For every market that passed gate G0: run the canonical pipeline (from
snapshot) at END = 2026-04-17 (repro) and END = 2026-06-30 (extended);
compute KW-H / η² (raw + filtered), shares, flip rates; persist label
series for phases 2–5; compare the repro column against
results_v2/n27_experiment/h2_eta_squared_n27.json per market.

Classification of repro-vs-frozen drift (heuristic, stated in the plan):
  exact    |ΔH|/H_frozen < 1e-3      → environment reproduces
  minor    < 5%                       → small numeric drift, note
  REVISION ≥ 5%                       → input data changed (BVB-style);
                                        Apr→Jun comparisons use repro as base

Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/oos_n27_phase1_repro.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validation._features import flip_rate_per_year
from validation.h2_eta_squared import compute_kw_h_and_eta
from validation.oos_n27_common import (
    REPRO_END, OOS_END, OOS_DIR, pipeline_from_snapshot, save_labels,
)

FROZEN = os.path.join(os.path.dirname(__file__), "results_v2",
                      "n27_experiment", "h2_eta_squared_n27.json")


def regime_shares(labels) -> dict:
    arr = labels.astype(int).to_numpy()
    return {k: float((arr == i).mean()) for i, k in
            enumerate(["det", "tra", "sto"])}


def main() -> int:
    with open(os.path.join(OOS_DIR, "phase0_manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    ok_records = [r for r in manifest["records"] if r.get("gate_ok")]
    markets = [r["market"] for r in ok_records]
    source_of = {r["market"]: r["source"] for r in ok_records}

    frozen = {}
    if os.path.exists(FROZEN):
        with open(FROZEN, encoding="utf-8") as f:
            frozen = json.load(f).get("per_market", {})

    print("=" * 74)
    print(f"  oos-n27-rigor PHASE 1 — pipeline ×2 windows + replication check "
          f"({len(markets)} markets)")
    print("=" * 74)
    t0 = time.time()
    per_market: dict[str, dict] = {}
    for name in markets:
        entry: dict = {}
        try:
            for win, end in [("repro", REPRO_END), ("extended", OOS_END)]:
                out = pipeline_from_snapshot(name, end, source_of[name])
                save_labels(name, win, out)
                entry[win] = {
                    "n_bars": int(len(out["features"])),
                    "kw_raw": compute_kw_h_and_eta(out["ohlcv"], out["raw_labels"]),
                    "kw_filtered": compute_kw_h_and_eta(out["ohlcv"], out["filtered_labels"]),
                    "shares_filtered": regime_shares(out["filtered_labels"]),
                    "flip_rate_filtered": flip_rate_per_year(out["filtered_labels"]),
                }
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {str(e)[:150]}"
            per_market[name] = entry
            print(f"  ERR   {name:<9} {entry['error']}")
            continue

        fro = frozen.get(name, {})
        H_fro = (fro.get("raw") or {}).get("H_stat")
        H_rep = entry["repro"]["kw_raw"]["H_stat"]
        if H_fro:
            rel = abs(H_rep - H_fro) / abs(H_fro)
            entry["repro_vs_frozen"] = {
                "H_raw_frozen": H_fro, "H_raw_repro": H_rep, "rel_diff": rel,
                "class": ("exact" if rel < 1e-3 else
                          "minor" if rel < 0.05 else "REVISION"),
            }
        else:
            entry["repro_vs_frozen"] = {"class": "no-frozen-baseline"}

        c = entry["repro_vs_frozen"]["class"]
        flag = "  " if c in ("exact",) else ("~ " if c == "minor" else "! ")
        H_ext = entry["extended"]["kw_raw"]["H_stat"]
        print(f"  {flag}{name:<9} H_raw frozen={H_fro if H_fro else float('nan'):>7.2f} "
              f"repro={H_rep:>7.2f} [{c:<9}]  extended={H_ext:>7.2f}  "
              f"bars {entry['repro']['n_bars']}→{entry['extended']['n_bars']}")
        per_market[name] = entry

    classes = [e.get("repro_vs_frozen", {}).get("class") for e in per_market.values()
               if "error" not in e]
    summary = {c: classes.count(c) for c in
               ["exact", "minor", "REVISION", "no-frozen-baseline"]}
    payload = {
        "spec": "oos-n27-rigor phase 1: pipeline ×2 windows + repro-vs-frozen check",
        "n_markets": len(per_market),
        "class_summary": summary,
        "per_market": per_market,
        "elapsed_seconds": float(time.time() - t0),
    }
    out = os.path.join(OOS_DIR, "phase1_repro_check.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    print("\n" + "=" * 74)
    print(f"  GATE G1: {summary}")
    print(f"  markets classified REVISION use the repro column as the Apr→Jun base")
    print("=" * 74)
    print(f"  JSON: {out}   ({(time.time()-t0)/60:.1f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
