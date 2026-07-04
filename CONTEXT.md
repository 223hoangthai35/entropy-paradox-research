# BỐI CẢNH DỰ ÁN — Entropy Paradox (research repo)

> **Read this file first.** Orientation anchor for new Claude Code
> sessions. CLAUDE.md is the developer how-to; CONTEXT.md is the
> project state-of-play.

---

## 1. What this repo is

A research-only repository for the canonical paper *The Entropy
Paradox* (v2.1). The paper evaluates an 8-market panel
(VNINDEX, PSEI, KOSPI, NIFTY, SPX, FTSE, NIKKEI, BTC) under a fixed
post-COVID 2020-01-01 → 2026-04-17 window using rolling SPE_Z
features, GMM regime classification, and a Schmitt-trigger hysteresis
post-filter.

The **thesis**: in Type-2 chaotic systems like financial markets,
**low entropy = coordinated behaviour = fragility**, inverting the
gas-thermodynamics intuition. Paper v2.1 reframes this as a
*microstructure gradient* — the paradox magnitude tracks Retail
Participation Share rather than holding uniformly.

Production tooling (Streamlit dashboard, LLM agent orchestrator) lives
in a companion production repository (reference withheld during
double-anonymized review; restored upon acceptance).
This repo is research-only.

  - User-facing description: [README.md](README.md)
  - Technical spec: [architecture.md](architecture.md)
  - Canonical paper: [paper_artifacts/paper_v2_1_combined_summary.md](paper_artifacts/paper_v2_1_combined_summary.md)
  - Developer how-to: [CLAUDE.md](CLAUDE.md) (gitignored, local)

---

## 2. Branch and tag landscape

| Branch / tag                | Status   | Purpose                                        |
|-----------------------------|----------|------------------------------------------------|
| `master`                    | tracking | Receives `--no-ff` merges from working branch  |
| `v7.2-case-a-validation`    | **active** | Default working branch                       |
| `v3.4-jfds-submission`      | tag      | Journal-submission manuscript v3.4 archive (2026-07-04) — canonical reproducibility tag cited on the title page |
| `v2.1.3-prereg-audit`       | tag      | Prior canonical HEAD (paper + audit)           |
| `v2.1-paper-combined`       | tag      | Canonical v2.1 paper (April 2026)              |
| `v2.0-paper`                | tag      | Historical paper v2 draft (provenance only)    |
| `v1.0-paper`                | tag      | Historical paper v1 (provenance only)          |
| `v7.1-production`           | tag      | Pre-research-split production baseline         |

The earlier `phase0..phase5-*` and `v7.1-hysteresis-rolling-garch`
branches are archived; pre-COVID-window v1 and v2 papers live only at
their tags. Active research lives on `v7.2-case-a-validation`; merging
to `master` is standard workflow now that the repo is research-only.

---

## 3. Paper v2.1 — hypotheses and where they live

Pre-registration frozen at commit `b130b0f` (2026-04-18):
[pre_registration/hypotheses_v2_combined.md](pre_registration/hypotheses_v2_combined.md).
Scientific-foundation audit:
[pre_registration/critique.md](pre_registration/critique.md).

| H  | What                                          | Test script                                      | Outputs (under `validation/results_v2/`)                                  |
|----|-----------------------------------------------|--------------------------------------------------|----------------------------------------------------------------------------|
| H1 | Paradox direction (Det > Sto, pairwise MW)    | `validation/cross_market_v2.py`                  | `cross_market_summary_v2.csv`, `cross_market_h1_horizons.csv`              |
| H2 | Microstructure gradient ρ(H, RPS)             | `validation/h2_rps_validation.py`                | `h2_rps_panel.csv`, `h2_rps_validation.json`, `h_vs_rps_v2.png`            |
| H3 | Transitional persistence (block-bootstrap CI) | `validation/hysteresis_cross_market_v2.py`       | `h3_refined.csv`, `h3_continuous.json`                                     |
| H4 | Temporal structure (block-permutation + FDR)  | same as H3                                       | `h4_block_permutation.csv`                                                 |
| H5 | Parameter robustness (pre-reg dead-zone rule) | `validation/hysteresis_robustness_v2.py`         | `h5_refined.csv`, `hysteresis_robustness_v2.{csv,json}`                    |

Paper §12 exploratory robustness appendix (NOT pre-registered):
- V2 GARCH benchmark on VNINDEX → `validation/garch_vnindex_v2.py`
- V3 tail-Lift on 8 markets, adaptive thresholds → `validation/tail_lift_8market.py`
- V4 entropy vs SimpleVol vs Combined on 8 markets → `validation/entropy_vs_simple_8market.py`

Pre-registration archive (frozen first-run outputs):
[validation/results_v2/prereg_b130b0f/](validation/results_v2/prereg_b130b0f/).

---

## 4. Pinned hyperparameters (research invariants — do not parameterise)

Baked into [validation/_features.py](validation/_features.py); mirror
the production pipeline. Changing any of them invalidates the entire
canonical validation suite. Sweep them only on a NEW branch with a new
tag.

| Constant                | Value | File                                              |
|-------------------------|-------|---------------------------------------------------|
| WPE m                   | 3     | [skills/quant_skill.py](skills/quant_skill.py)    |
| WPE tau                 | 1     | same                                              |
| WPE rolling window      | 22    | same                                              |
| Price SampEn window     | 60    | same                                              |
| SPE_Z rolling window    | 504   | same — note 2-year labelable-bar floor            |
| GMM n_components        | 3     | [skills/ds_skill.py](skills/ds_skill.py)          |
| GMM covariance_type     | full  | same                                              |
| GMM random_state        | 42    | same                                              |
| Hysteresis delta_hard   | 0.60  | `HYSTERESIS_DELTA_HARD` in ds_skill.py            |
| Hysteresis delta_soft   | 0.35  | `HYSTERESIS_DELTA_SOFT`                           |
| Hysteresis t_persist    | 8     | `HYSTERESIS_T_PERSIST`                            |
| Refit interval          | 21    | `REFIT_INTERVAL` (rolling GMM)                    |

Hysteresis was calibrated on VNINDEX post-2020 to a 4–10 flips/yr
target band (achieves ~7.8/yr); calibration source:
[scripts/calibrate_hysteresis.py](scripts/calibrate_hysteresis.py).

---

## 5. Paper terminology ↔ code

| Paper term                          | Code symbol / location                                                                     |
|-------------------------------------|--------------------------------------------------------------------------------------------|
| WPE, weighted permutation entropy   | `calc_rolling_wpe()` in [skills/quant_skill.py](skills/quant_skill.py)                     |
| SPE_Z, standardised price SampEn    | `calc_rolling_price_sample_entropy()` + `cal_spe_z_rolling()` (win=504), same file         |
| Plane 1                             | `[WPE, SPE_Z]` matrix; built by `validation/_features.build_plane1_features()`             |
| Plane 2 (volume)                    | `[Vol_Shannon, Vol_SampEn]`; PowerTransform + GMM                                          |
| Deterministic (Det) regime          | label=0 in `EntropyPhaseSpaceClassifier`                                                   |
| Transitional regime                 | label=1                                                                                    |
| Stochastic (Sto) regime             | label=2                                                                                    |
| Hysteresis filter                   | `HysteresisGMMWrapper` in [skills/ds_skill.py](skills/ds_skill.py)                         |
| `raw_labels` vs `filtered_labels`   | Both returned by `validation/_features.run_full_pipeline()`                                |
| Filtered flip rate                  | `flip_rate_per_year(out["filtered_labels"])` in [validation/_features.py](validation/_features.py) |
| Retail Participation Share (RPS)    | Per-market constant in `validation/cross_market_v2.py`; rationale in [paper_artifacts/rps_rationale.md](paper_artifacts/rps_rationale.md) |
| Transitional Dominance              | Reframed in v2.1 as a continuous gradient ρ(p_tra, RPS) = 0.56                             |

Old triple "Stable / Fragile / Chaos" is wrong about the danger
ordering; it has been retired. Current labels live in `REGIME_NAMES`
at [skills/ds_skill.py:35](skills/ds_skill.py#L35).

---

## 6. Operational invariants (decisions made — do not re-litigate)

- **No PowerTransformer on Plane 1.** Plane 1 GMM operates on raw
  `[WPE, SPE_Z]`. Plane 2 (volume) DOES use PowerTransformer. Mixing
  this up produces non-reproducible regime labels.

- **SPE_Z is rolling, not global, in v2.1 production.** The global
  variant `cal_spe_z_global` is retained only for static analysis
  scatter overlays. Switching the pipeline to global SPE_Z
  reintroduces look-ahead bias.

- **The 504-day SPE_Z window precludes labelling the first ~2 years
  of any dataset.** v2.1 loads from 2018-01-01 (or 2020-01-01 for
  H3/H4/H5) so labelable bars are post-COVID by construction.

- **Pre-registration discipline.** `hypotheses_v2_combined.md` is
  frozen at `b130b0f`. All H1–H5 changes since the pre-reg are
  documented in the §9 appendix and `pre_registration/critique.md`,
  with the "additive, not altering" regression assertion enforced in
  the validation scripts.

---

## 7. Scripts you will likely need

  - Recalibrate hysteresis: `python scripts/calibrate_hysteresis.py`
  - Run the canonical paper validation suite:
    ```
    python validation/cross_market_v2.py            # H1 + H2 (Phase 1)
    python validation/h2_rps_validation.py          # H2 RPS panel
    python validation/hysteresis_cross_market_v2.py # H3 + H4 (Phase 2)
    python validation/hysteresis_robustness_v2.py   # H5 (Phase 2b)
    ```
  - Run the §12 appendix scripts:
    ```
    python validation/garch_vnindex_v2.py
    python validation/tail_lift_8market.py
    python validation/entropy_vs_simple_8market.py
    ```

All validation scripts memoise the GMM pipeline per
`(market, start, end)` via
[scripts/extract_flip_dates.py](scripts/extract_flip_dates.py), so
running multiple tests in the same Python process reuses the fit.

No build step, no test runner, no linter. Each `skills/*.py` file has
an `if __name__ == "__main__":` block for standalone smoke testing.

---

## 8. Where to look when something feels off

- **"Why is the flip rate suddenly different?"** → check
  `HysteresisGMMWrapper` parameters. They are immutable defaults; any
  drift means someone overrode them. Also check if SPE_Z accidentally
  flipped to global.
- **"Why does the GMM emit different labels?"** → `random_state=42`
  is pinned everywhere. If labels look re-shuffled, check that
  `_label_map` (semantic sort by centroid entropy) is being applied.
- **"Why does the validation script pull empty data?"** → vnstock
  and yfinance both have rate limits. Re-run with a sleep, or shrink
  the date range.
- **"Why is the bootstrap p-value suspicious?"** → look for
  `datetime64[D]` casting. pandas builds disagree on the int64
  representation of timestamps; circular block bootstrap that mixes
  date-arithmetic and integer indexing can silently misalign.

---

## 9. Conventions for new work

- Validation scripts and outputs live under [validation/](validation/)
  with JSON / CSV / PNG outputs in
  [validation/results_v2/](validation/results_v2/).
- Paper drafts and rationales live in
  [paper_artifacts/](paper_artifacts/).
- Pre-registration documents and audits live in
  [pre_registration/](pre_registration/).
- Discoveries after pre-registration are documented in
  `pre_registration/critique.md` (the audit log), not in the frozen
  pre-reg document.
- Commit messages: imperative mood, scope prefix
  (`feat(validation):`, `fix(hysteresis):`, `docs(paper):`,
  `chore(repo):`); explain WHY the change is necessary, not what the
  diff says.

---

*Last updated: 2026-04-29 (research-only repo, v2.1-only HEAD).
If you change something here that future sessions need to know,
update both this file and the relevant section in CLAUDE.md.*
