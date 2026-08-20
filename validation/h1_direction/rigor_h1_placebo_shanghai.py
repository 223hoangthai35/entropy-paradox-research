"""Canonical-window rotation-placebo p_cal for SHANGHAI (n=27 flagship claim).

Same battery as rigor_h1_placebo.py (circular rotation offsets in [252, n-252],
full canonical estimator CF-DML + PurgedKFold per rotation), run for SHANGHAI
at END=2026-06-30 so the abstract's grading can apply the two-gate rule at the
canonical window instead of citing the archived-era p_cal.

Output: validation/results_v2/oos_2026q2/rigor_h1_placebo_shanghai.json
"""
import json
import os
import sys
import time
import zlib

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

from validation._features import run_full_pipeline  # noqa: E402
from validation.h1_direction.h1_dml import START, PRIMARY_HORIZON, build_dml_dataset  # noqa: E402
from validation.h1_direction.h1_dml_cpcv import fit_causal_forest_dml_cpcv  # noqa: E402
from validation.markets_n27 import MARKETS_N27  # noqa: E402

END = "2026-06-30"
RNG_SEED = 42
N_ROT = int(os.environ.get("PLACEBO_ROT_SHANGHAI", "100"))

OOS_DIR = os.path.join(_VALIDATION, "results_v2", "oos_2026q2")
os.makedirs(OOS_DIR, exist_ok=True)


def main() -> int:
    t0 = time.time()
    cfg = next(c for c in MARKETS_N27 if c["name"] == "SHANGHAI")
    out = run_full_pipeline(market="SHANGHAI", ticker=cfg["ticker"],
                            source=cfg["source"], start=START, end=END)
    filt = out["filtered_labels"]
    n = len(filt)
    rng = np.random.default_rng(RNG_SEED + zlib.crc32(b"SHANGHAI") % 1000)

    ref = json.load(open(os.path.join(_VALIDATION, "results_v2",
                                      "n27_experiment", "h1_dml_cpcv_n27.json"),
                         encoding="utf-8"))["results"]["SHANGHAI"]["causal_forest_dml"]
    real_ate = ref["ate"]
    print(f"real SHANGHAI ATE (canonical n27 run): {real_ate:+.3f} "
          f"[{ref['ci_lo']:+.2f},{ref['ci_hi']:+.2f}]")

    placebos = []
    for r in range(N_ROT):
        off = int(rng.integers(252, n - 252))
        lab_rot = pd.Series(np.roll(filt.to_numpy(), off), index=filt.index)
        df_p = build_dml_dataset(out["ohlcv"], lab_rot, horizon=PRIMARY_HORIZON)
        if int(df_p["T"].sum()) < 30 or int((1 - df_p["T"]).sum()) < 30:
            continue
        cf = fit_causal_forest_dml_cpcv(df_p, rng)
        cf["offset"] = off
        placebos.append(cf)
        if cf.get("fit_status") == "ok" and (r + 1) % 10 == 0:
            print(f"  rot {r+1}/{N_ROT}  t+{(time.time()-t0)/60:.1f}m")

    ok = [p for p in placebos if p.get("fit_status") == "ok"]
    ates = np.array([p["ate"] for p in ok])
    p_cal = (1 + int((np.abs(ates) >= abs(real_ate)).sum())) / (1 + len(ok))
    fp = [p for p in ok if p["direction_verdict"] in ("Paradox", "Inverted")]
    doc = {"spec": ("SHANGHAI canonical-window rotation placebo, same machinery as "
                    "rigor_h1_placebo.py; real ATE from frozen h1_dml_cpcv_n27.json."),
           "window": [START, END], "n_rot": N_ROT, "n_ok": len(ok),
           "real_ate": real_ate, "real_ci": [ref["ci_lo"], ref["ci_hi"]],
           "p_cal_one_sided_abs": p_cal,
           "placebo_abs_p95": float(np.percentile(np.abs(ates), 95)) if len(ates) else None,
           "fp_rate_asymptotic": len(fp) / len(ok) if ok else None,
           "placebos": placebos,
           "elapsed_min": round((time.time() - t0) / 60, 1)}
    path = os.path.join(OOS_DIR, "rigor_h1_placebo_shanghai.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, default=float)
    print(f"SHANGHAI p_cal={p_cal:.4f}  (n_ok={len(ok)}, |ATE| p95={doc['placebo_abs_p95']:.2f})")
    print("JSON:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
