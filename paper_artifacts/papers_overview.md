# Papers Overview

Three successive drafts describe the same underlying phenomenon —
**microstructure-dependent entropy-volatility coupling** — at progressively
larger scope and methodological tightness.

| Version | Date       | Tag                     | Scope                       | Headline claim                                                    |
|---------|------------|-------------------------|-----------------------------|-------------------------------------------------------------------|
| v1      | April 2026 | `v1.0-paper`            | 3 markets, ~10-yr window    | Entropy Paradox: low entropy → higher vol on frontier; inverts on developed |
| v2      | May 2026 (draft) | `v2.0-paper`      | 3 markets, 2022–2026 common | Adds hysteresis + Transitional Dominance (VN p(Tra) ≈ 67.8%)      |
| v2.1    | April 2026 | `v2.1-paper-combined`   | 8 markets, 2020–2026        | Paradox direction tracks MS_index (Spearman ρ ≈ 0.95); Transitional Dominance extended to 8-market panel |

Per-version summaries:

- [paper_v1_summary.md](paper_v1_summary.md) — Entropy Paradox, V1–V5 validation
- [paper_v2_summary.md](paper_v2_summary.md) — Hysteresis + Case A (T1–T4, T-D)
- [paper_v2_1_combined_summary.md](paper_v2_1_combined_summary.md) — 8-market, post-COVID, H1–H5

Extended drafts and working artifacts:

- [section_5_6_draft.md](section_5_6_draft.md) — Paper v2 Section 5.6 draft text
- [ms_index_rationale.md](ms_index_rationale.md) — H2 / Microstructure Index construction, robustness, and the "not a VNINDEX outlier" argument

## Why three versions

- **v1 → v2.** v1 left regime *cadence* and *duration* unexamined. When
  v7.1's hysteresis filter reduced the raw ~28 flips/yr on VNINDEX to
  ~7.8/yr, the question became: is that residual cadence real or an
  artifact? v2 answers it (Case A validation).
- **v2 → v2.1.** v1 and v2 both used a 3-market panel and both
  effectively labelled post-2020 bars (the 504-bar rolling SPE_Z
  precludes labelling earlier). v2.1 makes the post-COVID window
  explicit, widens the panel to 8 markets grouped by microstructure, and
  pre-registers H1–H5 (commit `b130b0f`) before running Phase 1.

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
