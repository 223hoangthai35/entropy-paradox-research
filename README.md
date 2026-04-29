# Entropy Paradox Research

**Academic research platform for entropy-based market regime analysis.**

## Purpose

Research artifacts, validation studies, and the canonical paper on
the Entropy Paradox — the market-microstructure-dependent relationship
between permutation entropy and forward realized volatility, evaluated
on an 8-market panel under a fixed post-COVID 2020-01-01 → 2026-04-17
window.

**Companion production software**: [financial-entropy-agent](https://github.com/223hoangthai35/financial-entropy-agent)

## Publication

### Paper v2.1 (April 2026, canonical)

*The Entropy Paradox — 8-market post-COVID evidence under refined
statistical architecture with pre-registration transparency.*

**Headline claim**: Paradox magnitude tracks Retail Participation
Share (Spearman ρ = 0.754, p = 0.031, n = 8). Pairwise direction
(Det > Sto) survives FDR correction on PSEI at the 20-day horizon.
Transitional Dominance is a microstructure gradient (continuous
ρ(p_tra, RPS) = 0.56).

Summary: [paper_artifacts/paper_v2_1_combined_summary.md](paper_artifacts/paper_v2_1_combined_summary.md).
Pre-registration audit: [pre_registration/critique.md](pre_registration/critique.md).

Earlier paper-v1 (3-market, 2015-2024) and paper-v2 draft (3-market,
2022-2026) used pre-COVID windows that do not align with v2.1's recipe
(rolling SPE_Z 504, hysteresis-filtered labels). They are no longer
maintained in HEAD — recoverable via git tags `v1.0-paper` and
`v2.0-paper` for provenance.

## Validation framework

The canonical hypotheses H1–H5 (frozen pre-registration at commit
`b130b0f`, 2026-04-18) are tested by:

- **Phase 1** — H1 (paradox direction) and H2 (microstructure
  gradient via Retail Participation Share):
  [validation/cross_market_v2.py](validation/cross_market_v2.py),
  [validation/h2_rps_validation.py](validation/h2_rps_validation.py).
- **Phase 2** — H3 (Transitional persistence) and H4 (temporal
  structure under block-permutation):
  [validation/hysteresis_cross_market_v2.py](validation/hysteresis_cross_market_v2.py).
- **Phase 2b** — H5 (parameter robustness with pre-reg dead-zone
  rule):
  [validation/hysteresis_robustness_v2.py](validation/hysteresis_robustness_v2.py).

Paper §12 exploratory robustness appendix (paper-v1 V2/V3/V4 redos
under v2.1 recipe):
[validation/garch_vnindex_v2.py](validation/garch_vnindex_v2.py),
[validation/tail_lift_8market.py](validation/tail_lift_8market.py),
[validation/entropy_vs_simple_8market.py](validation/entropy_vs_simple_8market.py).

All outputs land in [validation/results_v2/](validation/results_v2/).
The frozen pre-registration archive is at
[validation/results_v2/prereg_b130b0f/](validation/results_v2/prereg_b130b0f/).

## Repository structure

```
paper_artifacts/        Canonical paper v2.1 summary + RPS rationale + papers overview
pre_registration/       Frozen H1-H5 pre-registration and scientific-foundation audit
validation/             H1-H5 validation scripts (cross_market_v2, hysteresis_*) and §12 appendix scripts
validation/results_v2/  All canonical outputs + prereg_b130b0f/ archive
skills/                 Core computation modules (quant, ds, data)
scripts/                Calibration and feature-extraction helpers
docs/                   README images
CONTEXT.md              Project state anchor for research sessions
architecture.md         Detailed system architecture
```

## Reproducibility

All paper results reproducible via tagged commits. All code public
for verification.

Tags:
- `v2.1.3-prereg-audit` — current HEAD (canonical paper + pre-registration audit)
- `v2.1-paper-combined` — canonical v2.1 paper (April 2026)
- `v2.0-paper` — historical paper v2 draft (provenance only)
- `v1.0-paper` — historical paper v1 (provenance only)
- `v7.1-production` — v7.1 production baseline

## Author

Hoang Thai — Independent Research (2026)
Pre-MSc candidate, Data Science applications 2027

## License

MIT License for code. Please cite the paper if using methodology.
