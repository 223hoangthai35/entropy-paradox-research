"""H5 (hysteresis parameter robustness) on the n = 27 expansion panel.

H5 was registered and executed on the eight-market panel only. Its verdict there
is a rejection -- SPX 11.7pp and NIFTY 8.8pp exceed the registered 7pp
falsification bound -- so the obvious question is whether that is a property of
two markets or of the parameterisation. Twenty-seven markets answer it.

The machinery is imported from hysteresis_robustness_v2 rather than
reimplemented, so the n = 8 and n = 27 numbers are produced by identical code:
one GMM fit per market, then the three registered Schmitt configurations applied
to that same fitted classifier, then p(Transitional) under each.
"""
from __future__ import annotations

import json
import os
import sys
import time

import pandas as pd

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from validation.h3_h4_h5.hysteresis_robustness_v2 import (  # noqa: E402
    _analyze_market, CONFIGS, H5_SPREAD_THRESHOLD,
)
from validation.markets_n27 import MARKETS_N27  # noqa: E402

OUT_DIR = os.path.join(_VALIDATION, "results_v2", "n27_experiment")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_CSV = os.path.join(OUT_DIR, "h5_n27.csv")
OUT_JSON = os.path.join(OUT_DIR, "h5_n27.json")

# Registered falsification bound. The 5pp figure is the point prediction; a
# market only falsifies H5 by exceeding 7pp.
FALSIFY_PP = 0.07


def main() -> int:
    t0 = time.time()
    rows, blocks, skipped = [], [], []
    for cfg in MARKETS_N27:
        try:
            res = _analyze_market(cfg)
        except Exception as e:
            print(f"[{cfg['name']}] SKIP {type(e).__name__}: {e}")
            skipped.append(cfg["name"])
            continue
        if res is None:
            skipped.append(cfg["name"])
            continue
        blocks.append(res)
        rows.extend(res["rows"])

    if not rows:
        print("[FATAL] no markets produced results")
        return 1

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)

    per_market = []
    for blk in blocks:
        vals = [r["p_tra"] for r in blk["rows"]]
        spread = max(vals) - min(vals)
        per_market.append({
            "market": blk["market"], "category": blk["category"],
            "p_tra_by_config": {r["config"]: r["p_tra"] for r in blk["rows"]},
            "spread": round(spread, 4),
            "spread_pp": round(spread * 100, 1),
            "meets_point_prediction_5pp": bool(spread < H5_SPREAD_THRESHOLD),
            "falsifies_at_7pp": bool(spread > FALSIFY_PP),
        })
    per_market.sort(key=lambda r: -r["spread"])

    breaches = [r for r in per_market if r["falsifies_at_7pp"]]
    misses = [r for r in per_market if not r["meets_point_prediction_5pp"]
              and not r["falsifies_at_7pp"]]

    print("\n" + "=" * 74)
    print(f"H5 ON n = {len(per_market)} (registered configs A/B/C, identical machinery)")
    print("=" * 74)
    print(f"{'market':10} {'category':10} {'spread pp':>10}  verdict")
    for r in per_market:
        v = ("FALSIFIES (>7pp)" if r["falsifies_at_7pp"]
             else "misses 5pp point prediction" if not r["meets_point_prediction_5pp"]
             else "pass")
        print(f"{r['market']:10} {r['category']:10} {r['spread_pp']:>10.1f}  {v}")

    print(f"\n  markets exceeding the 7pp falsification bound: "
          f"{len(breaches)} / {len(per_market)}"
          f"  -> {[r['market'] for r in breaches]}")
    print(f"  markets missing the 5pp point prediction but within 7pp: {len(misses)}"
          f"  -> {[r['market'] for r in misses]}")
    print(f"  H5 VERDICT at n = {len(per_market)}: "
          f"{'REJECT' if breaches else 'PASS'}")

    payload = {
        "spec": "H5 hysteresis parameter robustness on the n=27 expansion panel; "
                "machinery imported from hysteresis_robustness_v2 so n=8 and n=27 "
                "are produced by identical code.",
        "configs": CONFIGS,
        "point_prediction_pp": H5_SPREAD_THRESHOLD * 100,
        "falsification_bound_pp": FALSIFY_PP * 100,
        "n_markets": len(per_market),
        "skipped": skipped,
        "verdict": "REJECT" if breaches else "PASS",
        "breaches": [r["market"] for r in breaches],
        "point_prediction_misses": [r["market"] for r in misses],
        "per_market": per_market,
        "elapsed_min": round((time.time() - t0) / 60, 1),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nCSV:  {OUT_CSV}\nJSON: {OUT_JSON}  ({payload['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
