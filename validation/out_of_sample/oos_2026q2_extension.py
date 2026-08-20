"""
OOS EXTENSION EXPERIMENT — canonical n=8 suite with END extended
2026-04-17 → 2026-06-30 (+~2.5 months out-of-sample, Q2/2026).

PURPOSE. The JFDS v3.4 manuscript freezes the labeled window at
2020-01-01 → 2026-04-17. This experiment asks: do the headline claims
(H1 direction heterogeneity, H2 tier scaling, Link B mechanism,
regime composition) survive when 2 more months of data are appended?

THIS IS NOT A CANONICAL PAPER RUN. Frozen archive files under
validation/results_v2/ are read-only inputs here; every output of this
script goes to validation/results_v2/oos_2026q2/.

THREE-COLUMN DESIGN (to separate env drift from data effect):
  frozen    — archived results_v2 numbers (original env, END 2026-04-17)
  repro     — this env, END 2026-04-17  (isolates library/data-revision drift)
  extended  — this env, END 2026-06-30  (the out-of-sample question)

MACHINERY REUSE. No statistical code is re-implemented: this driver
monkeypatches module-level END on the canonical modules and calls their
own analyze_market()/compute functions:
  cross_market_v2.analyze_market      — H1 legacy + primary contrast + shares
  h1_dml_cpcv.analyze_market          — LinearDML + CausalForestDML (PurgedKFold)
  h2_eta_squared.compute_kw_h_and_eta — H2 KW-H + η² (canonical H2 numbers)
  link_b_tests.per_market_entropy_stats + permutation_spearman_ci
  link_b_raw_sampen_test-style raw SampEn stats (same formulas)
A per-process cache wraps _features.run_full_pipeline so each
(market, window) is fetched + fitted exactly once and shared by all blocks.

Pinned hyperparameters are untouched (WPE 3/1/22, SampEn 60, SPE_Z 504,
GMM k=3 rs=42, hysteresis 0.60/0.35/8).

Run (deterministic hash for canonical rng-seed derivation):
  PYTHONHASHSEED=0 .venv/Scripts/python.exe validation/oos_2026q2_extension.py
Options:
  --skip-dml            skip the (slow, ~30 min/window) DML block
  --markets A,B         subset of the 8-market panel (smoke tests)
  --windows repro,extended   which windows to run (default both)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_VALIDATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_VALIDATION, ".."))

import validation._features as _features
from validation._features import SPE_Z_WIN, SAMPEN_WIN, flip_dates, flip_rate_per_year
from skills.quant_skill import calc_rolling_price_sample_entropy
from skills.ds_skill import REGIME_NAMES

import validation.h2_magnitude.cross_market_v2 as cmv2
import validation.h2_magnitude.h2_eta_squared as h2e
import validation.mechanism_battery.link_b_tests as lbt

START = "2018-01-01"
REPRO_END = "2026-04-17"      # canonical frozen window
OOS_END = "2026-06-30"        # extension target
OOS_CUTOFF = pd.Timestamp(REPRO_END)

RESULTS_V2 = os.path.join(_VALIDATION, "results_v2")
OOS_DIR = os.path.join(RESULTS_V2, "oos_2026q2")
os.makedirs(OOS_DIR, exist_ok=True)

PANEL = cmv2.MARKETS                      # pre-registered 8-market panel
RPS = dict(lbt.RPS)                       # cascade point values
TIER_RANK = {m["name"]: m["tier_rank"] for m in h2e.MARKETS}

# ------------------------------------------------------------------
# Pipeline cache — one fetch + GMM fit per (market, window), shared by
# every canonical analyze_* block below.
# ------------------------------------------------------------------
_PIPE_CACHE: dict[tuple, dict] = {}


def cached_pipeline(market: str, ticker: str, source: str,
                    start: str, end: str | None = None, **kw) -> dict:
    key = (market, ticker, source, start, end)
    if key not in _PIPE_CACHE:
        t0 = time.time()
        _PIPE_CACHE[key] = _features.run_full_pipeline(
            market=market, ticker=ticker, source=source, start=start, end=end, **kw
        )
        print(f"    [pipeline] {market} {start}→{end}: "
              f"{len(_PIPE_CACHE[key]['features'])} bars ({time.time()-t0:.1f}s)")
    return _PIPE_CACHE[key]


# Patch the canonical modules to route through the cache. OUTPUT_DIR is
# redirected so no canonical writer can touch the frozen archive.
cmv2.run_full_pipeline = cached_pipeline
cmv2.OUTPUT_DIR = OOS_DIR
lbt.run_full_pipeline = cached_pipeline


def _load_dml_module():
    """Import DML modules lazily (econml is heavy) and patch them."""
    import validation.h1_direction.h1_dml_cpcv as h1c
    h1c.run_full_pipeline = cached_pipeline
    return h1c


# ------------------------------------------------------------------
# Extra per-market stats (same formulas as canonical scripts)
# ------------------------------------------------------------------
def raw_sampen_stats(ohlcv: pd.DataFrame) -> dict[str, float]:
    """Mirror link_b_raw_sampen_test.extract_raw_sampen_stats on cached OHLCV."""
    sampen = calc_rolling_price_sample_entropy(ohlcv["Close"].values, window=SAMPEN_WIN)
    sampen = sampen[~np.isnan(sampen)]
    if len(sampen) < SPE_Z_WIN:
        return {"n_obs": int(len(sampen)), "error": "too few observations"}
    lab = sampen[SPE_Z_WIN:]
    return {
        "n_obs": int(len(lab)),
        "mean_raw_SampEn": float(np.mean(lab)),
        "std_raw_SampEn": float(np.std(lab)),
        "median_raw_SampEn": float(np.median(lab)),
        "iqr_raw_SampEn": float(np.percentile(lab, 75) - np.percentile(lab, 25)),
        "p95_raw_SampEn": float(np.percentile(lab, 95)),
        "p05_raw_SampEn": float(np.percentile(lab, 5)),
    }


def regime_shares(labels: pd.Series) -> dict[str, float]:
    n = len(labels)
    named = labels.astype(int).map(REGIME_NAMES)
    return {r: float((named == r).sum() / n) for r in
            ["Deterministic", "Transitional", "Stochastic"]}


def label_segments(labels: pd.Series) -> list[dict[str, Any]]:
    """Contiguous same-regime segments [(from, to, regime, n_bars)]."""
    if len(labels) == 0:
        return []
    named = labels.astype(int).map(REGIME_NAMES)
    segs = []
    seg_start = named.index[0]
    cur = named.iloc[0]
    prev = named.index[0]
    for ts, val in named.iloc[1:].items():
        if val != cur:
            segs.append({"from": str(seg_start.date()), "to": str(prev.date()),
                         "regime": cur,
                         "n_bars": int(((named.index >= seg_start) & (named.index <= prev)).sum())})
            seg_start, cur = ts, val
        prev = ts
    prev = named.index[-1]
    segs.append({"from": str(seg_start.date()), "to": str(prev.date()),
                 "regime": cur,
                 "n_bars": int(((named.index >= seg_start) & (named.index <= prev)).sum())})
    return segs


# ------------------------------------------------------------------
# Cross-market blocks (H2 + composition + Link B), per window
# ------------------------------------------------------------------
def cross_market_block(per_market: dict[str, dict]) -> dict[str, Any]:
    names = list(per_market.keys())
    tier = np.array([TIER_RANK[m] for m in names], dtype=float)
    rps = np.array([RPS[m] for m in names], dtype=float)

    block: dict[str, Any] = {"markets": names}

    # --- H2: ρ(H, tier) etc. from canonical compute_kw_h_and_eta numbers ---
    for lab in ["raw", "filtered"]:
        H = np.array([per_market[m][f"kw_{lab}"]["H_stat"] for m in names])
        eta = np.array([per_market[m][f"kw_{lab}"]["eta_sq"] for m in names])
        rho_ht, p_ht = spearmanr(H, tier)
        rho_et, p_et = spearmanr(eta, tier)
        rho_hr, p_hr = spearmanr(H, rps)
        rho_er, p_er = spearmanr(eta, rps)
        _, p_ht_perm, _, _ = lbt.permutation_spearman_ci(H, tier)
        block[f"h2_{lab}"] = {
            "rho_H_tier": float(rho_ht), "p_H_tier": float(p_ht),
            "p_H_tier_perm": float(p_ht_perm),
            "rho_eta_tier": float(rho_et), "p_eta_tier": float(p_et),
            "rho_H_rps": float(rho_hr), "p_H_rps": float(p_hr),
            "rho_eta_rps": float(rho_er), "p_eta_rps": float(p_er),
        }

    # --- Composition vs RPS (manuscript B.5.3 headline) ---
    for lab, key in [("filt", "shares_filtered"), ("raw", "shares_raw")]:
        for regime, short in [("Stochastic", "sto"), ("Transitional", "tra"),
                              ("Deterministic", "det")]:
            x = np.array([per_market[m][key][regime] for m in names])
            rho, p_perm, ci_lo, ci_hi = lbt.permutation_spearman_ci(x, rps)
            block[f"rho_p_{short}_{lab}_rps"] = {
                "rho": rho, "p_perm_2sided": p_perm,
                "ci_lo_fisher": ci_lo, "ci_hi_fisher": ci_hi,
            }

    # --- Link B B.3.1: entropy LEVEL vs RPS ---
    for feat in ["mean_WPE", "mean_SPE_Z", "median_WPE", "median_SPE_Z"]:
        x = np.array([per_market[m]["link_b"][feat] for m in names])
        rho, p_perm, ci_lo, ci_hi = lbt.permutation_spearman_ci(x, rps)
        block[f"B31_{feat}"] = {"rho": rho, "p_perm_2sided": p_perm}

    # --- Link B raw SampEn (tail level / dispersion) vs RPS ---
    for feat in ["mean_raw_SampEn", "std_raw_SampEn", "p95_raw_SampEn",
                 "iqr_raw_SampEn"]:
        x = np.array([per_market[m]["raw_sampen"][feat] for m in names])
        rho, p_perm, ci_lo, ci_hi = lbt.permutation_spearman_ci(x, rps)
        block[f"sampen_{feat}"] = {"rho": rho, "p_perm_2sided": p_perm}

    return block


# ------------------------------------------------------------------
# One full window run
# ------------------------------------------------------------------
def run_window(window_name: str, end: str, markets: list[dict],
               skip_dml: bool) -> dict[str, Any]:
    print("\n" + "=" * 74)
    print(f"  WINDOW [{window_name}]  {START} → {end}   (n={len(markets)} markets)")
    print("=" * 74)

    cmv2.END = end
    h1c = None
    if not skip_dml:
        h1c = _load_dml_module()
        h1c.END = end

    per_market: dict[str, dict] = {}
    cm_results: list[dict] = []

    for cfg in markets:
        name = cfg["name"]
        print(f"\n--- [{window_name}] {name} ---")
        res = cmv2.analyze_market(cfg)
        if res is None:
            print(f"  [WARN] {name} skipped by analyze_market")
            continue
        cm_results.append(res)

        out = cached_pipeline(market=name, ticker=cfg["ticker"],
                              source=cfg["source"], start=START, end=end)

        entry: dict[str, Any] = {
            "n_bars": int(len(out["features"])),
            "bars_from": str(out["features"].index[0].date()),
            "bars_to": str(out["features"].index[-1].date()),
            "kw_raw": h2e.compute_kw_h_and_eta(out["ohlcv"], out["raw_labels"]),
            "kw_filtered": h2e.compute_kw_h_and_eta(out["ohlcv"], out["filtered_labels"]),
            "shares_raw": regime_shares(out["raw_labels"]),
            "shares_filtered": regime_shares(out["filtered_labels"]),
            "flip_rate_raw": flip_rate_per_year(out["raw_labels"]),
            "flip_rate_filtered": flip_rate_per_year(out["filtered_labels"]),
            "link_b": lbt.per_market_entropy_stats(out),
            "raw_sampen": raw_sampen_stats(out["ohlcv"]),
            # headline slices of the canonical cross_market_v2 result
            "cm": {k: res[k] for k in [
                "H_stat", "p_value", "direction", "kw_epsilon_sq",
                "primary_p_mw_1sided", "primary_cliffs_delta",
                "primary_delta_ci_lo", "primary_delta_ci_hi",
                "direction_verdict_formal", "direction_across_horizons",
                "H_stat_filtered", "direction_filtered",
                "primary_cliffs_delta_filtered",
                "primary_delta_ci_lo_filtered", "primary_delta_ci_hi_filtered",
                "primary_p_mw_1sided_filtered",
                "direction_verdict_formal_filtered",
            ]},
        }

        if not skip_dml:
            dml_cfg = {k: cfg[k] for k in ("name", "ticker", "source")}
            dml = h1c.analyze_market(dml_cfg)
            entry["dml"] = dml

        per_market[name] = entry

    summary_df = cmv2.build_summary_csv(cm_results) if cm_results else pd.DataFrame()
    if len(summary_df):
        path = os.path.join(OOS_DIR, f"cross_market_summary_{window_name}.csv")
        summary_df.to_csv(path, index=False)
        print(f"  window summary CSV: {path}")

    block = cross_market_block(per_market) if per_market else {}
    return {"window": window_name, "start": START, "end": end,
            "per_market": per_market, "cross_market": block}


# ------------------------------------------------------------------
# Stability diagnostics between repro and extended windows
# ------------------------------------------------------------------
def stability_diagnostics(markets: list[dict]) -> dict[str, Any]:
    diag: dict[str, Any] = {}
    for cfg in markets:
        name = cfg["name"]
        key_r = (name, cfg["ticker"], cfg["source"], START, REPRO_END)
        key_e = (name, cfg["ticker"], cfg["source"], START, OOS_END)
        if key_r not in _PIPE_CACHE or key_e not in _PIPE_CACHE:
            continue
        out_r, out_e = _PIPE_CACHE[key_r], _PIPE_CACHE[key_e]
        d: dict[str, Any] = {}
        for lab in ["raw_labels", "filtered_labels"]:
            a, b = out_r[lab], out_e[lab]
            common = a.index.intersection(b.index)
            same = (a.loc[common].astype(int).values ==
                    b.loc[common].astype(int).values)
            d[f"agreement_{lab}"] = float(same.mean())
            d[f"n_common_bars"] = int(len(common))
            d[f"n_disagree_{lab}"] = int((~same).sum())
            if (~same).any():
                d[f"first_disagree_{lab}"] = str(common[np.argmax(~same)].date())
        # OOS slice: what did the extended model label after the cutoff?
        filt_e = out_e["filtered_labels"]
        oos_slice = filt_e[filt_e.index > OOS_CUTOFF]
        d["oos_n_bars"] = int(len(oos_slice))
        d["oos_segments_filtered"] = label_segments(oos_slice)
        d["oos_n_flips_filtered"] = int(len(flip_dates(oos_slice)))
        raw_e = out_e["raw_labels"]
        d["oos_n_flips_raw"] = int(len(flip_dates(raw_e[raw_e.index > OOS_CUTOFF])))
        diag[name] = d
    return diag


# ------------------------------------------------------------------
# Frozen baselines (read-only)
# ------------------------------------------------------------------
def load_frozen() -> dict[str, Any]:
    frozen: dict[str, Any] = {}
    p = os.path.join(RESULTS_V2, "h2_magnitude/cross_market_summary_v2.csv")
    if os.path.exists(p):
        frozen["summary"] = pd.read_csv(p).set_index("market").to_dict("index")
    for key, fname in [("h1_dml_cpcv", "h1_direction/h1_dml_cpcv.json"),
                       ("h2_eta_squared", "h2_magnitude/h2_eta_squared.json"),
                       ("link_b_tests", "mechanism_battery/link_b_tests.json")]:
        fp = os.path.join(RESULTS_V2, fname)
        if os.path.exists(fp):
            with open(fp, encoding="utf-8") as f:
                frozen[key] = json.load(f)
    fp = os.path.join(RESULTS_V2, "n27_experiment", "link_b_raw_sampen_test.json")
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            frozen["raw_sampen"] = json.load(f)
    return frozen


# ------------------------------------------------------------------
# Headline comparison table: frozen vs repro vs extended
# ------------------------------------------------------------------
def headline_comparison(frozen: dict, windows: dict[str, dict]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(metric: str, fro, rep, ext, note: str = ""):
        rows.append({"metric": metric, "frozen_2026-04-17": fro,
                     "repro_2026-04-17": rep, "extended_2026-06-30": ext,
                     "note": note})

    rep = windows.get("repro", {})
    ext = windows.get("extended", {})

    def cm_get(win: dict, market: str, field: str):
        try:
            return win["per_market"][market]["cm"][field]
        except (KeyError, TypeError):
            return None

    def dml_get(win: dict, market: str, model: str, field: str):
        try:
            return win["per_market"][market]["dml"][model][field]
        except (KeyError, TypeError):
            return None

    fro_sum = frozen.get("summary", {})
    fro_dml = frozen.get("h1_dml_cpcv", {}).get("results", {})

    markets = list((ext or rep).get("per_market", {}).keys())

    # --- H1 per market ---
    for m in markets:
        fs = fro_sum.get(m, {})
        add(f"H1 {m} verdict formal (raw)", fs.get("direction_verdict_formal"),
            cm_get(rep, m, "direction_verdict_formal"),
            cm_get(ext, m, "direction_verdict_formal"))
        add(f"H1 {m} Cliff's δ (raw, 20d)", fs.get("cliffs_delta"),
            cm_get(rep, m, "primary_cliffs_delta"),
            cm_get(ext, m, "primary_cliffs_delta"))
        fd = fro_dml.get(m, {}).get("causal_forest_dml", {})
        add(f"H1 {m} CF-DML ATE", fd.get("ate"),
            dml_get(rep, m, "causal_forest_dml", "ate"),
            dml_get(ext, m, "causal_forest_dml", "ate"))
        add(f"H1 {m} CF-DML verdict", fd.get("direction_verdict"),
            dml_get(rep, m, "causal_forest_dml", "direction_verdict"),
            dml_get(ext, m, "causal_forest_dml", "direction_verdict"))

    # --- H2 cross-market ---
    fro_h2 = frozen.get("h2_eta_squared", {}).get("cross_market", {})
    for lab in ["raw", "filtered"]:
        fh = fro_h2.get(lab, {})
        def x_get(win, field):
            try:
                return win["cross_market"][f"h2_{lab}"][field]
            except (KeyError, TypeError):
                return None
        add(f"H2 ρ(H,tier) {lab}", fh.get("rho_H_tier"),
            x_get(rep, "rho_H_tier"), x_get(ext, "rho_H_tier"))
        add(f"H2 p(H,tier) {lab}", fh.get("p_H_tier"),
            x_get(rep, "p_H_tier"), x_get(ext, "p_H_tier"))
        add(f"H2 ρ(η²,tier) {lab}", fh.get("rho_eta_tier"),
            x_get(rep, "rho_eta_tier"), x_get(ext, "rho_eta_tier"))
        add(f"H2 ρ(H,RPS) {lab}", fh.get("rho_H_rps"),
            x_get(rep, "rho_H_rps"), x_get(ext, "rho_H_rps"))

    # --- Composition headline (B.5.3): ρ(p_sto_filt, RPS) ---
    def comp_get(win, key):
        try:
            return win["cross_market"][key]["rho"]
        except (KeyError, TypeError):
            return None
    def comp_p(win, key):
        try:
            return win["cross_market"][key]["p_perm_2sided"]
        except (KeyError, TypeError):
            return None
    # frozen value from summary CSV shares (3dp, the manuscript convention)
    if fro_sum:
        ms = [m for m in markets if m in fro_sum]
        psto = np.array([fro_sum[m]["p_sto_filtered"] for m in ms])
        ptra = np.array([fro_sum[m]["p_tra_filtered"] for m in ms])
        rpsv = np.array([RPS[m] for m in ms])
        fro_psto = float(spearmanr(psto, rpsv)[0])
        fro_ptra = float(spearmanr(ptra, rpsv)[0])
    else:
        fro_psto = fro_ptra = None
    add("Mech ρ(p_sto_filt, RPS)", fro_psto,
        comp_get(rep, "rho_p_sto_filt_rps"), comp_get(ext, "rho_p_sto_filt_rps"),
        note="frozen from summary CSV 3dp shares (ms: -0.850)")
    add("Mech p_perm(p_sto_filt, RPS)", None,
        comp_p(rep, "rho_p_sto_filt_rps"), comp_p(ext, "rho_p_sto_filt_rps"),
        note="ms: 0.012")
    add("H3-adjacent ρ(p_tra_filt, RPS)", fro_ptra,
        comp_get(rep, "rho_p_tra_filt_rps"), comp_get(ext, "rho_p_tra_filt_rps"))

    # --- Link B B.3.1 + raw SampEn ---
    fro_lb = frozen.get("link_b_tests", {}).get("tests", {})
    for feat in ["mean_WPE", "mean_SPE_Z"]:
        def b_get(win):
            try:
                return win["cross_market"][f"B31_{feat}"]["rho"]
            except (KeyError, TypeError):
                return None
        add(f"LinkB ρ({feat}, RPS)",
            fro_lb.get(f"B.3.1_{feat}", {}).get("rho"), b_get(rep), b_get(ext))
    fro_rs = (frozen.get("raw_sampen", {}).get("panels", {})
              .get("n8", {}).get("tests", {}))
    for feat in ["p95_raw_SampEn", "std_raw_SampEn"]:
        def s_get(win, fld="rho"):
            try:
                return win["cross_market"][f"sampen_{feat}"][fld]
            except (KeyError, TypeError):
                return None
        add(f"LinkB ρ({feat}, RPS)",
            fro_rs.get(feat, {}).get("rho"), s_get(rep), s_get(ext))
        add(f"LinkB p({feat}, RPS)",
            fro_rs.get(feat, {}).get("p_perm_2sided"),
            s_get(rep, "p_perm_2sided"), s_get(ext, "p_perm_2sided"))

    # --- Composition / flip-rate per market ---
    for m in markets:
        fs = fro_sum.get(m, {})
        def sh_get(win, key):
            try:
                return round(win["per_market"][m][key]["Stochastic"], 3)
            except (KeyError, TypeError):
                return None
        add(f"p_sto_filt {m}", fs.get("p_sto_filtered"),
            sh_get(rep, "shares_filtered"), sh_get(ext, "shares_filtered"))

    return pd.DataFrame(rows)


# ------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-dml", action="store_true")
    ap.add_argument("--markets", type=str, default="")
    ap.add_argument("--windows", type=str, default="repro,extended")
    args = ap.parse_args()

    markets = PANEL
    if args.markets:
        wanted = {m.strip().upper() for m in args.markets.split(",")}
        markets = [m for m in PANEL if m["name"].upper() in wanted]
    win_names = [w.strip() for w in args.windows.split(",") if w.strip()]

    print("=" * 74)
    print("  OOS 2026-Q2 EXTENSION — canonical n=8 suite, END 2026-04-17 → 2026-06-30")
    print("=" * 74)
    print(f"  markets : {[m['name'] for m in markets]}")
    print(f"  windows : {win_names}   skip_dml={args.skip_dml}")
    print(f"  outputs : {OOS_DIR}")

    t0 = time.time()
    windows: dict[str, dict] = {}
    if "repro" in win_names:
        windows["repro"] = run_window("repro", REPRO_END, markets, args.skip_dml)
    if "extended" in win_names:
        windows["extended"] = run_window("extended", OOS_END, markets, args.skip_dml)

    diag = stability_diagnostics(markets) if len(windows) == 2 else {}
    frozen = load_frozen()
    comp_df = headline_comparison(frozen, windows)

    payload = {
        "spec": ("OOS extension of the canonical n=8 suite: END 2026-04-17 → "
                 "2026-06-30. Canonical machinery reused verbatim via module "
                 "monkeypatch; frozen archive untouched."),
        "start": START, "repro_end": REPRO_END, "oos_end": OOS_END,
        "skip_dml": bool(args.skip_dml),
        "elapsed_seconds": float(time.time() - t0),
        "windows": windows,
        "stability_diagnostics": diag,
    }
    out_json = os.path.join(OOS_DIR, "oos_2026q2_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float)

    comp_path = os.path.join(OOS_DIR, "oos_2026q2_headline_comparison.csv")
    comp_df.to_csv(comp_path, index=False)

    # stray file written by canonical build_summary_csv inside OOS_DIR
    stray = os.path.join(OOS_DIR, "h2_magnitude/cross_market_summary_v2.csv")
    if os.path.exists(stray):
        os.remove(stray)

    print("\n" + "=" * 74)
    print("  HEADLINE COMPARISON (frozen | repro | extended)")
    print("=" * 74)
    with pd.option_context("display.max_rows", None, "display.width", 200,
                           "display.max_colwidth", 40):
        print(comp_df.to_string(index=False))

    if diag:
        print("\n" + "=" * 74)
        print("  OOS WINDOW (2026-04-18 → 2026-06-30) — filtered-regime narrative")
        print("=" * 74)
        for m, d in diag.items():
            segs = "; ".join(f"{s['from']}→{s['to']} {s['regime']}({s['n_bars']})"
                             for s in d["oos_segments_filtered"])
            print(f"  {m:<8} agree_filt={d['agreement_filtered_labels']:.4f} "
                  f"oos_flips={d['oos_n_flips_filtered']}  {segs}")

    print(f"\n  JSON: {out_json}")
    print(f"  comparison CSV: {comp_path}")
    print(f"  total elapsed: {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
