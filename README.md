# Entropy Paradox Research

**Code, validation scripts, and frozen outputs supporting a journal-submission
paper on entropy-derived market-regime informativeness across a heterogeneous
cross-market panel.**

This repository is the public reproducibility archive referenced on the
manuscript's title page. The manuscript is under double-anonymized review, so
its exact title and author block are withheld from this README until
acceptance; everything needed to audit the pipeline and reproduce every
reported number is here.

A companion production system (live dashboard + agent layer) exists in a
separate repository; its reference is withheld during double-anonymized
review and will be restored upon acceptance. This repo is research-only.

**Canonical reproducibility tag for the submitted manuscript:
`v3.4-jfds-submission`.** Reported numbers reproduce byte-for-byte against the
frozen outputs at this tag via regression assertions (`atol = 1e-4`) inside
the validation scripts.

## The pipeline

The paper's analysis is a five-layer pipeline. Every layer is independently
runnable and every layer's constants are pinned (see
[Research invariants](#research-invariants)).

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 1. DATA INGESTION                                                          │
│    Daily OHLCV pulled from 2018-01-01 → 2026-04-17                         │
│    vnstock (VNINDEX) · yfinance (international indices, BTC-USD)           │
├────────────────────────────────────────────────────────────────────────────┤
│ 2. ENTROPY FEATURE ENGINEERING            skills/quant_skill.py            │
│    WPE  — weighted permutation entropy (m=3, τ=1, window=22)               │
│    SPE_Z — price sample entropy (m=2, r=0.2σ, window=60), standardized     │
│            by a strictly BACKWARD rolling 504-day Z-score (no look-ahead). │
│    The 504-day window consumes 2018–2019 as burn-in → labeled bars begin   │
│    late Mar–Apr 2020 (BTC: Jul 2019); labeled analysis window is           │
│    2020-01-01 → 2026-04-17 (post-COVID by construction).                   │
├────────────────────────────────────────────────────────────────────────────┤
│ 3. REGIME CLASSIFICATION                  skills/ds_skill.py               │
│    GMM on raw [WPE, SPE_Z] (K=3, full covariance, n_init=10, seed 42)      │
│    → three regimes: Deterministic / Transitional / Stochastic              │
│    + Schmitt-trigger hysteresis post-filter on posterior probabilities     │
│      (δ_hard=0.60, δ_soft=0.35, t_persist=8) → filtered labels             │
├────────────────────────────────────────────────────────────────────────────┤
│ 4. FORWARD-VOLATILITY TARGET                                               │
│    Forward 20-day annualized realized volatility per bar                   │
├────────────────────────────────────────────────────────────────────────────┤
│ 5. HYPOTHESIS TESTS                       validation/*.py                  │
│    H1 direction  — causal forest DML + Purged K-Fold (K=5, 20-bar embargo) │
│    H2 magnitude  — Kruskal–Wallis H × MSCI tier (primary)                  │
│                    + cascade Retail-Participation-Share (secondary)        │
│    H3 geometry   — Transitional-band width vs cluster separation           │
│    H4 structure  — block-permutation temporal-structure prerequisite       │
│    H5 robustness — hysteresis parameter transfer + per-market re-calib     │
│    + n=27 panel expansion, Chronos foundation-model head-to-head           │
└────────────────────────────────────────────────────────────────────────────┘
```

Feature recipe pinning: [validation/_features.py](validation/_features.py) is
the single entry point every test imports (`run_full_pipeline()`); no script
rebuilds features ad hoc, which keeps all tests cross-comparable.

## Headline findings (as submitted)

1. **Direction heterogeneity (H1).** The Deterministic–Stochastic
   regime-volatility direction is not universal — it tracks microstructure.
   Under the leakage-proof canonical spec (causal forest DML + Purged K-Fold +
   filtered labels), SPX reads decisive *Paradox* (low-entropy regime precedes
   HIGHER forward vol) and BTC decisive *Inverted*; the remaining markets
   carry directional signs at the n = 8 power floor. At n = 27, BVB Romania
   lifts to decisive Paradox and SHANGHAI emerges decisive Paradox. Apparent
   Paradox readings on developed markets under naive K-Fold are shown to be
   future-data leakage.
2. **Cross-market magnitude scaling (H2).** Regime informativeness
   (Kruskal–Wallis H on the regime labels) scales monotonically with MSCI
   tier — ρ = 0.927 (p = 0.0009) at n = 8, replicated at n = 27 — with retail
   participation share as a cascade-supported secondary ordering. A
   convergent mechanism battery (stochastic-regime share, raw-SampEn tail and
   dispersion × RPS) supports a behavioral-coordination reading: high-retail
   markets show lower entropy and lower entropy-tail dispersion.
3. **Cluster geometry (H3, reformulated).** Transitional-band width scales
   inversely with regime informativeness at the tier-mean level; monotone
   across the three MSCI tiers at n = 27.

## Reproducing the paper's numbers

No build step. Python 3.13 with numpy / scipy / pandas / scikit-learn /
econml / ruptures. All seeds pinned (42). Outputs land in
[validation/results_v2/](validation/results_v2/) as JSON / CSV / PNG; scripts
assert byte-for-byte agreement with the frozen copies at `atol = 1e-4`.

```bash
# Canonical pre-registered suite
python validation/cross_market_v2.py             # H1 direction (Cliff's δ track) + H2 base
python validation/h2_rps_validation.py           # H2 RPS panel
python validation/hysteresis_cross_market_v2.py  # H3 + H4
python validation/hysteresis_robustness_v2.py    # H5

# Canonical H1 DML specification (manuscript Table 2)
python validation/h1_dml_cpcv.py

# H2 tier-based primary + effect size + cascade (manuscript §4.2, Tables 3/E.1)
python validation/h2_tier_based.py
python validation/h2_eta_squared.py
python validation/h2_cascade.py

# Appendix / robustness
python validation/h2_decomposition_sensitivity.py   # variance decomposition (Table 4)
python validation/phase2_revision_addenda.py        # RPS scenario grids (Table E.3)
python validation/gmm_k_sensitivity.py              # K-grid (Table C.2)
python validation/structural_breaks.py              # PELT breakpoints (Table C.3)
python validation/link_b_tests.py                   # mechanism battery (App B.5)
python validation/h6_chronos_8market.py             # Chronos head-to-head (App H)

# n = 27 expansion (App I)
python validation/h1_dml_cpcv_n27.py
python validation/h2_cascade_n27.py
python validation/h2_eta_squared_n27.py
```

### Manuscript table → script → frozen output

| Manuscript object | Script | Frozen output (`validation/results_v2/`) |
|---|---|---|
| Table 1 / E.1 (panel, H, η², N_obs) | `h2_eta_squared.py` | `cross_market_summary_v2.csv`, `h2_eta_squared.json` |
| Table 2 / F.2–F.3 (DML ATE per market) | `h1_dml_cpcv.py` | `h1_dml_cpcv.json` |
| §4.2.1 tier correlation (ρ = 0.927) | `h2_tier_based.py` | `h2_tier_based.json` |
| Table 3 / G.1 (cascade composite MC) | `h2_cascade.py` | `h2_cascade.json` |
| Table 4 / G.2 (variance decomposition) | `h2_decomposition_sensitivity.py` | `h2_decomposition_sensitivity.json` |
| Table E.2 (crypto rank grid) | `h2_tier_rank_sensitivity.py` | `h2_tier_rank_sensitivity.json` |
| Table E.3 (RPS noise scenarios C/D) | `phase2_revision_addenda.py` | `phase2_revision_addenda.json` |
| Tables E.4 / E.5 (subpanels, leave-one-out) | derivations from Table E.1 | `h2_eta_squared.json` inputs |
| Tables 6 / E.7 / E.8 (H5 verdicts) | `hysteresis_robustness_v2.py`, `h5_per_market_grid_search.py` | `h5_refined.csv`, `h5_per_market_grid_search.{csv,json}` |
| Table B.1 (SPE_Z standardization) | `h2_sensitivity_spe_z.py` | `h2_sensitivity_spe_z.json` |
| Table C.1 (flip rates, compositions) | `hysteresis_cross_market_v2.py` | `hysteresis_summary_v2.csv`, `*_hysteresis.json` |
| Table C.2 (GMM K-grid) | `gmm_k_sensitivity.py` | `gmm_k_sensitivity.json` |
| Table C.3 (structural breakpoints) | `structural_breaks.py` | `structural_breaks.json` |
| Figure C.1 (phase space) | `regime_phase_space_compare.py` | `regime_phase_space_vnindex_raw_vs_filtered.png` |
| App B.5 mechanism battery | `link_b_tests.py` + n27 variants | `link_b_tests.json`, `n27_experiment/link_b_*.json` |
| Tables H.1 / H.3 (Chronos) | `h6_chronos_8market.py` | `h6_chronos_8market.json` |
| App I (n = 27) | `h1_dml_cpcv_n27.py`, `h2_cascade_n27.py`, `h2_eta_squared_n27.py` | `n27_experiment/*.json` |

The manuscript text itself is deliberately not tracked here (it is under
double-anonymized review); this repository carries the code and the frozen
outputs that back every reported number.

## Plane-1 phase space — raw GMM vs hysteresis-filtered

![VNINDEX Plane-1 phase space, raw GMM vs hysteresis-filtered](validation/results_v2/regime_phase_space_vnindex_raw_vs_filtered.png)

Both panels show the **same** GMM (k = 3, full-covariance,
random_state = 42) fit on `[WPE, SPE_Z]` for VNINDEX over the
2018–2026 loading window. The dashed ellipses are the 2-σ confidence
regions of the three GMM clusters and are identical between panels —
only the **per-bar labelling rule** differs:

- **Left (Raw GMM)** — argmax of the GMM posterior at each bar,
  independent of temporal context. **91 flips total · 15.23 / year**.
- **Right (Hysteresis-Filtered)** — Schmitt-trigger state machine over
  the same posteriors (δ_hard = 0.60, δ_soft = 0.35, t_persist = 8).
  **39 flips total · 6.53 / year (57 % reduction vs raw)**.

Display window 2020-01-01 → 2026-04-17 (post-COVID), n = 1506 bars.
Labels differ on 156 bars (10.4 %) — these are the bars where
hysteresis "holds" the previously-held regime against an
instantaneous argmax flip. Reproduced by
[`regime_phase_space_compare.py`](validation/regime_phase_space_compare.py).

## Pre-registration

Hypotheses H1–H5 are frozen at commit `b130b0f` (2026-04-18):
[pre_registration/hypotheses_v2_combined.md](pre_registration/hypotheses_v2_combined.md).
Scientific-foundation audit:
[pre_registration/critique.md](pre_registration/critique.md).
Frozen first-run outputs are archived under
[validation/results_v2/prereg_b130b0f/](validation/results_v2/prereg_b130b0f/)
(this archive reflects the original pre-registration panel; the submitted
manuscript documents the subsequent panel correction — the second frontier
slot realized as BVB Romania — and all post-pre-registration analyses are
additive, never altering a pre-registered result).

## Repository structure

```
pre_registration/        Frozen H1-H5 pre-registration + scientific-foundation audit
validation/              Pre-registered H1-H5 scripts + journal-submission extensions
                         + appendix robustness redos
validation/results_v2/   JSON / CSV / PNG frozen outputs + prereg_b130b0f/ archive
skills/                  Core computation modules (quant_skill, ds_skill, data_skill)
scripts/                 Calibration + feature-extraction helpers
docs/                    Architectural diagram images
CONTEXT.md               Project state-of-play anchor
architecture.md          Detailed system architecture
```

Cover letters, title pages, lab notebooks, and audit logs stay in a private
workspace and are not tracked here.

## Research invariants

These constants are pinned across the canonical pipeline; sweeping
any of them requires a new branch and a new tag.

| Component | Value |
|-----------|-------|
| Weighted Permutation Entropy (WPE) | m = 3, τ = 1, rolling window = 22 |
| Price Sample Entropy (SampEn) | m = 2, r = 0.2σ, rolling window = 60 |
| Standardised SampEn (SPE_Z) | strictly backward rolling Z-score, window = 504 (never global) |
| Plane-1 features | `[WPE, SPE_Z]`, raw scale, no transformer |
| Gaussian Mixture Model | k = 3 (fixed a priori), full covariance, n_init = 10, max_iter = 500, random_state = 42 |
| Hysteresis filter (production default) | δ_hard = 0.60, δ_soft = 0.35, t_persist = 8 |
| DML cross-fitting | Purged K-Fold, K = 5, 20-bar embargo; nuisance forests 200×6; final forest 300×6 |

Hysteresis was calibrated on VNINDEX post-2020 to a 4–10 flips / yr
target band (achieves 6.53 / yr on the labeled window); calibration source:
[scripts/calibrate_hysteresis.py](scripts/calibrate_hysteresis.py).

## Authors

Anonymized for double-anonymized peer review. The full author block,
contact details, and contribution statement appear on the manuscript title
page and will be restored here upon acceptance.

## License

MIT License for code. Please cite the paper if using the methodology.
