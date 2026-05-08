# Peer Review v3: "Direction Heterogeneity and Magnitude Scaling in Cross-Market Entropy–Risk Coupling with Retail Participation"

**Artifact:** [`02_AnonymizedManuscript_v3_4.md`](../02_AnonymizedManuscript_v3_4.md) — 1026 lines, ~16K total words (~7K main text)
**Slug:** `entropy-rps-coupling`
**Review date:** 2026-05-07
**Reviewer protocol:** Feynman skill `peer-review` workflow (`prompts/review.md`)
**Trust level:** Adversarial peer review pre-submission, JFDS-KeAi target
**Previous reviews:** [v1](entropy-rps-coupling-review.md), [v2](entropy-rps-coupling-review-v2.md)
**Evidence file:** [`entropy-rps-coupling-review-v3-evidence.md`](.drafts/entropy-rps-coupling-review-v3-evidence.md)

---

## 1. Summary Assessment

Since v2, the paper has undergone a major restructure (Hybrid C with H1 + H2 co-equal), Cliff's δ has been removed entirely in favour of causal forest DML as the canonical H1 estimator, the appendices have been re-organised along the production workflow (A→B→C→D→E→F→G→H), and a round-7 polish pass has anonymised the pre-registration commit hash, tightened the title and the AI declaration, and fixed §2.4 / Link B duplication. The numerical findings are unchanged and verified against the frozen JSON outputs.

The result is a tighter, more conventionally-shaped JFDS submission with a cleaner central thesis. **The remaining gaps are not about the science — they are about presentation hygiene that a copy-editor or first-round reviewer would catch.** Two issues stand out: local repository paths leaking through ten appendix mentions, and internal review-tracking IDs (`Critical C-3`, `Major M-9`, `Plan v9 Phase 0`) appearing in section headers and table captions. Both are mechanical to fix and should be cleaned up before submission. A third issue — an orphaned `Eq. (6)` with no Eqs. (1)–(5) to anchor it — is a small numbering bug.

**Verdict:** **Accept with minor revision.** Risk-adjusted JFDS-KeAi accept probability: **70–80%** after the cleanup pass below.

---

## 2. Strengths (delta vs v2)

### 2.1 Strengths preserved from v2 review

- Pre-registration discipline (now anonymously archived).
- Byte-for-byte regression assertions with `atol = 1e-4`.
- BH-FDR multiplicity correction across the panel.
- Cascade composite Monte Carlo with phase-aware variance attribution.
- Aleatoric/epistemic decomposition (preserved as §4.4 + Appendix G.2).
- Tier-based primary specification preserved as §4.2.1.

### 2.2 New strengths added since v2

- **Hybrid C structure.** H1 + H2 are co-equal Principal Contributions; magnitude is no longer subordinate to direction. The central thesis is sharper.
- **Causal forest DML canonicalisation.** Appendix F's reconciliation between Linear DML (which fails treatment-balance on three frontier markets) and Causal Forest (which succeeds on all eight) is methodologically transparent and pedagogically useful.
- **Reconciliation table F.4.** Documents how the canonical DML reading corrects the earlier 3-market preliminary report's SPX (raw-means Inverted → DML Paradox) and BTC (thin Paradox → decisive Inverted). A model of honest evolution.
- **Cliff's δ removal.** Eliminates the awkward "three-method convergence" framing; the H1 narrative is now direct: DML-primary + observational reconciliation.
- **Workflow-aligned appendix structure.** Pipeline → Features → Regimes → RPS → Tests → DML → Uncertainty → Exploratory maps cleanly onto the production code, which strengthens the reproducibility claim.
- **§6.6 + §6.7 merge.** AMH and the heterogeneous-effects framework are now one coherent section instead of two overlapping ones.
- **AI Declaration** now follows the JFDS/Elsevier two-sentence template.
- **§2.4 reframed** as "Position of this paper" — eliminates the §1.1/§2.4 research-gap duplication.
- **Title stratification** signals that n = 8 is a tier-stratified panel, not a sample-of-convenience.

---

## 3. Critical Issues

**None.** All v1 and v2 critical issues are addressed (Cliff's δ verified removed, KOSPI cascade correction documented, abstract qualitative-descriptive style adopted, references complete).

---

## 4. Major Issues (cleanup required pre-submission)

### M-1. Local repository paths leak through ten appendix mentions

**Severity:** Major. **Effort:** 30 minutes. **Locations:** App A.2 (line 468), A.4 (476), B.4 (514), B.5 (529), C.5 (597), C.6 (613), D.4 (674), E.2 (696), F.2 (856), F.3 (862), G.3 (962).

**Issue.** The submitted manuscript should be readable independently of the author's local checkout. Constructions like "via `project/validation/h2_eta_squared.py` (frozen output `h2_eta_squared.json`)" leak the directory layout, name internal scripts, and only resolve for someone with the repository clone. They also reveal the project's internal naming conventions (`_cpcv_splitter.py`, `link_b_tests.py`).

**Recommended fix.** Adopt one of two patterns:
- *Pattern A (cleanest):* drop the filename mention entirely. Refer to the routine by its role: "Three alternative variants of SPE_Z standardisation are tested (frozen output preserved in the public repository)."
- *Pattern B (more reproducibility-prominent):* keep a single line in App A.2 stating "All sensitivity tests are computed by the routines listed in Table A.1 of the public repository README" and drop per-section script callouts.

Both patterns rely on the existing public-archive pointer. Pattern A is recommended for body cleanliness.

### M-2. Internal review-tracking IDs in section headers and captions

**Severity:** Major. **Effort:** 15 minutes. **Locations:**

| Line | Header / caption |
|---|---|
| 482 | "(Critical C-3)" in App B intro |
| 512 | "### B.4 SPE_Z standardisation sensitivity (Critical C-3)" |
| 548 | "(Major M-9), and ... (Major M-10)" in App C intro |
| 595 | "### C.5 GMM K-selection per market sensitivity (Major M-9)" |
| 611 | "### C.6 Within-window structural breakpoints (Major M-10)" |
| 670 | "### D.4 PSEI source-classification sensitivity (Major M-6)" |
| 711 | "**Table E.2.** ... (Plan v9 §A.4, Major M-1)" |
| 864 | "**Table F.1.** DML spec variants compared in Plan v9 Phase 0" |
| 931 | "(Major M-5)" in App G intro |
| 960 | "### G.3 SD sensitivity (Major M-5)" |

**Issue.** "Plan v9", "Phase 0", "Critical C-3", "Major M-N" are author-internal review-process artifacts that look unprofessional in a published paper. They reveal the development workflow to reviewers without serving any reader-facing purpose.

**Recommended fix.** Strip the parenthetical IDs from headers and captions. The substantive titles (e.g., "SPE_Z standardisation sensitivity", "GMM K-selection per market sensitivity") stand alone. Also: §A.4 line 476 says "scripts added in the v9 round" — replace "v9 round" with "the post-pre-registration round" or drop the qualifier.

### M-3. Orphaned `Eq. (6)` with no Eqs. (1)–(5)

**Severity:** Major (cosmetic but jarring). **Effort:** 5 minutes. **Location:** Line 152.

**Issue.** Only one main-text equation is numbered: `\tag{6}` on line 152. There are no equations (1)–(5) elsewhere in the body. The numbering is a leftover from an earlier draft where equations existed in the methodology section and were later moved to appendices.

**Recommended fix.** Either renumber to `\tag{1}` (the only main-text equation), or drop the `\tag` entirely (the result is short enough to fit inline with text). Also: the §4.4 variance-decomposition display equation on line 177 is unnumbered, while the formally identical equation in App G.1 is tagged `(G.1)`. If the main-text equation gets a tag, give it `\tag{1}` and the App G.1 version remains `\tag{G.1}` as the formal restatement.

### M-4. N_obs inconsistency between Table 1, Table E.1, and the JSON output

**Severity:** Major (reproducibility). **Effort:** 5 minutes.

**Issue.**
- Paper Table 1 (line 87) and Table E.1 (line 700) both report VNINDEX `N_obs = 1506`.
- Frozen JSON `h2_eta_squared.json` shows VNINDEX `N_obs = 1486`.
- The 20-bar gap is the forward-20-day vol target removing 20 bars from the end of each market series. Table 1 reports the post-504-day-floor N (1506); the H statistic was actually computed on the post-target N (1486).

A reader who runs the public code will not reproduce 1506. This is the kind of thing JFDS reviewers spot-check.

**Recommended fix.** Either (a) report `N_obs = 1486` everywhere to match what was actually used, or (b) add a one-sentence footnote to Table E.1 noting the 20-bar reduction for the forward-vol horizon. Option (a) is cleaner. The same audit applies to all eight markets — recompute the N_obs column in Tables 1 and E.1 from the JSON.

---

## 5. Minor Issues

### m-1. Bibliography typo on line 434

`Sánchez-Fernández, et al., 2025.` — extra comma after the surname is non-standard for Elsevier author-year format. Should be `Sánchez-Fernández et al., 2025.`

### m-2. p-value rounding inconsistency

Eq. (6) line 152 reports `p = 0.0009`; Appendix E.2 line 709 reports `p = 0.001` for the same Spearman correlation. Both round JSON value 0.000936. Pick one rounding rule (3 sig figs preferred for p-values near the threshold).

### m-3. Keywords list slightly long

9 keywords (line 11): "weighted permutation entropy; Gaussian mixture model; Entropy Paradox; heterogeneous treatment effects; causal forest; double machine learning; retail participation; cross-market efficiency; pre-registered validation". JFDS norm is 3–6. Suggest trimming to 5–6: e.g., drop "cross-market efficiency" (covered by "Entropy Paradox") and "double machine learning" (subsumed by "causal forest").

### m-4. Det / Trans / Sto abbreviations not explicitly defined in main text

Used from line 142 onwards without a one-line legend. They are introduced indirectly via §3.3 ("low-entropy (Deterministic), mid-entropy (Transitional), high-entropy (Stochastic)") and Appendix C, but the abbreviated forms are only labeled implicitly by table-column ordering. Add a brief parenthetical at first abbreviated use, e.g., "Det/Trans/Sto" after the §3.3 introduction.

### m-5. Mixed casing of "causal forest"

Mostly "causal forest" (lowercase) in prose, "CausalForestDML" in code/spec contexts. One outlier: Table F.4 caption (line 912) uses "Causal Forest" with title case in a prose sentence. Standardise.

### m-6. Acronym discipline

"DML" is used throughout but not formally expanded at first use until §1.2 line 31 ("double/debiased machine learning") in a parenthetical reference. Earlier mentions (e.g., §1.1) read fine in context, but a JFDS reader who skims the abstract first will hit "DML" in §1.2 PC1 without having seen the expansion. Spell out at first use.

### m-7. §6.1 Link B paragraph is now very long

After the round-7 merge of Link B mechanism + empirical test, the paragraph spans ~250 words in a single block. Readability suffers. Consider splitting at the *Empirical test on the panel.* italic break into two paragraphs while keeping the single Link B header.

### m-8. App E.6 still uses "Plan v9" historical language

Line 820 reads "(7) H1 primary test re-specified to causal forest DML…" — fine — but Table E.2 caption (line 711) still tags "Plan v9 §A.4". Strip per M-2.

---

## 6. Reproducibility and Verification

### 6.1 Numerical claims spot-checked vs frozen JSON outputs

| Claim (manuscript) | JSON value | Match |
|---|---|---|
| ρ(H_raw, tier) = 0.927 | h2_eta_squared.json: 0.9266 | ✓ |
| ρ(η²_raw, tier) = 0.964 | h2_eta_squared.json: 0.9636 | ✓ |
| Cascade ρ_raw mean = +0.847 | h2_cascade.json raw_cascade.mean: 0.8472 | ✓ |
| Cascade ρ_raw 95% CI [+0.786, +0.905] | h2_cascade.json: matches | ✓ |
| SPX CF ATE = +3.48 [+0.92, +6.04] | h1_dml_cpcv.json SPX: ate=3.48, CI=[0.924, 6.038] | ✓ |
| BTC CF ATE = −9.34 [−18.07, −0.61] | h1_dml_cpcv.json BTC: ate=-9.34, CI=[-18.07, -0.61] | ✓ |
| SPX LinearDML ATE = +4.16 [+0.07, +8.25] | h1_dml_cpcv.json SPX linear_dml: ate=4.16, CI=[0.07, 8.25] | ✓ |
| BTC LinearDML ATE = −9.45 [−19.38, +0.49] | h1_dml_cpcv.json BTC linear_dml: ate=-9.45, CI=[-19.38, 0.49] | ✓ |

All verified spot-checks pass. The byte-for-byte regression assertion claim is credible.

### 6.2 Reproducibility infrastructure

- Frozen JSON outputs for all 13 sensitivity + DML scripts present in `project/validation/results_v2/`.
- Random seeds documented (canonical seed = 42).
- Python 3.13 + NumPy / SciPy / pandas / scikit-learn / econml / ruptures listed.
- Pre-registration archive preserved (anonymised reference now points to "the public archive specified on the title page").

### 6.3 Outstanding reproducibility issues

- N_obs inconsistency between paper tables and JSON (M-4).
- Local-path mentions (M-1) — these don't break reproducibility but make the paper reliant on the reader knowing the repo structure.
- Block-bootstrap proxy in Layer 2 of the variance decomposition (preserved from v2 — already disclosed in App G.2's "Computational note").

---

## 7. Inline Annotations

### Title (line 1)
Round-7 update to "Stratified Eight-Market Panel" is a clear improvement over "Eight Markets". ✓

### Abstract (lines 5–9)
Qualitative-descriptive style aligns with JFDS norm. Three-paragraph topic-method-findings structure works. **POLISH:** keyword list (line 11) could trim to 5–6 (m-3).

### §1.2 Contributions (lines 27–33)
2 PC + 2 SC structure is now clean. PC1 sentence introduces "DML" without expansion (m-6); fix on first use.

### §1.3 Methodological commitments (line 37)
Round-7 anonymisation is correct. ✓

### §2.4 Position of this paper (lines 55–57)
Round-7 reframe from "Research gap addressed" works. ✓

### §3.6 Data, analysis window, and computational implementation (line 104)
Already correctly attributes AI code-generation. ✓

### §4.1.1 Causal forest DML (lines 114–131)
Methodological framing is strong. Table 2 is decisive on SPX and BTC; n.s. verdicts on the other six are honest.

### §4.2.1 Tier-based primary specification (lines 148–154)
**MAJOR M-3:** Eq. (6) is orphaned. Renumber or drop the tag.

### §4.4 Aleatoric vs epistemic (lines 173–188)
Variance decomposition equation on line 177 is unnumbered while the same equation in App G.1 is `(G.1)`. Decide a convention.

### §6.1 Link B (lines 257–261)
**MINOR m-7:** post-merge paragraph is long. Consider re-splitting at the italic *Empirical test on the panel.* break.

### §6.6 Heterogeneous-effects + AMH (lines 287–293)
Round-6 merge produced a coherent section. ✓

### §7.2 Conclusion (line 312)
Clean two-paragraph wrap. ✓

### Appendix A (lines 458–478)
**MAJOR M-1, M-2:** local paths in §A.2, §A.4; "v9 round" wording in §A.4.

### Appendix B (lines 480–542)
**MAJOR M-1, M-2:** local paths in §B.4, §B.5; "Critical C-3" tags in §B intro and §B.4 header.

### Appendix C (lines 546–628)
**MAJOR M-1, M-2:** local paths in §C.5, §C.6; "Major M-9", "Major M-10" tags.

### Appendix D (lines 632–682)
**MAJOR M-1, M-2:** local path in §D.4; "Major M-6" tag.

### Appendix E (lines 686–824)
**MAJOR M-1, M-2:** local path in §E.2 Table caption; "Plan v9 §A.4, Major M-1" in Table E.2 caption.
**MAJOR M-4:** N_obs column matches main-text Table 1 but not the JSON output.

### Appendix F (lines 828–925)
**MAJOR M-1, M-2:** local path in §F.2 specification, §F.3 outputs note; "Plan v9 Phase 0" in Table F.1 caption.
**MINOR m-5:** "Causal Forest DML" title casing in Table F.4 caption.

### Appendix G (lines 929–971)
**MAJOR M-1, M-2:** local path in §G.3 Table caption; "Major M-5" tags in §G intro and §G.3 header.

### Appendix H (lines 975–1022)
Clean. Properly labelled exploratory. ✓

### References (lines 336–454)
**MINOR m-1:** Sánchez-Fernández bibliography entry has stray comma after surname.

### Declaration of generative AI (line 330)
Round-7 rewrite to JFDS/Elsevier template. ✓

---

## 8. Recommendation

### Verdict: **Accept with minor revision** (no science changes; cleanup only)

Concrete pre-submission cleanup list (estimated 60–90 minutes total):

1. **M-1 — Local-path purge** (30 min). Drop `project/validation/...` mentions in 10 appendix locations. Refer to scripts by role; rely on the public-archive pointer for replication.
2. **M-2 — Strip internal review-tracking IDs** (15 min). Remove "(Critical C-3)", "(Major M-N)", "Plan v9 …" from headers and table captions in App B, C, D, E, F, G.
3. **M-3 — Fix Eq. (6) numbering** (5 min). Renumber to `(1)` or drop the tag. Decide on a convention for the §4.4 vs App G.1 equation.
4. **M-4 — Resolve N_obs discrepancy** (5 min). Recompute the N_obs column in Tables 1 and E.1 from the JSON, or add a footnote noting the forward-vol-horizon reduction.
5. **m-1, m-2, m-3, m-5, m-6, m-7** — minor polish per §5 (15 min total).

After cleanup, the paper is **ready for JFDS submission**. No further substantive revision is required.

### Risk-adjusted accept probability

| Venue | Tier | IF | Fit | Estimate |
|---|---|---|---|---|
| **JFDS-KeAi** (target) | Q1 | 3.9 | 9.5/10 | **70–80%** post-cleanup |
| Quantitative Finance (T&F) | Q1 | 1.7 | 9/10 | 60–70% |
| Annals of Applied Statistics | Q1 | 1.5 | 8/10 | 50–60% |

Hybrid C + DML canonicalisation + workflow appendix = a competitive submission. The cleanup items above are mechanical, not substantive.

---

## 9. Sources

- Manuscript: [`02_AnonymizedManuscript_v3_4.md`](../02_AnonymizedManuscript_v3_4.md) (1026 lines, post-round-7 fixes)
- Cover-letter snapshot: [`02_AnonymizedManuscript_FULL_for_cover_letter.md`](../02_AnonymizedManuscript_FULL_for_cover_letter.md) (verified byte-identical body)
- Frozen JSON outputs verified: `h2_eta_squared.json`, `h2_cascade.json`, `h1_dml_cpcv.json`
- Plan file: [`vi-c-mirror-sang-c-velvet-walrus.md`](../../C:/Users/Administrator/.claude/plans/vi-c-mirror-sang-c-velvet-walrus.md)
- Previous reviews: [v1](entropy-rps-coupling-review.md), [v2](entropy-rps-coupling-review-v2.md)
- Evidence notes: [`entropy-rps-coupling-review-v3-evidence.md`](.drafts/entropy-rps-coupling-review-v3-evidence.md)
