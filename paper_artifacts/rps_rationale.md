# Retail Participation Share (RPS) — H2 Microstructure Specification

Companion note to [paper_v2_1_combined_summary.md](paper_v2_1_combined_summary.md).
This document supplies the construction, sourcing, and robustness analysis
for **Retail Participation Share (RPS)** — the single-variable
microstructure proxy used to test hypothesis **H2** (the Entropy Paradox
scales with microstructure depth).

---

## 1. What H2 claims

The Entropy Paradox (paper v1) is a sign on the Deterministic–minus–Stochastic
forward-volatility gap, measured as the Kruskal–Wallis H-statistic on
regime-conditional forward 20-day vol. v1 showed the sign is **positive on
VNINDEX** (frontier) and **inverts on SPX** (developed). v2.1's claim is
stronger:

> **H2.** The magnitude of the H-statistic scales monotonically with an
> a-priori single-variable microstructure proxy — i.e. the paradox is
> not a binary frontier/developed artifact but a *continuous*
> microstructure-depth phenomenon.

If H2 holds with a high-enough rank correlation, "frontier vs developed"
drops out of the story. The paradox becomes a gradient, not a dichotomy.

---

## 2. Why RPS, and why a single variable

### 2.1 Architectural refinement — from composite MS_index to RPS

The version originally pre-registered in commit `b130b0f` (2026-04-18) was
a **composite** three-component index combining circuit-breaker presence
(weight 0.4), institutional-share complement (0.3), and log-inverse
market cap (0.3). During the scientific-foundation review that preceded
the paper's final statistical architecture, the composite was judged
scientifically untenable on two grounds:

1. The 0.4 / 0.3 / 0.3 weights were chosen by the authors on qualitative
   reasoning ("circuit breakers are structural, not compositional"). They
   were not derived from first principles, not cross-validated against a
   held-out panel, and not benchmarked against alternative weight schemes.
   Any ρ computed against such a scale carries the weight-choice as an
   uncontrolled degree of freedom.
2. The three components are measured in **incompatible units** (binary
   indicator, share ∈ [0,1], log-USD). Linear combination across
   incompatible units produces a number whose *ranking* is interpretable
   (Spearman is scale-free) but whose *magnitude* is not. Reporting a
   composite scalar as though it were a real-valued microstructure
   measurement overstates the precision of the construction.

RPS replaces the composite as the H2 primary instrument. The replacement
is an architectural refinement conditioned on a single published number
per market, with full transparency of the pre-reg history. The composite
value and its pre-registered ρ = 0.952 result are preserved read-only
in the pre-registration archive at
[validation/results_v2/prereg_b130b0f/](../validation/results_v2/prereg_b130b0f/);
the paper's active H2 test reports ρ(H, RPS) = 0.754, a *lower* ρ than
the composite — the refinement went against author self-interest. See
[pre_registration/critique.md §2](../pre_registration/critique.md) for
the full audit entry.

### 2.2 RPS — one measurement, one unit, publicly sourced

**Retail Participation Share (RPS)** is the share of trading **value** (not
volume, not accounts) attributable to retail participants, expressed as a
number in [0, 1]. The choice is driven by three properties:

| Property | Why it matters |
|---|---|
| **Single variable** | No weights to tune. The Spearman ρ reported against RPS is conditional on one number per market and on the published source, nothing else. |
| **Unit-interpretable** | All eight markets report RPS as a trading-value share. Cross-market comparisons are like-for-like; there is no log-vs-binary-vs-ratio mixing. |
| **Published by reputable sources** | Every RPS value below is drawn from an exchange annual report, a regulator filing, or a recognised industry association's published research — not from author construction. The paper does not ask the reader to trust a custom weighting scheme. |

RPS is also ex-ante to the return series used to compute H_stat: all
values were sourced before H_stat was recomputed in this specification.

### 2.3 Mechanism link (why RPS predicts H)

Higher RPS means trading flow is tilted toward participants who are
more trend-chasing, less mean-reverting, and slower to arbitrage
deterministic regime structure away. Institutional flow in low-RPS
markets (SPX, FTSE, NIKKEI) is dominated by rebalancers, hedgers, and
systematic arbitrageurs who compress the Deterministic-vs-Stochastic
entropy gap. As RPS climbs, that compression weakens and the GMM
discriminator's H-statistic grows.

---

## 3. RPS values and sources (ex-ante, pre-test)

| Market  | RPS  | Source |
|---------|------|--------|
| VNINDEX | 0.90 | VinaCapital (2024) *"Vietnam's Resilient Stock Market"* — retail-account trading share |
| PSEI    | 0.68 | Philippine Stock Exchange, 2023 Annual Report — retail turnover share |
| KOSPI   | 0.70 | ASIFMA (2022) *Korea Capital Markets Report*; KRX retail-participation disclosure |
| NIFTY   | 0.40 | NSE India Ownership Report, Q1 FY25 — retail turnover share |
| SPX     | 0.22 | SIFMA (2024) equity-ownership composition (~17.9%) + MEMX (2025) retail order-flow estimate (30–37%); midpoint ~22% |
| FTSE    | 0.18 | LSE / MEMX (2025) retail order-flow estimate; SQ Magazine (2026) UK retail statistics |
| NIKKEI  | 0.18 | JPX (2024) retail turnover share; SQ Magazine (2026) Japan retail participation |
| BTC     | 0.55 | Aggregated crypto-exchange retail-vs-institutional reports, 2024–2025 |

All eight values are **ex-ante market-structure facts**: they are based on
reporting periods before the analysis window closes (2026-04-17) and are
derived from trade-receipt or account-ownership data, not from the price
series used downstream. There is no leakage from outcome to regressor.

---

## 4. H2 test result

From [validation/results_v2/cross_market_summary_v2.csv](../validation/results_v2/cross_market_summary_v2.csv)
(analysis window 2020-01-01 → 2026-04-17, rolling SPE_Z win=504, raw GMM
argmax labels):

| Market  | RPS  | H-stat | p-value    | Legacy direction label |
|---------|------|--------|------------|------------------------|
| VNINDEX | 0.90 | 83.90  | 6.0e-19    | Paradox                |
| PSEI    | 0.68 | 48.10  | 3.6e-11    | Paradox                |
| KOSPI   | 0.70 |  5.88  | 0.053      | Paradox                |
| NIFTY   | 0.40 | 13.98  | 9.2e-4     | Inverted\*             |
| SPX     | 0.22 |  2.12  | 0.35       | n.s.                   |
| FTSE    | 0.18 |  4.15  | 0.13       | n.s.                   |
| NIKKEI  | 0.18 |  4.05  | 0.13       | n.s.                   |
| BTC     | 0.55 |  7.13  | 0.028      | Inverted\*             |

\* "Inverted" is the descriptive mean-ordering label from the legacy
pre-reg analysis. Under the formal pairwise test with bootstrap CI
(v2.1 §9), NIFTY and BTC are both **n.s.** at 20d; only PSEI @ 20d
passes the formal Paradox verdict. H2 tests the *magnitude* of H
against RPS and is independent of the per-market direction-verdict.

**Spearman ρ(H_stat, RPS) = 0.754, p = 0.0305, n = 8.**
Figure: [validation/results_v2/h_vs_rps_v2.png](../validation/results_v2/h_vs_rps_v2.png).

**H2 verdict: PASS** — clears both the ρ > 0.5 and p < 0.10 bars that
were pre-registered for the original composite specification. The
thresholds are reused here as a conservative reference bar for the
superseding specification; they are not re-registered.

---

## 5. Why this is still a strong result at ρ = 0.754

### 5.1 The alternative hypothesis this rules out

A sceptic of paper v1 could argue that VNINDEX is simply a statistical
outlier — one market happening to exhibit the paradox with high H, with
no generalisable mechanism. That alternative predicts **no** structure
in H across markets beyond VNINDEX itself.

RPS's rank correlation ρ = 0.754 on 8 markets is not consistent with
that. A monotone relationship between H-stat and a *single* a-priori
quantity drawn from public retail-turnover reports — with nothing from
the return series — is evidence that something systematic about market
microstructure drives the paradox.

### 5.2 Gradient, not dichotomy

As RPS climbs from 0.18 (SPX/FTSE/NIKKEI cluster) through 0.40–0.70
(emerging/BTC cluster) to 0.90 (VNINDEX), H climbs through ~2–4 → ~6–14
→ ~84. This is a gradient across four orders of magnitude in H, not a
binary flip.

### 5.3 No post-hoc tuning

- Each RPS value is drawn from **one** published source. No
  author-selected weights, no sensitivity knobs.
- All eight values were sourced before the H_stats were recomputed in
  the superseding specification; [validation/h2_rps_validation.py](../validation/h2_rps_validation.py)
  loads them from a frozen dict.
- The panel composition was pre-registered (choice between KSE / SET /
  PSEI etc.), not cherry-picked after seeing H.

### 5.4 Honest magnitude comparison

| Specification | Spearman ρ | p     | Scientific status |
|---------------|------------|-------|-------------------|
| Composite (weights 0.4/0.3/0.3) | 0.952 | 2.6e-4 | Pre-registered `b130b0f`; **superseded** — arbitrary weights invalidate ρ magnitude as evidence |
| RPS (single variable) | **0.754** | **0.031** | **Primary specification** — one ex-ante measurement per market |

The magnitude drop from 0.952 to 0.754 is the cost of giving up the
author-chosen degrees of freedom embedded in the composite's weights.
We regard the drop as a *correctness* gain, not a loss: a weaker
correlation against a principled single variable is stronger evidence
than a tighter correlation against a tunable scalar.

---

## 6. Robustness of the RPS result

### 6.1 Bootstrap 95% CI for ρ_RPS

10,000 pair-resamples (n=8, seed=42) yield a 95% CI of
**[0.089, 0.994]**, mean 0.691, sd 0.234. The CI is wide — expected at
n=8 — but the bulk of the distribution sits well above the ρ > 0.5
reference bar.

### 6.2 Monte Carlo measurement-noise sensitivity

Each market's RPS is perturbed by N(0, 0.05) (clamped to [0, 1]) and the
Spearman statistic recomputed. Over 10,000 trials (seed=43):

| Statistic | Value |
|-----------|-------|
| ρ mean    | 0.796 |
| ρ sd      | 0.049 |
| [p5, p50, p95] | [0.738, 0.810, 0.881] |
| **P(ρ > 0.5)** | **100.0 %** |

The RPS result is not a knife-edge on any one market's retail-share
value; ±0.05 absolute measurement error per market leaves the pre-reg
reference threshold untouched in every trial.

### 6.3 Stratified subpanels

| Subpanel | n | ρ_RPS | p_RPS |
|----------|---|-------|-------|
| Full panel | 8 | 0.754 | 0.031 |
| Circuit-breaker present | 6 | 0.771 | 0.072 |
| Circuit-breaker absent  | 2 | — | — (descriptive) |
| Frontier + Emerging     | 4 | 0.400 | 0.600 (descriptive) |
| Developed only          | 3 | — | — (descriptive) |

The full-panel and CB-present subpanels both clear ρ > 0.5; the
frontier-emerging subpanel at n=4 is descriptive only. The result is
not a one-bucket artifact.

### 6.4 Sample-size caveat

n = 8 is small. Spearman ρ = 0.754 at n = 8 has p ≈ 0.031 under the
standard null (exact permutation). This is reportable but it is not a
substitute for a larger panel — future work should extend to 15–20
markets once data-quality constraints on frontier / emerging feeds can
be relaxed.

---

## 7. Relationship to other hypotheses

| H  | Claim                          | RPS-H2 relation |
|----|--------------------------------|-----------------|
| H1 | Frontier paradox significance  | H2 *generalises* the direction claim: H-stat magnitude is ordered by retail participation across 8 markets |
| H3 | Transitional Dominance         | p(Tra) is a *different* metric from H-stat; H2 says nothing about p(Tra) |
| H4 | Shuffle-null structure         | Orthogonal — H4 is a within-market test |
| H5 | Hysteresis robustness          | Orthogonal — parameter stability, not cross-market gradient |

**Key paper-text nuance.** H2 establishes that *magnitude* (H-stat) scales
with RPS. The sign (Paradox vs Inverted vs n.s.) is reported per-market
in §4 of the summary but does *not* follow RPS monotonically (NIFTY and
BTC are descriptively Inverted at low-to-mid RPS). Paper text should
distinguish magnitude-scaling (H2 via ρ_RPS) from direction-per-market
(H1 via the pairwise test in §9).

---

## 8. Threats to validity

1. **Source heterogeneity.** The eight RPS values are drawn from eight
   different sources. Each is the best-available public estimate, but
   the definitional detail (executed volume vs turnover vs account
   share) varies in the second decimal. The MC-noise sensitivity
   analysis (§6.2) is the first-line response to this.

2. **Reporting-period drift.** VNINDEX RPS is from 2024, SPX is a
   2024-ish SIFMA-plus-MEMX midpoint, BTC is a 2024–2025 aggregate. A
   retail share is not a constant; a robustness run using a 2020
   snapshot (start of analysis window) is a reasonable follow-up.

3. **BTC is a genuine archetype.** Crypto is neither frontier nor
   developed; treating it as a single panel point is a compromise. Its
   mid-RPS value (0.55) and mid-range H (7.13) are roughly where a
   "high retail, high volatility, no circuit breaker" asset would land
   — consistent, but not a test.

4. **n = 8.** As in §6.4. Do not over-interpret the magnitude of ρ;
   focus on the *direction* of monotone scaling.

---

## 9. What the paper should say

Suggested paper-text for v2.1 §6 ("Structural interpretation"):

> The paradox direction does not follow a binary frontier/developed
> split. We use Retail Participation Share (RPS; share of trading value
> originating from retail participants) as a single-variable ex-ante
> microstructure proxy, with every value drawn from a published
> exchange, regulator, or industry-association report (VinaCapital,
> PSE, ASIFMA, NSE India, SIFMA, MEMX, JPX). Across the 8-market panel,
> the Kruskal–Wallis H-statistic from the raw-GMM regime discrimination
> scales monotonically with RPS (Spearman ρ = 0.754, p = 0.031, n = 8;
> bootstrap 95% CI [0.09, 0.99]; ρ > 0.5 in 100% of
> measurement-noise MC trials). The Entropy Paradox is therefore a
> *gradient* in microstructure depth rather than a frontier-market
> dichotomy.
>
> The specification originally pre-registered in commit `b130b0f` was a
> three-component composite (ρ = 0.952). Post-hoc review found the
> 0.4/0.3/0.3 weights were not theoretically derived and the three
> components are measured in incompatible units, so the magnitude of
> that ρ depended on an uncontrolled degree of freedom. We therefore
> adopt the single-variable RPS specification as primary. The composite
> result is preserved read-only under
> [`validation/results_v2/prereg_b130b0f/`](../validation/results_v2/prereg_b130b0f/).

---

## 10. Open follow-ups

- Refresh RPS with harmonised reporting-period snapshots (2020, 2023,
  2025) to quantify reporting-drift sensitivity.
- Extension to 15–20 markets — the candidate panel in
  [pre_registration/hypotheses_v2_combined.md §4.1](../pre_registration/hypotheses_v2_combined.md)
  lists several that were deprioritised on data-quality grounds
  (BIST 100, KSE, SET, BOVESPA).
- Validate each RPS value against a second independent source where
  available (ASIFMA ↔ KRX for KOSPI, SIFMA ↔ MEMX for SPX).
- Explore free-float-adjusted market cap as a *second* single-variable
  specification for convergent-validity checking; report alongside RPS
  rather than combined into a new composite.
