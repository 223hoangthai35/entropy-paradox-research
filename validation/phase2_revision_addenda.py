"""Phase 2 revision addenda — supplementary computations for JFDS-KeAi submission.

Computes:
  (1) LOO sensitivity for H2 Spearman rho(H, RPS) — drop-each-market (raw + filtered)
  (2) MC measurement-noise sensitivity for H2 with sd in {0.05, 0.10, 0.15}
  (3) Feature-comparison Spearman: rho(H_Entropy, RPS), rho(H_SimpleVol, RPS),
      rho(H_Combined, RPS) on the entropy_vs_simple restricted-window panel.
  (4) Power analysis: minimum detectable Spearman rho at n=8, alpha=0.05, power=0.8.

Reads:
  - results_v2/cross_market_summary_v2.csv           (main H values)
  - results_v2/entropy_vs_simple_8market.json        (3-feature comparison values)

Writes:
  - results_v2/phase2_revision_addenda.json          (consolidated outputs)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results_v2"

# Pre-registered RPS panel (ex-ante; see rps_rationale.md)
RPS_OLD = {
    "VNINDEX": 0.90,
    "PSEI": 0.68,
    "KOSPI": 0.70,
    "NIFTY": 0.40,
    "SPX": 0.22,
    "FTSE": 0.18,
    "NIKKEI": 0.18,
    "BTC": 0.55,
}

# Window-averaged RPS panel (2020-04-17 → 2026-04-17, trading-value share)
# Sources documented in plan v5 §D.4.5; reasoning per market based on:
#   VNINDEX: SSC reports + VinaCapital (consistently retail-dominant 80-92%)
#   PSEI:    PSE Stock Market Investor Profile (2021=29.9%, 2023=16.5%, 3-yr avg 21%)
#   KOSPI:   KRX Data Marketplace (2021 COVID peak 0.70 → March 2026 0.45; window-avg ~0.45)
#   NIFTY:   NSE India FY data (FY21=0.45 → FY24/25=0.336)
#   SPX:     MEMX retail-order-flow share (30-37% 2024) — NOT SIFMA ownership
#   FTSE:    Limited public data; pre-reg 0.18 retained as best-available
#   NIKKEI:  JPX Trading-by-Investor-Type (~0.18-0.22 throughout window)
#   BTC:     Pre-ETF retail-dominant 85-90%, post-ETF 65-75%; window-avg ~0.75
RPS_CORRECTED = {
    "VNINDEX": 0.85,
    "PSEI": 0.22,
    "KOSPI": 0.45,
    "NIFTY": 0.39,
    "SPX": 0.30,
    "FTSE": 0.18,
    "NIKKEI": 0.20,
    "BTC": 0.75,
}

# Default panel for backward compatibility
RPS = RPS_CORRECTED
MARKETS = list(RPS.keys())  # ordered

# Reproducibility seeds
SEED_BOOTSTRAP = 42
SEED_MC_05 = 43
SEED_MC_10 = 44
SEED_MC_15 = 45
N_BOOT = 10_000
N_MC = 10_000


def load_main_h_values() -> tuple[dict[str, float], dict[str, float]]:
    """Load primary H values from cross_market_summary_v2.csv (raw + filtered)."""
    df = pd.read_csv(RESULTS_DIR / "cross_market_summary_v2.csv")
    df = df.set_index("market")
    h_raw = {m: float(df.loc[m, "H_stat"]) for m in MARKETS}
    h_filt = {m: float(df.loc[m, "H_stat_filtered"]) for m in MARKETS}
    return h_raw, h_filt


def load_feature_comparison_h() -> dict[str, dict[str, dict[str, float]]]:
    """Load H values from entropy_vs_simple_8market.json.

    Returns nested dict: model -> source -> market -> H.
    """
    with open(RESULTS_DIR / "entropy_vs_simple_8market.json", encoding="utf-8") as fh:
        data = json.load(fh)
    out = {m: {"raw": {}, "filtered": {}} for m in ["Entropy", "SimpleVol", "Combined"]}
    for market_block in data["markets"]:
        m = market_block["market"]
        for row in market_block["rows"]:
            model = row["model"]
            src = row["label_source"]
            out[model][src][m] = float(row["kw_h"])
    return out


def spearman(h_dict: dict[str, float], panel: dict[str, float] = None) -> tuple[float, float]:
    """Spearman rho + p-value for the 8-market panel."""
    if panel is None:
        panel = RPS
    h = np.array([h_dict[m] for m in MARKETS])
    rps = np.array([panel[m] for m in MARKETS])
    res = stats.spearmanr(h, rps)
    return float(res.statistic), float(res.pvalue)


def loo_sensitivity(h_dict: dict[str, float], panel: dict[str, float] = None) -> list[dict]:
    """Drop-each-market Spearman rho for 8 markets."""
    if panel is None:
        panel = RPS
    rows = []
    for held_out in MARKETS:
        keep = [m for m in MARKETS if m != held_out]
        h = np.array([h_dict[m] for m in keep])
        rps = np.array([panel[m] for m in keep])
        res = stats.spearmanr(h, rps)
        rows.append({
            "dropped_market": held_out,
            "n": len(keep),
            "rho": float(res.statistic),
            "p_value": float(res.pvalue),
        })
    return rows


def mc_noise_sensitivity(h_dict: dict[str, float], noise_sd: float, seed: int,
                         threshold: float = 0.5, panel: dict[str, float] = None) -> dict:
    """MC sensitivity: perturb RPS by N(0, noise_sd), clamp to [0,1], recompute rho."""
    if panel is None:
        panel = RPS
    rng = np.random.default_rng(seed)
    h = np.array([h_dict[m] for m in MARKETS])
    rps_base = np.array([panel[m] for m in MARKETS])
    rhos = np.empty(N_MC)
    for i in range(N_MC):
        perturbed = np.clip(rps_base + rng.normal(0, noise_sd, size=len(rps_base)), 0.0, 1.0)
        res = stats.spearmanr(h, perturbed)
        rhos[i] = res.statistic
    return {
        "noise_sd": noise_sd,
        "n_trials": int(N_MC),
        "rho_mean": float(np.mean(rhos)),
        "rho_std": float(np.std(rhos, ddof=1)),
        "rho_p05": float(np.percentile(rhos, 5)),
        "rho_p50": float(np.percentile(rhos, 50)),
        "rho_p95": float(np.percentile(rhos, 95)),
        "rho_min": float(np.min(rhos)),
        "rho_max": float(np.max(rhos)),
        f"frac_rho_gt_{threshold:.2f}": float(np.mean(rhos > threshold)),
    }


def power_analysis_n8(alpha: float = 0.05, power: float = 0.8) -> dict:
    """Approximate minimum detectable Spearman rho at n=8.

    Use the Fisher z-transform approximation. Spearman rho's null distribution
    at n=8 is well-approximated by t with n-2=6 df under H0 via
    t = rho * sqrt((n-2) / (1 - rho^2)).
    """
    n = 8
    df = n - 2
    t_crit_two_sided = stats.t.ppf(1 - alpha / 2, df)
    # solve rho * sqrt(df / (1-rho^2)) = t_crit  for rho:
    # rho^2 * df = t^2 * (1 - rho^2)
    # rho^2 (df + t^2) = t^2
    # rho_min = t / sqrt(df + t^2)
    rho_min_two_sided = t_crit_two_sided / np.sqrt(df + t_crit_two_sided ** 2)
    t_crit_one_sided = stats.t.ppf(1 - alpha, df)
    rho_min_one_sided = t_crit_one_sided / np.sqrt(df + t_crit_one_sided ** 2)
    return {
        "n": n,
        "df": df,
        "alpha": alpha,
        "rho_min_alpha_two_sided_no_power_target": rho_min_two_sided,
        "rho_min_alpha_one_sided_no_power_target": rho_min_one_sided,
        "note": (
            "Approximate minimum |rho| to reject rho=0 at the given alpha "
            "via t-statistic transform; does NOT incorporate beta=0.2 power. "
            "For alpha=0.05 one-sided at n=8 the threshold is ~0.62 |rho|."
        ),
    }


def run_panel(label: str, panel: dict[str, float], h_raw: dict[str, float],
              h_filt: dict[str, float], fc: dict) -> dict:
    """Run all H2 analyses for a given RPS panel; return consolidated dict."""
    print(f"\n{'='*70}\n  PANEL: {label}\n{'='*70}")
    print("  market    RPS    H_raw   H_filt")
    for m in MARKETS:
        print(f"  {m:<8} {panel[m]:.2f}   {h_raw[m]:6.2f}  {h_filt[m]:6.2f}")

    rho_raw, p_raw = spearman(h_raw, panel)
    rho_filt, p_filt = spearman(h_filt, panel)
    print(f"\n  rho(H_raw,  RPS) = {rho_raw:+.4f}  p = {p_raw:.4f}")
    print(f"  rho(H_filt, RPS) = {rho_filt:+.4f}  p = {p_filt:.4f}")

    loo_raw = loo_sensitivity(h_raw, panel)
    loo_filt = loo_sensitivity(h_filt, panel)
    print("\n  LOO raw:")
    for row in loo_raw:
        print(f"    drop {row['dropped_market']:<8}  rho={row['rho']:+.4f}  p={row['p_value']:.4f}")
    print("  LOO filtered:")
    for row in loo_filt:
        print(f"    drop {row['dropped_market']:<8}  rho={row['rho']:+.4f}  p={row['p_value']:.4f}")

    mc_raw = {
        "0.05": mc_noise_sensitivity(h_raw, 0.05, SEED_MC_05, panel=panel),
        "0.10": mc_noise_sensitivity(h_raw, 0.10, SEED_MC_10, panel=panel),
        "0.15": mc_noise_sensitivity(h_raw, 0.15, SEED_MC_15, panel=panel),
    }
    mc_filt = {
        "0.05": mc_noise_sensitivity(h_filt, 0.05, SEED_MC_05, panel=panel),
        "0.10": mc_noise_sensitivity(h_filt, 0.10, SEED_MC_10, panel=panel),
        "0.15": mc_noise_sensitivity(h_filt, 0.15, SEED_MC_15, panel=panel),
    }
    print("  MC sensitivity raw  P(rho>0.5):", end=" ")
    for k, v in mc_raw.items():
        print(f"sd={k}->{v['frac_rho_gt_0.50']:.3f}", end="  ")
    print()
    print("  MC sensitivity filt P(rho>0.5):", end=" ")
    for k, v in mc_filt.items():
        print(f"sd={k}->{v['frac_rho_gt_0.50']:.3f}", end="  ")
    print()

    fc_results = {}
    for model in ("Entropy", "SimpleVol", "Combined"):
        for src in ("raw", "filtered"):
            rho, p = spearman(fc[model][src], panel)
            fc_results[f"{model}_{src}"] = {
                "model": model,
                "label_source": src,
                "rho": rho,
                "p_value": p,
                "n": 8,
            }
    print("  Feature comparison rho(H, RPS):")
    for k, v in fc_results.items():
        print(f"    {k:<22}  rho={v['rho']:+.4f}  p={v['p_value']:.4f}")

    return {
        "panel_label": label,
        "panel_values": panel,
        "headline_h2": {
            "rho_raw": rho_raw, "p_raw": p_raw,
            "rho_filt": rho_filt, "p_filt": p_filt,
        },
        "loo_sensitivity_raw": loo_raw,
        "loo_sensitivity_filtered": loo_filt,
        "mc_noise_sensitivity_raw": mc_raw,
        "mc_noise_sensitivity_filtered": mc_filt,
        "feature_comparison_spearman": fc_results,
    }


def main():
    print("==> Loading main H values")
    h_raw, h_filt = load_main_h_values()
    fc = load_feature_comparison_h()

    # Multiple scenario panels for sensitivity analysis
    scenarios = {
        "A_original": RPS_OLD,
        "B_full_correction": RPS_CORRECTED,
        "C_only_KOSPI_corrected": {
            **RPS_OLD,
            "KOSPI": 0.45,
        },
        "D_KOSPI_SPX_corrected": {
            **RPS_OLD,
            "KOSPI": 0.45,
            "SPX": 0.30,
        },
        "E_KOSPI_NIFTY_SPX_corrected": {
            **RPS_OLD,
            "KOSPI": 0.45,
            "NIFTY": 0.39,
            "SPX": 0.30,
        },
        "F_KOSPI_corrected_BTC_higher": {
            **RPS_OLD,
            "KOSPI": 0.45,
            "BTC": 0.75,
        },
        "G_VN_higher_KOSPI_corrected": {
            **RPS_OLD,
            "VNINDEX": 0.92,
            "KOSPI": 0.45,
        },
    }

    all_results = {}
    summary_table = []
    for label, panel in scenarios.items():
        result = run_panel(label, panel, h_raw, h_filt, fc)
        all_results[label] = result
        summary_table.append({
            "scenario": label,
            "rho_raw": result["headline_h2"]["rho_raw"],
            "p_raw": result["headline_h2"]["p_raw"],
            "rho_filt": result["headline_h2"]["rho_filt"],
            "p_filt": result["headline_h2"]["p_filt"],
            "panel": panel,
        })

    print(f"\n{'='*90}\n  MULTI-SCENARIO COMPARISON SUMMARY\n{'='*90}")
    print(f"  {'Scenario':<35}  {'rho_raw':>10}  {'p_raw':>8}  {'rho_filt':>10}  {'p_filt':>8}")
    print(f"  {'-'*35}  {'-'*10}  {'-'*8}  {'-'*10}  {'-'*8}")
    for row in summary_table:
        print(f"  {row['scenario']:<35}  {row['rho_raw']:>+10.4f}  {row['p_raw']:>8.4f}  "
              f"{row['rho_filt']:>+10.4f}  {row['p_filt']:>8.4f}")

    # Use B as default "new" results for backward compat
    old_results = all_results["A_original"]
    new_results = all_results["B_full_correction"]

    # Comparison summary
    print(f"\n{'='*70}\n  COMPARISON SUMMARY: OLD vs CORRECTED RPS PANEL\n{'='*70}")
    print(f"  rho_raw      :  OLD = {old_results['headline_h2']['rho_raw']:+.4f}"
          f"   NEW = {new_results['headline_h2']['rho_raw']:+.4f}"
          f"   delta = {new_results['headline_h2']['rho_raw'] - old_results['headline_h2']['rho_raw']:+.4f}")
    print(f"  p_raw        :  OLD = {old_results['headline_h2']['p_raw']:.4f}"
          f"   NEW = {new_results['headline_h2']['p_raw']:.4f}")
    print(f"  rho_filtered :  OLD = {old_results['headline_h2']['rho_filt']:+.4f}"
          f"   NEW = {new_results['headline_h2']['rho_filt']:+.4f}"
          f"   delta = {new_results['headline_h2']['rho_filt'] - old_results['headline_h2']['rho_filt']:+.4f}")
    print(f"  p_filtered   :  OLD = {old_results['headline_h2']['p_filt']:.4f}"
          f"   NEW = {new_results['headline_h2']['p_filt']:.4f}")

    pa = power_analysis_n8()
    output = {
        "spec": "Phase 2 revision addenda — MULTI-SCENARIO RPS panel comparison",
        "panel_n": 8,
        "scenarios": all_results,
        "summary_table": summary_table,
        "old_panel_results": old_results,
        "new_panel_results": new_results,
        "power_analysis_n8": pa,
        "seeds": {
            "bootstrap": SEED_BOOTSTRAP,
            "mc_05": SEED_MC_05,
            "mc_10": SEED_MC_10,
            "mc_15": SEED_MC_15,
        },
    }
    out_path = RESULTS_DIR / "phase2_revision_addenda.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)
    print(f"\n==> Wrote {out_path}")


if __name__ == "__main__":
    main()
