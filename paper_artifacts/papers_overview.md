# Papers Overview

The canonical paper is **v2.1** (`v2.1-paper-combined`). v1 and v2 are
preserved as historical draft snapshots documenting the progression of
scope and methodological tightness. Only v2.1 reflects the final
statistical architecture and the pre-registration transparency review.

| Version | Date       | Tag                     | Status      | Scope                       | Headline claim                                                    |
|---------|------------|-------------------------|-------------|-----------------------------|-------------------------------------------------------------------|
| v1      | April 2026 | `v1.0-paper`            | Historical  | 3 markets, ~10-yr window    | Entropy Paradox: low entropy → higher vol on frontier; inverts on developed |
| v2      | May 2026 (draft) | `v2.0-paper`      | Historical  | 3 markets, 2022–2026 common | Adds hysteresis + Transitional Dominance (VN p(Tra) ≈ 67.8%)      |
| v2.1    | April 2026 | `v2.1-paper-combined`   | **Canonical** | 8 markets, 2020–2026      | Paradox *magnitude* tracks Retail Participation Share (Spearman ρ = 0.754, p = 0.031). Pairwise direction survives on PSEI @ 20d only. Transitional Dominance is a microstructure gradient (continuous ρ = 0.56, n = 8). |

Per-version summaries:

- [paper_v1_summary.md](paper_v1_summary.md) — **historical snapshot.** Entropy Paradox, V1–V5 validation. Superseded by v2.1.
- [paper_v2_summary.md](paper_v2_summary.md) — **historical snapshot.** Hysteresis + Case A (T1–T4, T-D). Superseded by v2.1.
- [paper_v2_1_combined_summary.md](paper_v2_1_combined_summary.md) — **canonical v2.1 paper.** 8-market, post-COVID, H1–H5 under refined statistical architecture with pre-registration transparency.

Extended drafts and working artifacts:

- [section_5_6_draft.md](section_5_6_draft.md) — Paper v2 Section 5.6 draft text (historical)
- [rps_rationale.md](rps_rationale.md) — H2 Retail Participation Share construction, sources, robustness, and the "not a VNINDEX outlier" argument
- [../pre_registration/hypotheses_v2_combined.md](../pre_registration/hypotheses_v2_combined.md) — Frozen pre-registration at commit `b130b0f` (2026-04-18)
- [../pre_registration/critique.md](../pre_registration/critique.md) — Scientific-foundation audit of the H1–H5 pre-registration design (`v2.1.3-prereg-audit`)

## Progression of scope

- **v1 → v2.** v1 left regime *cadence* and *duration* unexamined. When
  v7.1's hysteresis filter reduced the raw ~28 flips/yr on VNINDEX to
  ~7.8/yr, the question became: is that residual cadence real or an
  artifact? v2 answers it (Case A validation).
- **v2 → v2.1.** v1 and v2 both used a 3-market panel and both
  effectively labelled post-2020 bars (the 504-bar rolling SPE_Z
  precludes labelling earlier). v2.1 makes the post-COVID window
  explicit, widens the panel to 8 markets grouped by microstructure,
  and pre-registers H1–H5 (commit `b130b0f`) before running Phase 1.
  v2.1's statistical architecture was further refined during the
  scientific-foundation review: pairwise directional tests replace KW
  omnibus for H1, a single-variable RPS replaces a three-component
  composite for H2, bootstrap CIs and continuous companions replace
  categorical thresholds for H3, block-permutation replaces simple
  shuffle for H4, and the pre-registered dead-zone rule is applied as
  written for H5. The pre-registration transparency appendix in v2.1
  §9 and the full audit at `pre_registration/critique.md` document the
  refinement history.

## What is *not* changed between versions

- Feature recipe: WPE (m=3, τ=1, win=22); Sample Entropy win=60; rolling
  SPE_Z win=504.
- GMM: k=3, full covariance, random_state=42.
- Hysteresis defaults: δ_hard=0.60, δ_soft=0.35, t_persist=8 (calibrated
  on VNINDEX post-2020; `scripts/calibrate_hysteresis.py`).

These are research invariants — sweeping them requires a new branch and a
new tag (see [CLAUDE.md](../CLAUDE.md) "Research invariants").

## Validation provenance

- Paper v1 results → `validation/results/` (V1–V5 scripts).
- Paper v2 results → `validation/results/` (T1–T4, T-D scripts).
- Paper v2.1 results → `validation/results_v2/` (Phase 1, 2, 2.1 scripts).
- Paper v2.1 earlier 2016-window results archived under
  `validation/results_v2_2016win/` for reference.

## Citation

Hoang Thai (2026). *The Entropy Paradox.* Independent research, pre-MSc
programme. Reproducibility tags as above.
