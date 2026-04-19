# Paper v2 — Hysteresis + Transitional Dominance (May 2026, draft)

> **Historical snapshot — superseded by v2.1.** This file preserves the
> May 2026 v2 draft at reproducibility tag `v2.0-paper`. The canonical
> paper is [paper_v2_1_combined_summary.md](paper_v2_1_combined_summary.md)
> (8-market panel, post-COVID window, H1–H5 under the refined statistical
> architecture with pre-registration transparency). v2 is retained for
> provenance of the Transitional Dominance line of argument; do not cite
> as current.

**Title.** *Hysteresis-Filtered Regime Classification and Transitional
Dominance on Frontier Equity.*

**Reproducibility tag.** `v2.0-paper` (current HEAD of `v7.2-case-a-validation`).

**Draft artifact.** [section_5_6_draft.md](section_5_6_draft.md).

---

## 1. What triggered v2

Paper v1 left the raw GMM flip rate (~28/yr on VNINDEX) as *implicit noise*.
v7.1 added a Schmitt-trigger hysteresis post-filter that knocked the cadence
down to ~7.8/yr. That left one question: is the residual 7.8/yr
cadence a real regime signal or just a product of where we set the
hysteresis thresholds? **Case A validation** was the answer.

## 2. Methodology refinements vs v1

| Component          | v1 (master)          | v2 (v7.2)                  |
|--------------------|----------------------|----------------------------|
| SPE_Z              | Global z-score       | **Rolling win=504** (no look-ahead) |
| Hysteresis filter  | None                 | δ_hard=0.60, δ_soft=0.35, t_persist=8 |
| Risk engine        | Tri-vector composite | **GARCH-X only** (v7.0 composite removed in d364009) |
| Pre-registration   | Implicit             | `KNOWN_EVENTS_VNINDEX` frozen in commit 4b146b1; hypotheses H1–H5 frozen in b130b0f |

## 3. Markets

Same three as v1: **VNINDEX, SP500, BTC-USD.** Common analysis window
2022-01-01 → 2026-04-17 (the 504-bar rolling SPE_Z precludes labelling
the first ~2 years of each dataset).

## 4. Case A tests (pre-registered T1–T4 + T-D)

| Test | Status | Headline |
|------|--------|----------|
| T1 event study          | NULL         | precision 16.1% vs null 12.7%, p = 0.359 |
| T1-wide (±21d tol.)     | NULL strong  | precision 19.4%, null mean 24.7%, p = 0.814 |
| T2 cross-market flip    | **REFRAMED** | VN flips *less* than SPX/BTC — opposite of the frontier-fragility prediction |
| T3 shuffle test         | **PASS**     | observed 7.77 vs null 118.36 flips/yr, p < 1e-4 STRUCTURED |
| T-D regime duration     | **NEW**      | **Transitional Dominance** — VN p(Tra) ≈ 67.8%, T_tra ≈ 62 days |
| T4 hysteresis robustness| **PASS**     | p(Tra) ∈ {66.1%, 67.8%, 68.8%} across 3 configs (2.7 pp spread) |

## 5. The headline result — Transitional Dominance

VNINDEX spends ~67.8% of trading bars in the **Transitional** regime with
62-day mean spells. SPX and BTC spend proportionally less time there and
have shorter spells. T4 confirms this is *structural* — it survives loose
and tight hysteresis configurations with <3 pp drift.

Interpretation: **frontier fragility does not operate through faster
transition cadence** (v1's implicit framing). It operates through
*persistence in an intermediate coordination regime* — neither fully ordered
nor fully random, but stuck in a metastable middle.

## 6. What v2 reformulates vs v1

- The Entropy Paradox *itself* (v1's finding) is **not refuted**. It stands
  at the level of regime-conditional return distributions.
- v1's implicit "frontier = faster flips" intuition is **rejected** by T2.
- v1's tri-vector composite as a risk engine is **deprecated** in favour of
  GARCH-X (v7.1 decision, locked in d364009).

## 7. Reproducibility

```
git checkout v2.0-paper
python validation/event_study.py                         # T1
python validation/event_study_robustness.py              # T1 addenda
python validation/cross_market_flip_rate.py              # T2
python validation/shuffle_test.py                        # T3
python validation/regime_duration.py                     # T-D
python validation/transitional_dominance_robustness.py   # T4
```

Outputs land in `validation/results/`.
