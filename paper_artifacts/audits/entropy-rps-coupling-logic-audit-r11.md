# Logic + Coherence Audit (Round 11)

**Artifact:** [`02_AnonymizedManuscript_v3_4.md`](../02_AnonymizedManuscript_v3_4.md) — post-round-10
**Audit date:** 2026-05-08
**Scope:** narrative flow, claim-evidence consistency, cross-reference integrity, vague claims, orphaned sentences

---

## Major issues (4)

### M-1. Factual error: "four orders of magnitude" overstates the H range
**Location:** §4.2 line 139 — "Per-market H spans four orders of magnitude and groups cleanly by tier"
**Issue:** Actual H_raw range from Table E.1: 2.12 (SPX) to 83.90 (VNINDEX) = ~40× = ~1.6 orders of magnitude. Filtered: 1.34 to 96.33 = ~72× = ~1.86 orders. "Four orders of magnitude" would imply 10,000× — off by a factor of ~140.
**Fix:** "spans nearly two orders of magnitude" or just "varies by an order of magnitude".

### M-2. §5 intro outdated: claims H1 sole "central finding"
**Location:** §5 line 219 — "H1 (per-market direction, the Paradox / Inverted dichotomy) is the central finding reported in §4.1."
**Issue:** Inherited from earlier draft when H1 was sole Principal Contribution. Post-Hybrid C, H1 + H2 are co-equal Principal Contributions per §1.2. The §5 intro contradicts §1.2 + §7.2 which both treat H1 + H2 as the two central findings.
**Fix:** "H1 (per-market direction) and H2 (cross-market magnitude) are the central findings reported in §4.1 and §4.2."

### M-3. Wrong cross-reference: "(§4.1.2)" for DML methodology study
**Locations:**
- §4.6 line 213: "The DML methodology study (§4.1.2 and Appendix F)"
- §6.3 line 268: "The DML methodology study (§4.1.2)"
- §6.6 line 286: "(§4.1.2 details the splitter; Appendix F covers the spec grid)"

**Issue:** §4.1.2 is "Reconciliation with the earlier 3-market observational study" — it does NOT contain the DML methodology study. The canonical DML specification is established in **§4.1.1**, and the spec grid lives in Appendix F.3. The §4.1.2 cross-reference points at a section that discusses preliminary-vs-final reconciliation, not the methodology study being cited.
**Fix:** Replace §4.1.2 → §4.1.1 in all three places (or just point to Appendix F directly when the spec grid is the actual referent).

### M-4. Confused H1/H2 scope claim in §4.5 structural-breaks bullet
**Location:** §4.5 line 201 — "The H1 and H2 findings rely on cross-market ordering rather than within-market temporal stability and are robust to the within-window break structure"
**Issue:** §4.5 is in §4.2 H2's robustness suite — H2 is the cross-market test that legitimately depends on cross-market ordering. **H1 is a per-market direction test that DOES depend on within-market temporal structure** — saying H1 "relies on cross-market ordering" is incorrect. The bullet was migrated from the deleted §5.3 in round 8 and the scope claim wasn't updated for the new location.
**Fix:** Restrict to H2: "The H2 cross-market ordering finding is robust to the within-window break structure (Appendix C.6); within-window break sensitivity for H1 per-market direction is recorded as a future-work item."

---

## Minor issues (6)

### m-1. §5 intro wrong appendix pointer
**Location:** §5 line 219 — "Per-market detail appears in Appendices D and E."
**Issue:** §5 covers H3 (App E.3), H4 (E.4), H5 (E.5). App D is RPS specification — not relevant to §5's H3/H4/H5. The "D and E" pointer is wrong.
**Fix:** "Per-market detail appears in Appendix E."

### m-2. Terminology inconsistency: "template" vs "methodological exemplar"
**Locations:**
- §6.6 line 288: "the methodology adopted here is offered as a template"
- §7.2 line 311: "as a methodological exemplar"

**Issue:** Round 8 (item #4) softened §7.2 from "template" to "methodological exemplar" — §6.6 was missed and still says "template". Reader will notice the inconsistency.
**Fix:** §6.6 → "the methodology adopted here is offered as a methodological exemplar". (Or accept "template" as colloquial in §6.6 and stay precise in §7.2; preferred: align both to "exemplar".)

### m-3. Vague jargon: "first-order" vs "second-order property"
**Location:** §4.3 line 171 — "Magnitude scaling is therefore a second-order property of regime separability, while direction is a first-order property of regime semantics."
**Issue:** "First-order" and "second-order" are borrowed metaphorically from physics/math without explicit definition. A reader unfamiliar with this metaphorical use may parse it as "primary vs secondary" (which doesn't fit since both are co-equal Principal Contributions) or as a specific mathematical claim. The terms are doing rhetorical lifting without semantic anchoring.
**Fix:** Reframe in concrete language: "Magnitude scaling is a property of regime *separability* (how cleanly the regimes split); direction is a property of regime *semantics* (which regime is dangerous). Both are observed simultaneously and address different questions."

### m-4. Orphaned sentence in §5.1
**Location:** §5.1 line 223 — final sentence "The Transitional regime is dominant on 6 of 8 markets after filtering."
**Issue:** This factual claim about p_trans dominance is dropped at the end of the H3 paragraph without obvious connection to the preceding REJECT discussion. The reader doesn't know why it's mentioned — is it support for, against, or independent of the H3 rejection? Reads as orphaned.
**Fix:** Either remove (the fact is in App E.3 Table E.6) or contextualise: "Despite the H3 categorical rejection, the Transitional regime is dominant on 6 of 8 markets after filtering — the regime composition pattern is broadly consistent with the H3 prediction; only the categorical-threshold specification fails."

### m-5. Vague claim: "improves signal quality"
**Location:** §4.6 line 213 — "the filter improves signal quality rather than merely smoothing"
**Issue:** "Improves signal quality" is unspecific compared to the preceding concrete "removes label-flicker artifacts". The contrast "rather than merely smoothing" works only if the reader has already accepted "improves signal quality" as a meaningful claim.
**Fix:** Replace "improves signal quality" with a concrete consequence: "the filter removes label-flicker artifacts that confound naive estimation rather than merely averaging adjacent labels." (Or drop the redundant trailing phrase entirely — the preceding sentence already established the substantive claim.)

### m-6. Three frameworks mentioned, relationships not explicit
**Locations:** §6.2 (continuous-efficiency programme), §6.6 paragraph 1 (Adaptive Market Hypothesis, Lo 2004), §6.6 paragraph 2 (heterogeneous-effects framework, Wager–Athey 2018)
**Issue:** Three theoretical positionings appear across §6 without an explicit statement of how they relate. The reader could plausibly ask: are these complementary (paper sits at the intersection)? Hierarchical (AMH is the meta-frame, heterogeneous-effects is the methodological operationalisation, continuous-efficiency programme is the closest empirical predecessor)? Redundant (one would suffice)?
**Fix (light):** Add one sentence to the §6.6 opening that clarifies the hierarchy: "AMH (Lo, 2004) provides the meta-theoretical framing; the heterogeneous-effects framework (Wager and Athey, 2018) is its methodological operationalisation; the continuous-efficiency programme (§6.2) is the closest empirical predecessor."
**Alternative (heavier):** Open §6 with a 2-sentence intro stating the three frames and their roles.

---

## What is logically tight (preserved strengths)

- **§1.1 four gaps** map cleanly to §1.2 four contributions. ✓
- **§4.1.1 → Table 2 → §4.1.2 reconciliation** chain is coherent: spec is established, results are reported, then reconciled with prior 3-market study. ✓
- **§4.3 reconciliation question** ("how can H magnitude track RPS when direction is heterogeneous?") is a clear and well-posed question; the answer (separability vs semantics) is correct in substance — only the "first/second-order" language is suboptimal (m-3). ✓
- **§6.1 Link A → Link B → Link C chain** is logically tight: information-disadvantage → behavioural correlation → cross-market aggregation. The Kang (2026) "supports Link A only, not Link B" disclosure is honest. ✓
- **§6.6 H1 + H5 + canonical DML "convergent evidence of heterogeneity"** triangulation is well-constructed. ✓
- **§4.4 + §6.5 epistemic dominance** narrative is consistent: variance decomposition shown in §4.4 → roadmap implication in §6.5. ✓

---

## Recommended action ordering

If applying fixes:
1. **M-1 first** (factual error; reviewer-spot-check vulnerability)
2. **M-2 + M-3** (cross-reference + scope errors; mechanical fixes)
3. **M-4** (H1/H2 scope confusion in §4.5)
4. **m-1, m-2** (cross-reference + terminology consistency)
5. **m-3, m-4, m-5** (clarifications; lower urgency)
6. **m-6** (framework relationships; optional polish)

Total estimated effort: ~30–45 minutes for all 10 items. None require numerical changes; all are prose/cross-reference fixes.
