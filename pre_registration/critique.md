# Pre-Registration Scientific-Foundation Audit (H1–H5)

**Subject**: [hypotheses_v2_combined.md](hypotheses_v2_combined.md),
committed at `b130b0f` (2026-04-18).
**Audit date**: 2026-04-19.
**Audit tag**: `v2.1.3-prereg-audit`.

## 0. Purpose and scope

The §9 (H1) and §10 (H3/H4/H5) reassessments in
[paper_v2_1_combined_summary.md](../paper_artifacts/paper_v2_1_combined_summary.md)
upgraded the **numerical rigor** of the validation — block bootstrap
CIs, pairwise Mann-Whitney, Cliff's δ, BH-FDR, block-permutation,
horizon sweeps. Those upgrades implicitly assumed the underlying
pre-registered hypotheses were themselves well-posed.

This document audits that assumption. A pre-registration is
scientifically protective only if:

- Its falsification conditions correspond to the claim being tested.
- Its thresholds are derived from prior reasoning, not from in-sample
  data.
- Its statistical operators match its claims (omnibus vs pairwise,
  directional vs two-sided).
- Its panel is fixed ex-ante and adequately powered.
- Its primary instruments do not carry uncontrolled researcher degrees
  of freedom.
- The code executing the test exists at pre-reg time.

Each hypothesis is audited against these criteria. Every issue is
tagged with one of three remediation categories:

- **[Addressed]** — already handled in §9 or §10 via post-hoc rigor.
- **[Disclose]** — cannot be remediated after the fact; must be named
  honestly in the paper.
- **[v3-needed]** — a future v3 pre-registration should fix this
  upstream; not actionable in v2.1.

**What this audit does NOT claim.** It does not argue the results are
wrong. H1 and H4 survive all identified gaps. H2's swap is honest.
H3 and H5 require softened claims in the paper's abstract — that is
the scope of the downstream correction. The numeric outputs are not
re-run.

---

## 1. H1 — Direction hypothesis

> Pre-reg text: "Kruskal-Wallis H for regime discrimination of forward
> 20-day realized volatility is statistically significant (p < 0.05)
> AND mean(Deterministic fwd vol) > mean(Stochastic fwd vol)."
>
> Falsification: "frontier H < 20 OR direction inverted, OR developed
> H > 50 with correct direction."

### 1.1 Operator mismatch — KW omnibus does not test direction **[Addressed]**

Kruskal-Wallis tests whether *any* of the three regimes differs in
distribution. It does not test the specific pairwise claim
"Det > Sto". The pre-reg added a ranked-mean direction check alongside
KW to cover this, but that check is itself untested (see 1.5).

§9 added Mann-Whitney one-sided Det-vs-Sto with Cliff's δ effect size
and BH-FDR. The pairwise claim is now testable. The pre-reg's own
operator, however, did not match its own claim.

### 1.2 H-stat magnitude thresholds are not effect sizes **[Disclose]**

The falsification uses fixed H-magnitude thresholds ("H > 100 on
frontier", "H < 20 on developed"). KW H scales with sample size: for
a given true effect, doubling n roughly doubles H. The 8-market panel
has heterogeneous n:

- VNINDEX post-2020: ~1500 trading bars.
- PSEI post-2020: ~1500 trading bars (similar calendar).
- BTC post-2020: ~2200 bars (7-day calendar).
- SPX, FTSE, NIKKEI: ~1500 bars each.

A fixed H threshold across markets with different n conflates effect
size with sample size. An effect-size threshold (e.g. ε² ≥ 0.05 or
Cliff's δ ≥ 0.3) would have been correct. §9 reports ε² and δ but
cannot retroactively change the falsification rule.

### 1.3 Asymmetric falsification under-argued **[Disclose]**

"Developed H > 50 with correct direction REJECTs H1" is defensible —
if the effect were universal, microstructure would not be the
mechanism. But why 50 rather than 25 or 75? The pre-reg gives no
derivation. A sceptical reviewer should note: this threshold sits in
the range where a direction-positive result could be argued either way,
and was selected without ex-ante justification.

### 1.4 No multiplicity correction pre-specified **[Addressed]**

The pre-reg tests 8 markets on a shared hypothesis but specifies no
family-wise correction. §9 added BH-FDR across the 8-market panel.

### 1.5 Inversion declared by ranked-mean difference **[Disclose]**

"Mean(Sto) ≥ mean(Det)" is the direction-inversion criterion. No
significance test guards this comparison. NIFTY's "Inverted" label in
§4 Phase 1 is assigned by ranked-mean difference alone. Under a proper
pairwise test NIFTY might or might not meet a significance bar for
inversion — the pre-reg does not commit to either. §9's Mann-Whitney
provides the test post-hoc.

**Net for H1**: Survives the audit. Two issues [Addressed], three
[Disclose]. No claim softening required in the abstract; §9's rigor
upgrade is sufficient provided the post-hoc nature of the pairwise
test is flagged.

---

## 2. H2 — Microstructure ordering

> Pre-reg text: "Kruskal-Wallis H-statistic correlates positively
> (Spearman r > 0.5) with an a priori microstructure index:
> MS_index = 0.4 * circuit_breaker + 0.3 * (1 - institutional_share)
> + 0.3 * (1 - log(market_cap_usd))"
>
> Falsification: "Spearman correlation has p-value > 0.10."

### 2.1 Composite weights are an uncontrolled degree of freedom **[Addressed — but disclose the swap]**

The 0.4 / 0.3 / 0.3 weights were authors' qualitative judgement.
Varying them changes the composite's ranking and therefore ρ. With no
prior derivation, no cross-validation, and no benchmarking against
alternative weightings, the composite ρ carries weight-choice as a
hidden researcher degree of freedom.

The RPS swap in
[rps_rationale.md §2.1](../paper_artifacts/rps_rationale.md) addresses
this by replacing the composite with a single-variable proxy (share of
trading value by retail accounts). The swap is post-hoc but went to a
*weaker* headline number (ρ=0.754 vs composite ρ=0.952) — an act
*against* author self-interest — which partially mitigates the HARKing
concern. Disclose the sequence explicitly in the paper.

### 2.2 Unit incompatibility **[Addressed by swap]**

The composite mixes `{0, 1}` (circuit breaker), `[0, 1]`
(institutional share complement), and `log(USD)` (market cap). Linear
combination without standardization produces a scalar whose magnitude
has no interpretable meaning. The Spearman rank is scale-free so this
did not bias ρ directly, but the composite should never have been
reported as a real-valued measurement. Same remediation as 2.1.

### 2.3 Redundant and inconsistent thresholds **[Disclose]**

"Spearman ρ > 0.5 AND p < 0.10" at n=8. At n=8, rejecting ρ = 0 at
p = 0.10 (one-sided) requires |ρ| ≳ 0.64. The ρ > 0.5 bar is therefore
*looser* than the p-value bar; both gates are nominally "AND"-ed, but
only the p-bar binds. The pre-reg specified a redundant condition
without noticing. Does not invalidate the result (RPS ρ = 0.754 clears
both), but reveals that the thresholds were not jointly reasoned.

### 2.4 No power analysis **[Disclose / v3-needed]**

n = 8 Spearman has low power to distinguish ρ = 0.5 from ρ = 0. Under
H0, Spearman at n = 8 yields p = 0.10 at |ρ| ≈ 0.64; the CI at the
observed ρ = 0.754 is [0.09, 0.99] (§9). The pre-reg committed to a
low-power design without declaring this. Future v3 pre-reg should
include either a power analysis or a minimum-panel-size commitment.

### 2.5 Post-hoc specification swap erodes pre-reg protection **[Disclose]**

Even a specification swap *against* self-interest is still a post-hoc
change. A strict pre-reg reading says: the pre-registered instrument
was the composite, and its ρ = 0.952 is what pre-reg protects. RPS is
post-hoc evidence, not pre-registered evidence. The paper treats RPS
as primary, which is the honest scientific choice but not the
pre-reg-compliant choice. Disclose both readings.

**Net for H2**: The primary instrument was swapped post-hoc. The
result survives on the swapped instrument, but the pre-reg protection
is weakened. The paper's abstract and §4 should name the swap at first
mention.

---

## 3. H3 — Persistence

> Pre-reg text: "Under identical hysteresis parameterization, p(Transitional)
> correlates inversely with developed-market microstructure. Specifically:
> frontier markets show p(Transitional) > 0.55; developed markets show
> p(Transitional) < 0.50; difference is > 10 percentage points."
>
> Falsification: "any frontier market shows p(Transitional) < 0.45 OR
> any developed market shows p(Transitional) > 0.60."

### 3.1 Thresholds suspiciously close to VNINDEX in-sample p_tra **[Disclose]**

VNINDEX's paper-v2 post-2020 p_tra with the pre-reg hysteresis
calibration was ≈ 0.45–0.55 — the calibration target was the 4–10
flips-per-year band on VNINDEX, which mechanically produces p_tra in
that range. "Frontier > 0.55" and "Frontier fail < 0.45" both sit
inside or immediately adjacent to VNINDEX's own observed band.

A sceptical reader cannot rule out that the thresholds were chosen to
fit VNINDEX's observed number. This is *threshold*-HARKing — choosing
the falsification bar using data you have already observed. Even if
the author intent was principled, the evidentiary value of the
threshold is reduced.

§10's continuous Spearman(p_tra, RPS) partially addresses this by
removing the categorical bar, but does not retroactively justify the
original threshold choice.

### 3.2 Panel asymmetry — emerging and crypto not falsifiable **[Disclose]**

The H3 falsification rule applies only to frontier and developed
markets. Emerging (KOSPI, NIFTY) and Crypto (BTC) are measured but
their p_tra values cannot falsify H3 under the pre-reg rule. If H3's
real claim is "p_tra tracks microstructure", why include markets that
cannot contribute to its verdict?

This is a specification gap. The continuous Spearman in §10 remediates
by making all 8 markets informative on the relationship.

### 3.3 Small-n categorical test **[Disclose]**

2 frontier × 3 developed = 5 markets entering H3's verdict, against
binary thresholds. Any single borderline p_tra flips the pass/fail.
The actual first-run result (VNINDEX 0.451, PSEI 0.403) puts two of
the two frontier markets within a few percentage points of the 0.45
falsification boundary — exactly the configuration where low
statistical discipline dominates.

### 3.4 Scripts added post-b130b0f **[Disclose]**

`hysteresis_cross_market_v2.py` did not exist at pre-reg commit. The
pre-reg committed the verdict language but not the code that would
execute it. This is already disclosed in
[prereg_b130b0f/README.md](../validation/results_v2/prereg_b130b0f/README.md)
H3/H4/H5 addendum. Name it here for completeness.

**Net for H3**: The pre-reg's categorical rule was vulnerable on
thresholds, panel composition, and statistical discipline. §10's
continuous companion is a partial remediation. Paper abstract should
soften "Transitional Dominance holds on frontier markets" to "p_tra is
elevated on high-RPS markets and sits near the pre-reg 0.45–0.55 band
on VNINDEX/PSEI; continuous companion ρ = 0.56, p = 0.15
(underpowered)."

---

## 4. H4 — Temporal structure (shuffle test)

> Pre-reg text: "Across all markets tested, observed filtered flip
> rate < 5th percentile of shuffled-null distribution (10,000
> permutations, p < 0.01)."
>
> Falsification: "any market's observed flip rate falls within null
> 5th–95th percentile band."

### 4.1 Internal threshold inconsistency **[Disclose]**

"Observed < 5th percentile" corresponds to one-sided p < 0.05, not
p < 0.01. The two bars are inconsistent as written. The falsification
rule (5th–95th band) is two-sided at p = 0.10. The actual script
reports a point p-value and all 8 markets give p ≈ 0, so the
inconsistency does not change the verdict — but it reveals the pre-reg
was not proof-read.

### 4.2 Null specification is structurally weak **[Disclose / v3-needed]**

This is the most substantive H4 concern. Simple random permutation of
*hysteresis-filtered* labels is near-tautological:

- Hysteresis with t_persist = 8 mechanically produces long runs of
  constant label. Any such filtered sequence has a very low flip rate
  by construction.
- Random permutation of the filtered sequence destroys the runs,
  yielding a flip rate far above the filtered observed. The null-mean
  flip rate under simple shuffle is ~35–42/yr on the 8-market panel
  (§10.4.3), vs observed 7–15/yr — but the observed is *low by
  construction of the filter*, not because the underlying regime
  sequence is unusually structured.

A valid shuffle null would permute the *raw GMM argmax labels* (before
hysteresis) and then apply the same hysteresis filter to each shuffled
realisation. That null tests whether the filtered flip rate on real
data is lower than on random-regime data — a meaningful claim.

§10's block-permutation variant at blocks {5, 10, 20} improves on
simple shuffle by preserving short-range structure, but still permutes
filtered labels rather than raw labels-then-filter. The fundamental
null design gap remains. Disclose honestly: passing H4 confirms
filtering is non-trivial, not that regimes are temporally structured
beyond what filtering imposes. A v3 pre-reg should specify
permute-raw-then-filter.

### 4.3 No multiplicity correction **[Addressed]**

§10 added BH-FDR across the 8-market panel; all q-values are 0.

### 4.4 Scripts added post-b130b0f **[Disclose]**

Same as 3.4.

**Net for H4**: Passes the pre-reg but passes trivially. The
underlying claim ("regimes are temporally structured") is not what H4
actually tests. The paper's §4 "STRUCTURED on all 8 markets" headline
is technically correct under the pre-reg rule but overstates the
scientific content. Disclose in §11.

---

## 5. H5 — Parameter robustness

> Pre-reg text: "Across all markets tested, p(Transitional) spread
> across three hysteresis configurations (A production, B looser,
> C tighter) is less than 5 percentage points per market."
>
> Falsification: "any market shows p(Transitional) spread > 7
> percentage points across configurations."

### 5.1 Dead zone 5–7 pp in falsification rule **[Disclose]**

PASS = spread < 5 pp. REJECT = spread > 7 pp. Spreads in [5, 7] pp
have no assigned verdict. PSEI's 5.6 pp falls in this dead zone. Poor
falsification design.

### 5.2 Threshold mismatch bug between pre-reg and code **[Disclose + §4 correction]**

This is the audit's most consequential finding. The pre-reg rule is
REJECT iff spread > 7 pp. But `hysteresis_robustness_v2.csv`'s
`H5_verdict` column and the paper's §4 Phase 2b table both apply
*REJECT iff spread > 5 pp* (the PASS bar, not the REJECT bar).

Under the pre-reg's own rule the correct verdicts are:

| Market  | Spread (pp) | Pre-reg rule verdict |
|---------|-------------|-----------------------|
| NIKKEI  | 2.0         | **PASS** |
| BTC     | 2.7         | **PASS** |
| VNINDEX | 3.4         | **PASS** |
| PSEI    | 5.6         | **Dead zone** (5 < spread < 7) |
| KOSPI   | 7.2         | **REJECT** |
| NIFTY   | 7.7         | **REJECT** |
| SPX     | 9.0         | **REJECT** |
| FTSE    | 9.5         | **REJECT** |

Under the paper's applied rule (>5 pp REJECT): 3 PASS, 5 REJECT.
Under the pre-reg rule (>7 pp REJECT): 3 PASS, 1 dead zone, 4 REJECT.

The §4 correction follows: the pre-reg is what pre-registered.
Reinterpret §4 Phase 2b under the >7 pp rule. Spread numbers are
correct; only the verdict column is re-mapped. No code re-run required.
This is a narrative correction, not a re-analysis.

### 5.3 5-pp PASS bar calibrated on VNINDEX's 2.7 pp T4 result **[Disclose]**

The T4 VNINDEX result (2.7 pp spread, paper v2) predates the
pre-registration. Choosing 5 pp as the PASS bar with T4's 2.7 pp in
hand is borderline threshold-HARKing. The 7 pp REJECT bar is similarly
pinned — why 7 rather than 6 or 10? No derivation.

### 5.4 Perturbation magnitudes have no effect-size derivation **[Disclose / v3-needed]**

Configs B and C perturb δ_hard by ±0.10, δ_soft by ±0.05, t_persist by
±2 bars. The magnitudes have no prior justification. A larger
perturbation (say ±0.20) would plausibly blow up spreads on all
markets; a smaller (±0.05) would compress them. The choice of
perturbation magnitude is itself a researcher degree of freedom
determining how hard the robustness test is. A v3 pre-reg should
derive perturbation magnitudes from the calibration sensitivity (e.g.
the FWHM of the hysteresis tuning curve around the production
calibration).

### 5.5 Scripts added post-b130b0f **[Disclose]**

Same as 3.4.

**Net for H5**: Pre-reg rule has a dead zone, a threshold-mismatch
bug in the paper, and calibration-circular thresholds. Under the
correct rule, 4/8 reject (not 5/8), with PSEI in dead zone. §10's
bootstrap CIs show no rejection is decisive at 95 %; only NIKKEI is
PASS_DECISIVE. Paper abstract must soften and §4 must be corrected.

---

## 6. Meta-level issues

### 6.1 Flexible panel composition **[Disclose]**

Pre-reg text: "Frontier: VNINDEX, KSE 100 or SET, PSEi (choose 2 of 3
by data quality). Emerging: ... Developed: ..." The final panel was
not declared ex-ante; "choose 2 of 3 by data quality" leaves room for
post-data inspection. The actual panel (VNINDEX, PSEI, KOSPI, NIFTY,
SPX, FTSE, NIKKEI, BTC) was reasonable, but a strict pre-reg would
have frozen the selection before data was pulled.

### 6.2 No power analyses anywhere **[v3-needed]**

None of H1–H5 commits to a minimum detectable effect size or a power
calculation at the declared n = 8. The low-power nature of
Spearman-at-n=8 (H2 continuous, H3 continuous) is only visible in
the post-hoc CIs.

### 6.3 Hysteresis calibration upstream of pre-reg **[Disclose]**

δ_hard = 0.60, δ_soft = 0.35, t_persist = 8 were calibrated on VNINDEX
post-2020 (`scripts/calibrate_hysteresis.py`, target 4–10 flips/yr).
The calibration is a researcher degree of freedom that propagates into
H3, H4, and H5's operational definitions. The other 7 markets are OOS
on this calibration (a good property); VNINDEX is *in-sample* on it
(a threshold-HARKing adjacent property for H3's categorical bar).

### 6.4 H3/H4/H5 scripts did not exist at pre-reg commit **[Disclose]**

At commit b130b0f, the repo tree contained only H1/H2 cross-market
code (`cross_market_v2.py` and its pre-refactor form). The three
hysteresis scripts were written after the pre-reg. The pre-reg
therefore commits the hypothesis language for H3/H4/H5 but not the
executable test code. Under strict pre-reg discipline, a future v3
should commit both.

---

## 7. Remediation summary

| # | Issue | Hypothesis | Category | Action |
|---|---|---|---|---|
| 1.1 | KW omnibus vs directional claim | H1 | Addressed | §9 Mann-Whitney + δ |
| 1.2 | H-stat magnitude is not effect size | H1 | Disclose | §11 |
| 1.3 | Developed H>50 threshold under-argued | H1 | Disclose | §11 |
| 1.4 | No multiplicity correction | H1 | Addressed | §9 BH-FDR |
| 1.5 | Inversion by ranked mean, no test | H1 | Disclose | §11 |
| 2.1 | Composite weights uncontrolled DoF | H2 | Addressed (swap) | rps_rationale §2.1 + §11 |
| 2.2 | Unit incompatibility | H2 | Addressed (swap) | rps_rationale §2.1 |
| 2.3 | Redundant ρ-and-p thresholds | H2 | Disclose | §11 |
| 2.4 | No power analysis | H2 | Disclose / v3 | §11 |
| 2.5 | Post-hoc swap erodes pre-reg | H2 | Disclose | Abstract + §4 Phase 1 + §11 |
| 3.1 | Thresholds close to VNINDEX in-sample | H3 | Disclose | §11 |
| 3.2 | Emerging/Crypto not falsifiable | H3 | Disclose | §11 |
| 3.3 | Small-n categorical test | H3 | Disclose | §11 |
| 3.4 | Script post-b130b0f | H3 | Disclose | §11 (already in archive README) |
| 4.1 | 5th-%ile vs p<0.01 inconsistency | H4 | Disclose | §11 |
| 4.2 | Shuffle null near-tautological | H4 | Disclose / v3 | §11 |
| 4.3 | No multiplicity correction | H4 | Addressed | §10 BH-FDR |
| 4.4 | Script post-b130b0f | H4 | Disclose | §11 |
| 5.1 | 5–7 pp dead zone | H5 | Disclose | §11 |
| 5.2 | Paper applied 5-pp REJECT, pre-reg says 7-pp | H5 | Correction | §4 Phase 2b re-map + §11 |
| 5.3 | 5-pp bar calibrated on T4 | H5 | Disclose | §11 |
| 5.4 | Perturbation magnitudes undeferred | H5 | Disclose / v3 | §11 |
| 5.5 | Script post-b130b0f | H5 | Disclose | §11 |
| 6.1 | Flexible panel composition | Meta | Disclose | §11 |
| 6.2 | No power analyses | Meta | v3-needed | §11 |
| 6.3 | Hysteresis calibration upstream | Meta | Disclose | §11 |
| 6.4 | H3/H4/H5 scripts post-b130b0f | Meta | Disclose | §11 |

Category counts: Addressed = 5, Disclose = 18, v3-needed = 4,
Correction (§4 re-map) = 1.

---

## 8. What this audit does and does NOT invalidate

### Does NOT invalidate

- **H1 results.** KW passes on frontier, fails on developed, direction
  consistent with paradox. §9's pairwise Mann-Whitney and Cliff's δ
  give post-hoc support to the directional claim the pre-reg's operator
  did not test. H1 survives.
- **H2 results, under the swapped instrument.** ρ(H, RPS) = 0.754 with
  95 % CI [0.09, 0.99] and MC-robust to RPS ± 0.05. The result is honest
  — but it is on a post-hoc instrument, not the pre-registered one.
- **H4 results.** All 8 markets give p ≈ 0 under simple shuffle and
  block-permutation at {5, 10, 20}. Pre-reg passes. The scientific
  content of the pass is narrower than the pre-reg language suggests
  (see 4.2).
- **The Entropy Paradox itself.** The sign-reversal on frontier vs
  developed is observable in every version of the analysis.

### DOES invalidate or soften

- **H3 as stated.** Frontier Transitional Dominance as a binary
  threshold claim (p_tra > 0.55) is not supported: VNINDEX 0.451 and
  PSEI 0.403 both sit at or below the 0.55 bar and near the 0.45
  falsification boundary. §10's continuous companion (ρ = 0.56,
  p = 0.15) is suggestive but underpowered. The paper must soften to
  "p_tra is elevated on high-RPS markets without meeting the
  pre-registered categorical bars on VNINDEX or PSEI."
- **H5 verdict count.** Under the pre-reg's own >7 pp REJECT rule,
  4/8 markets reject (not 5/8). PSEI (5.6 pp) is in the 5–7 pp dead
  zone. §4 Phase 2b must be corrected.
- **H2's pre-reg protection.** The composite instrument was swapped
  post-hoc. The replacement is honest and went against author
  self-interest, but strict pre-reg protection applies to the composite
  only. Disclose at first mention.

---

## 9. Recommended v3 pre-registration checklist (future work)

Not committed to in v2.1 — the checklist is a forward-looking note so
future work does not repeat the same gaps.

1. **Freeze the panel ex-ante.** Name the 8 markets; do not leave
   "choose 2 of 3" flexibility.
2. **Commit the test code at pre-reg time.** Every hypothesis must
   have its executable script in the pre-reg commit tree.
3. **Specify effect-size thresholds, not magnitude thresholds.** Use
   ε², Cliff's δ, or CI-relative bars instead of raw KW H values.
4. **Declare power analyses.** Report the minimum detectable effect
   at the declared n.
5. **Derive thresholds from prior evidence, not in-sample
   calibration.** If VNINDEX T4 informed the perturbation magnitudes,
   either exclude VNINDEX from the pre-reg test or derive thresholds
   independently.
6. **Match operators to claims.** Directional claims require one-sided
   pairwise tests; "persistence" claims require CI-bounded point
   estimates, not binary thresholds.
7. **Specify multiplicity correction ex-ante.** BH-FDR or Bonferroni
   should be named, not added post-hoc.
8. **Close falsification dead zones.** Every observable value must map
   to PASS or REJECT; no middle band.
9. **Specify nulls that test the claim.** For H4, permute raw labels
   then filter, not filtered labels.
10. **Name all researcher degrees of freedom.** Weights, perturbation
    magnitudes, calibration windows — each must be declared and
    justified.

---

## 10. Audit conclusion

The pre-registration committed at b130b0f was a good-faith effort that
contains 23 identifiable scientific-foundation issues, 5 of which are
already addressed by §9/§10 post-hoc rigor, 18 require honest
disclosure in the paper, 4 are genuinely remediable only by a future
v3 pre-reg, and 1 is a narrative correction (H5 threshold mapping).

The validation results themselves are not wrong. What the audit
identifies is that **pre-registration discipline is thinner than the
paper's confident language suggests**. H1 and H4 survive. H2's
instrument was swapped; the swap is honest. H3 and H5 fail or
partially fail under their own rules and require softened abstract
claims.

This document is the scholarly record of that audit. §11 in the paper
summary is its public-facing distillation.

---

## Provenance

- **Audit authored**: 2026-04-19.
- **Audit tag**: `v2.1.3-prereg-audit`.
- **Referenced artifacts**:
  [hypotheses_v2_combined.md](hypotheses_v2_combined.md),
  [paper_v2_1_combined_summary.md §9–§10](../paper_artifacts/paper_v2_1_combined_summary.md),
  [rps_rationale.md](../paper_artifacts/rps_rationale.md),
  [prereg_b130b0f/README.md](../validation/results_v2/prereg_b130b0f/README.md),
  [hysteresis_robustness_v2.csv](../validation/results_v2/hysteresis_robustness_v2.csv).
