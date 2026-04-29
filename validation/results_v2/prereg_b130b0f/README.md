# Pre-Registered H1 Outputs — Commit `b130b0f`

Frozen snapshot of the Phase-1 cross-market H1 validation as produced
under the pre-registration committed in
[pre_registration/hypotheses_v2_combined.md](../../../pre_registration/hypotheses_v2_combined.md)
at commit `b130b0f` (2026-04-18).

These files are read-only reference artifacts. Do not modify them.

## Provenance

- Pre-registration commit: `b130b0f1f2769566eaf548181d6816eb31b1963e`
- Pre-registration date: 2026-04-18
- Analysis window: 2020-01-01 → 2026-04-17 (in-sample fit 2018-01-01 →)
- Panel: VNINDEX, PSEI, KOSPI, NIFTY, SPX, FTSE, NIKKEI, BTC (8 markets)
- Script: `validation/cross_market_v2.py` (pre-refactor)
- Feature recipe: WPE m=3/τ=1/win=22, SampEn win=60, rolling SPE_Z win=504
- GMM: k=3, full-cov, random_state=42
- Labels: raw GMM argmax (pre-hysteresis)

## Contents

| File | Purpose |
|------|---------|
| `cross_market_summary_v2.csv` | Per-market H-stat, p-value, regime means, direction, MS_index |
| `<MARKET>_v2_results.json` × 8 | Per-market full result (regime shares, drawdown lifts, medians) |
| `cross_market_validation_v2.png` | Per-market boxplot grid (fwd vol by regime) |
| `h_vs_microstructure_v2.png` | H-stat vs MS_index scatter (H2 visualisation) |
| `cross_market_v2_run.log` | Original stdout log of the pre-reg run (if present) |

## Why this snapshot exists

The active `validation/cross_market_v2.py` has been **refactored post-hoc**
to add scientific-foundation upgrades: pairwise Deterministic-vs-Stochastic
contrast (one-sided Mann-Whitney + Cliff's δ), KW ε² effect size, Dunn's
post-hoc with Holm adjustment, BH-FDR across the 8-market panel, block
bootstrap CIs, Newey-West corrected t-stats, and forward-vol horizon
robustness ({5, 10, 20, 40, 60}d). See
[paper_artifacts/paper_v2_1_combined_summary.md §9](../../../paper_artifacts/paper_v2_1_combined_summary.md)
for the refined interpretation.

The refactor is **additive and backward-compatible**: the refactored
script's output CSV still contains the legacy `H_stat`, `p_value`, and
`direction` columns, and a regression assertion in `main()` diffs them
against this archive to 4 decimal places. The pre-registration claim
(H1 rejected iff frontier H<20 or direction inverted, etc.) is evaluated
on the *archived* numbers here, not on any recomputed version.

---

## H3 / H4 / H5 snapshot — addendum (2026-04-19)

The hysteresis scripts — `validation/hysteresis_cross_market_v2.py`
(H3 persistence + H4 shuffle test) and
`validation/hysteresis_robustness_v2.py` (H5 parameter robustness) —
were **added post-b130b0f**. The pre-registration commit does not
include them; the numbers here are therefore the **first-run outputs
under the pre-reg falsification rules**, frozen immediately before the
post-hoc rigor upgrade described in
[paper_artifacts/paper_v2_1_combined_summary.md §10](../../../paper_artifacts/paper_v2_1_combined_summary.md).

This snapshot captures the categorical pre-reg verdicts prior to any
block-bootstrap CI on `p_tra`, continuous `Spearman(p_tra, RPS)` test,
block-permutation shuffle variant, or BH-FDR multiplicity correction.

### Contents (H3/H4/H5 addendum)

| File | Purpose |
|------|---------|
| `hysteresis_summary_v2.csv` | Per-market p_det/p_tra/p_sto, regime durations, shuffle p-value, H4 verdict. Columns include `ms_index` (pre-RPS-refactor column name — now `rps` in active scripts). |
| `<MARKET>_hysteresis.json` x 8 | Per-market full hysteresis + duration + shuffle result. |
| `hysteresis_robustness_v2.csv` | Per-market x per-config (A/B/C) p_tra and H5 spread verdict. |
| `hysteresis_robustness_v2.json` | H5 summary JSON with per-market spread and pass/reject. |
| `hysteresis_cross_market_v2_run.log` | Original stdout log of first-run. |
| `hysteresis_robustness_v2_run.log` | Original stdout log of first-run. |

Not in this archive: `p_transitional_vs_rps.png` — the figure was not
emitted by the first-run (the script rename from `plot_p_tra_vs_ms` to
`plot_p_tra_vs_rps` post-dated this CSV snapshot). Refactored runs
emit it to the active `results_v2/` directory.

### Pre-reg categorical verdicts as frozen here

- **H3** (frontier p_tra > 0.55, developed < 0.50, diff > 10 pp):
  REJECT on VNINDEX (p_tra=0.451, < 0.45 falsification threshold) and
  PSEI (0.403). Other markets trivially PASS (neither Frontier nor
  Developed category).
- **H4** (shuffle test p < 0.01): PASS on all 8 markets (every
  p approx 0, verdict STRUCTURED).
- **H5** (3-config p_tra spread < 5 pp): PASS on VNINDEX (3.4 pp),
  NIKKEI (2.0), BTC (2.7). REJECT on PSEI (5.6), KOSPI (7.2), NIFTY
  (7.7), SPX (9.0), FTSE (9.5).

The refactored scripts' regression assertion diffs the legacy
`p_det`, `p_tra`, `p_sto`, `shuffle_p_value`, `shuffle_verdict`,
`filtered_flips_per_year` columns against this archive to ensure the
rigor upgrade is additive, not altering.
