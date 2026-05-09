# Papers Overview

The repository hosts **paper v2.1** as the canonical and only active
paper. Earlier drafts (v1, v2) used pre-COVID windows and are no
longer maintained in HEAD; they remain reachable via git tags
`v1.0-paper` and `v2.0-paper` for provenance only.

| Version | Date       | Tag                     | Status        | Scope                       | Headline claim                                                    |
|---------|------------|-------------------------|---------------|-----------------------------|-------------------------------------------------------------------|
| v2.1    | April 2026 | `v2.1-paper-combined`   | **Canonical** | 8 markets, 2020–2026 (post-COVID) | Paradox *magnitude* tracks Retail Participation Share (Spearman ρ = 0.754, p = 0.031). Pairwise direction survives on PSEI @ 20d only. Transitional Dominance is a microstructure gradient (continuous ρ = 0.56, n = 8). |

Per-version summaries:

- [paper_v2_1_combined_summary.md](paper_v2_1_combined_summary.md) —
  **canonical v2.1 paper.** 8-market, post-COVID, H1–H5 under refined
  statistical architecture with pre-registration transparency, plus a
  §12 exploratory robustness appendix (V2/V3/V4 redos under v2.1 recipe).

Working artifacts in this folder:

- [rps_rationale.md](rps_rationale.md) — H2 Retail Participation Share
  construction, sources, robustness, and the architectural-refinement
  history from the composite MS_index.
- [../pre_registration/hypotheses_v2_combined.md](../pre_registration/hypotheses_v2_combined.md) —
  Frozen pre-registration at commit `b130b0f` (2026-04-18).
- [../pre_registration/critique.md](../pre_registration/critique.md) —
  Scientific-foundation audit of the H1–H5 pre-registration design
  (`v2.1.3-prereg-audit`).

## Scope and window

v2.1 fixes the test window at 2020-01-01 → 2026-04-17. The 504-bar
rolling SPE_Z requires that much warmup, so labelable bars are
post-COVID by construction. Pre-2020 windows from the v1 / v2 drafts
do not align with this recipe and have been removed from HEAD.

The statistical architecture refined during the scientific-foundation
review: pairwise directional tests replace KW omnibus for H1, a
single-variable RPS replaces a three-component composite for H2,
bootstrap CIs and continuous companions replace categorical
thresholds for H3, block-permutation replaces simple shuffle for H4,
and the pre-registered dead-zone rule is applied as written for H5.
The pre-registration transparency appendix in v2.1 §9 and the full
audit at `pre_registration/critique.md` document the refinement
history.

## Research invariants (locked across the canonical paper)

- Feature recipe: WPE (m=3, τ=1, win=22); Sample Entropy win=60;
  rolling SPE_Z win=504.
- GMM: k=3, full covariance, random_state=42.
- Hysteresis defaults: δ_hard=0.60, δ_soft=0.35, t_persist=8
  (calibrated on VNINDEX post-2020;
  [`scripts/calibrate_hysteresis.py`](../scripts/calibrate_hysteresis.py)).

These are research invariants — sweeping them requires a new branch
and a new tag (see [CLAUDE.md](../CLAUDE.md) "Research invariants").

## Validation provenance

- **Phase 1 (H1 + H2)**: [validation/cross_market_v2.py](../validation/cross_market_v2.py),
  [validation/h2_rps_validation.py](../validation/h2_rps_validation.py)
  → outputs under [validation/results_v2/](../validation/results_v2/).
- **Phase 2 (H3 + H4)**: [validation/hysteresis_cross_market_v2.py](../validation/hysteresis_cross_market_v2.py)
  → `h3_refined.csv`, `h3_continuous.json`, `h4_block_permutation.csv`,
  per-market `*_hysteresis.json`.
- **Phase 2b (H5)**: [validation/hysteresis_robustness_v2.py](../validation/hysteresis_robustness_v2.py)
  → `h5_refined.csv`, `hysteresis_robustness_v2.csv|json`.
- **Pre-registration archive**: [validation/results_v2/prereg_b130b0f/](../validation/results_v2/prereg_b130b0f/)
  preserves the frozen first-run outputs at commit `b130b0f`.
- **§12 appendix (paper-v1 V2/V3/V4 redo, exploratory)**:
  [validation/garch_vnindex_v2.py](../validation/garch_vnindex_v2.py),
  [validation/tail_lift_8market.py](../validation/tail_lift_8market.py),
  [validation/entropy_vs_simple_8market.py](../validation/entropy_vs_simple_8market.py)
  → `garch_vnindex_v2.{json,png}`, `tail_lift_8market.{csv,json,png}`,
  `entropy_vs_simple_8market.{csv,json,png}`.

## Citation

Hoang Thai (2026). *The Entropy Paradox.* Independent research,
pre-MSc programme. Reproducibility tag: `v2.1-paper-combined`
(canonical) or `v2.1.3-prereg-audit` (canonical + pre-registration
audit appendix).
