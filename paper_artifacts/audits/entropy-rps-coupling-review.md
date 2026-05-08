# Peer Review (tiếng Việt): "Cross-Market Entropy–Risk Coupling with Retail Participation"

**Artifact:** [02_AnonymizedManuscript_v3_4.md](../02_AnonymizedManuscript_v3_4.md) (706 dòng, ~83 KB)
**Slug:** `entropy-rps-coupling`
**Review date:** 2026-05-06
**Reviewer protocol:** Feynman skill `peer-review` workflow (`prompts/review.md`)
**Trust level:** Adversarial peer review pre-submission, 4 trục (weakness, claim verify, novelty, writing).
**Source artifacts inspected:** Manuscript + project repo (CONTEXT.md, CLAUDE.md, pre_registration/, paper_artifacts/, validation/results_v2/)
**Evidence file:** [.drafts/entropy-rps-coupling-review-evidence.md](.drafts/entropy-rps-coupling-review-evidence.md)

---

## 1. Summary Assessment

Bài báo trình bày một **kết quả thực nghiệm có giá trị**: chứng minh tương quan đơn điệu giữa độ phân biệt regime entropy-based (Kruskal–Wallis H) và Retail Participation Share (RPS) trên panel 8 thị trường post-COVID, kèm theo một **đóng góp phương pháp luận** là cơ chế Schmitt-trigger label-stabilization cho soft-assignment unsupervised classifiers. Mức kỷ luật pre-registration, tự audit (file `critique.md` 556 dòng), và byte-for-byte regression assertions là **xuất sắc** so với mặt bằng đa số bài empirical finance hiện tại.

Tuy nhiên — và đây là khúc mắc nghiêm trọng nhất — **bản thảo nộp KHÔNG propagate đầy đủ kết luận từ self-audit của chính tác giả vào main text**. Cụ thể: (1) việc đổi instrument H2 từ composite MS_index (pre-registered, ρ=0.952) sang RPS (post-hoc, ρ=0.754) chỉ được đề cập 1 dòng trong Appendix A.1 mà không nêu hậu quả đối với "pre-registration protection"; (2) Abstract khẳng định hysteresis "preserves qualitative conclusions" trong khi 4/8 thị trường REJECT H5 và 1 dead-zone — thẳng thắn ngược với kết luận tự audit; (3) PSEI p_tra=0.403 thực tế đã falsify pre-registered binary threshold của H3 nhưng chỉ được phủ bằng continuous companion (ρ=0.5629, p=0.146 — bản thân underpowered) mà không gọi tên thất bại. Cộng thêm 2 lỗi citation nghiêm trọng (Boehmer 2005 — sai năm + sai 2/3 tác giả; Vu 2024 — danh sách tác giả không khớp).

Toàn bộ kết quả định lượng đều **đúng và tái tạo được byte-for-byte** trong code repo. Vấn đề là **văn bản bài báo over-claim so với bằng chứng và self-audit của chính tác giả**. Mức tích cực bất ngờ: vấn đề không phải scientific dishonesty mà là **failed propagation** từ critique.md vào manuscript-as-submitted. Đa số là sửa được trong revision.

**Tóm:** Mạch khoa học tốt, kỷ luật pre-reg cao, nhưng manuscript hiện tại **over-claim ở Abstract/§A.1 so với §7.1 và critique.md**. Cần Major Revision tập trung vào (a) lift toàn bộ self-audit vào §9 Limitations + Abstract softening, (b) sửa 3 citation, (c) thêm leave-one-out sensitivity và SimpleVol-RPS Spearman, (d) softer language về Schmitt-trigger generalization và "preserves qualitative conclusions".

---

## 2. Strengths

Đây là những điểm tôi tin reviewer khác sẽ ghi nhận và bài báo không nên đánh đổi để chiều theo phản hồi:

1. **Pre-registration thực thụ.** Pre-reg `b130b0f` 2026-04-18 cùng public archive — không chỉ ý định mà có hash commit cụ thể, falsification rules, và pinned hyperparameters (CONTEXT.md, hypotheses_v2_combined.md). Trong empirical finance, mức này hiếm.

2. **Self-audit 556 dòng (`pre_registration/critique.md`).** 23 issues được tác giả tự nhận diện, phân loại Addressed / Disclose / v3-needed. Đây là tài liệu mẫu mực — tôi (reviewer) chủ yếu chỉ phải verify rằng tác giả nói đúng và propagate sang paper. Đề nghị giữ nguyên file này và public-cite nó.

3. **Honest swap đi ngược tự lợi ích.** Composite MS_index pre-reg cho ρ=0.952 nhưng tác giả tự nguyện supersede sang RPS đơn biến với ρ=0.754 thấp hơn, vì composite có 3 vấn đề (weights tùy ý, units không tương thích, kiểm soát researcher DoF kém). [rps_rationale.md §5.4](../project/paper_artifacts/rps_rationale.md). Đây là chuẩn mực đáng học hỏi.

4. **Byte-for-byte regression assertions.** Manuscript tuyên bố và tôi đã verify: ρ=0.754, p=0.031, CI=[0.089,0.994], MC P(ρ>0.5)=100%, filtered ρ=0.814 — toàn bộ khớp với [h2_rps_validation.json](../project/validation/results_v2/h2_rps_validation.json) trong sai số rounding (0.7545→0.754, 0.0305→0.031). Đây là level reproducibility hiếm.

5. **Block-aware inference cho overlapping forward-vol windows.** §5.1 phát hiện naive Mann–Whitney p-values bị inflated do 19-bar overlap giữa 20-day forward-vol windows liền kề; sửa bằng circular-block bootstrap + block-rotation permutation + Newey–West HAC (lag=20). Đây là contribution methodological mà field thường skip.

6. **BH-FDR multiplicity correction trên 8-market panel.** Đã thêm vào §10 cho H1, H4 (theo critique.md §1.4, §4.3). Không phải pre-registered nhưng tác giả thừa nhận và remediate.

7. **Architectural transparency cho refinements pre-reg→final.** Appendix A.1 liệt kê 6 thay đổi (H1 test, H2 instrument, H3 verdict, H4 null, multiplicity, H5 dead-zone). Mức minh bạch tốt hơn 90% bài finance.

8. **Per-domain re-calibration test (§7.2, Table E.2).** Verdict pattern (PASS/Dead/REJECT) ổn định giữa shared-parameter và own-optimum modes — giảm khả năng "transfer learning artifact" giải thích cross-market heterogeneity.

9. **AI assistance disclosure (§3.8 + Declaration).** Anthropic Claude Opus 4.x cho code-gen + lit synthesis được declare cleanly + protocol verify (line-by-line review, unit tests vs analytical benchmarks, byte-for-byte regression). Đây là chuẩn mực đáng học hỏi.

10. **Phase-space visualization Appendix G.** Same GMM components, only label-rule differs giữa raw vs filtered — đúng cách trình bày engineering claim của hysteresis ("smoothing rather than re-clustering"). 156/1506 bars (10.4%) đổi label, tập trung tại boundary regions. Trực quan hợp lý.

---

## 3. Critical Issues

Mỗi issue dưới đây — nếu không xử lý — tôi tin reviewer tại venue chuẩn (NAJEF, Quant Finance, J Empirical Finance, Entropy) sẽ recommend Reject hoặc Major Revision.

### C-1. Citation Boehmer et al. 2005 sai cả năm và 2/3 tác giả

**Vị trí:** Manuscript line 73, line 418 (References).
**Trích nguyên văn:**
> "Boehmer, E., Jones, C.M., Zhang, X., 2005. Institutional investors and the informational efficiency of prices. Rev. Financ. Stud. 22(9), 3563–3594. https://doi.org/10.1093/rfs/hhp028."

**Thực tế (verified qua [RFS](https://academic.oup.com/rfs/article-abstract/22/9/3563/1573896), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1468202), [IDEAS RePEc](https://ideas.repec.org/a/oup/rfinst/v22y2009i9p3563-3594.html)):**
- Tác giả đúng: **Ekkehart Boehmer + Eric K. Kelley** (2 tác giả)
- Năm đúng: **2009** (không phải 2005)
- Title, journal, volume(issue), pages, DOI đều đúng

"Boehmer Jones Zhang" là một paper **khác** ("Which Shorts Are Informed?" J. Finance 63(2), 491-527, 2008). Tác giả có khả năng nhầm 2 paper với nhau.

**Tại sao critical:** Reference này được dùng cho **Link A** trong three-link mechanism chain (§8.2), trong Principal Contribution 1 (§1.2), §2.3 lit gap framing, và §10 Conclusion. Một reviewer chuyên về market microstructure sẽ phát hiện ngay (Boehmer-Kelley 2009 là paper cực kỳ nổi tiếng trong field). Phát hiện này làm suy giảm uy tín của toàn bộ phần literature handling.

**Hành động:** Sửa references thành "Boehmer, E., Kelley, E.K., 2009. ..." Update mọi trích dẫn trong text từ "Boehmer et al. (2005)" thành "Boehmer and Kelley (2009)".

### C-2. Abstract over-claim "preserves qualitative conclusions" mâu thuẫn với §7.1 và critique.md

**Vị trí:** Abstract (line 5).
**Trích nguyên văn:**
> "Hysteresis filtering, applied for production-grade label stability, **preserves qualitative conclusions across per-market direction, cross-market coupling, and regime composition tests.**"

**Thực tế từ §7.1 Table 4 (đã sửa đúng theo pre-reg rule >7pp REJECT — verified vs critique.md §5.2):**
- 3 PASS (NIKKEI decisive, BTC borderline, VNINDEX borderline)
- 1 Dead zone (PSEI 5.6pp)
- **4 REJECT** (KOSPI 7.2pp, NIFTY 7.7pp, SPX 9.0pp, FTSE 9.5pp)

**Self-audit verbatim ([critique.md §5 Net for H5](../project/pre_registration/critique.md)):**
> "Pre-reg rule has a dead zone, a threshold-mismatch bug in the paper, and calibration-circular thresholds. Under the correct rule, 4/8 reject (not 5/8), with PSEI in dead zone. §10's bootstrap CIs show no rejection is decisive at 95 %; only NIKKEI is PASS_DECISIVE. **Paper abstract must soften** and §4 must be corrected."

> "**H3 and H5 fail or partially fail under their own rules and require softened abstract claims.**"

**Tại sao critical:** Abstract là cửa đầu tiên reviewer đọc. Câu "preserves qualitative conclusions across regime composition tests" trực tiếp được "regime composition" = H5 verdict. Khi 4/8 REJECT + 1 dead-zone, "preserves" là over-claim nghiêm trọng. Tác giả đã tự nhận điều này trong critique.md. Đây là lỗi propagation, không phải lỗi science.

**Hành động:** Re-write câu Abstract đó theo gợi ý (ví dụ): *"Hysteresis filtering preserves the per-market direction labels (invariant on every market) and sharpens the H–RPS coupling (ρ rises from 0.754 to 0.814); however, the parameter-robustness test (H5) does not generalize uniformly: under the pre-registered >7 pp REJECT bar, 3 markets pass, 1 falls in the 5–7 pp dead-zone, and 4 reject. Per-market re-calibration confirms this verdict pattern is intrinsic, not a transfer-learning artifact."*

### C-3. H2 instrument swap (composite → RPS) under-disclosed trong main text

**Vị trí:** Pre-reg specification ([hypotheses_v2_combined.md §H2](../project/pre_registration/hypotheses_v2_combined.md)) đăng ký:
> "MS_index = 0.4 * circuit_breaker + 0.3 * (1 - institutional_share) + 0.3 * (1 - log(market_cap_usd))"

**Pre-reg result (composite):** ρ = 0.952, p = 2.6e-4 (per [rps_rationale.md §5.4](../project/paper_artifacts/rps_rationale.md))

**Active spec (RPS):** ρ = 0.754, p = 0.031

**[h2_rps_validation.json](../project/validation/results_v2/h2_rps_validation.json) verbatim:**
> `"status": "PRIMARY H2 test (supersedes composite pre-registered b130b0f)"`
> `"supersession_reason": "Composite weights chosen qualitatively with no derivation; components measured in incompatible units; rho-magnitude against composite carried uncontrolled author degree of freedom."`

**Self-audit ([critique.md §2.5](../project/pre_registration/critique.md)) verbatim:**
> "Even a specification swap *against* self-interest is still a post-hoc change. **A strict pre-reg reading says: the pre-registered instrument was the composite, and its ρ = 0.952 is what pre-reg protects. RPS is post-hoc evidence, not pre-registered evidence.** The paper treats RPS as primary, which is the honest scientific choice but not the pre-reg-compliant choice. **Disclose both readings.**"

**Manuscript treatment:** §1.3 nói chung "refinements ... documented explicitly, several of which went against author self-interest" + Appendix A.1 dòng (2) "H2 instrument changed from composite microstructure index to single-variable Retail Participation Share". Không nêu:
- ρ pre-reg composite = 0.952 (vs 0.754)
- Strict pre-reg protection chỉ áp dụng với composite
- "RPS is post-hoc evidence, not pre-registered evidence"

**Tại sao critical:** Bài báo claim "pre-registered" trên Abstract / §1.3 / §3.8 nhiều lần. Một reviewer khắt khe sẽ đọc Appendix A.1, không thấy ρ composite=0.952 cũ, đến validation/results_v2/prereg_b130b0f/, mới hiểu được spec swap thực sự. Việc không lift mức disclosure này lên main text khiến độc giả không có repo access **không thể đánh giá đúng độ mạnh của bằng chứng**. Đây là lỗi failed propagation: critique.md đã yêu cầu *"Disclose at first mention"* nhưng manuscript không thực hiện.

**Hành động:** Thêm 1 paragraph vào §4 Phase 1 (mở đầu) hoặc §A.1 với nội dung như critique.md §2.5 prescribed:
> "Pre-registration `b130b0f` originally tested H2 against a 3-component composite microstructure index (weights 0.4/0.3/0.3 on circuit-breaker / 1−institutional-share / 1−log(market-cap-USD)) yielding Spearman ρ = 0.952 (p = 2.6e-4). Post-hoc review judged the composite scientifically untenable on three grounds: weights chosen qualitatively without derivation, components measured in incompatible units (binary, share, log-USD), and ρ-magnitude carried uncontrolled author DoF. RPS is therefore adopted as primary instrument despite producing a *lower* ρ = 0.754 — a refinement that went against author self-interest. The composite result and pre-reg artifacts are preserved read-only. Strict pre-registration protection applies to the composite specification; the RPS finding reported here is post-hoc rigor on a single-variable, ex-ante measurement."

---

## 4. Major Issues

### M-1. Citation Vu et al. 2024 — danh sách tác giả không khớp

**Vị trí:** Line 500 (References).
**Manuscript:**
> "Vu, L.T., Nguyen, P.M., Hoang, Q.A., 2024. An integrated approach with permutation entropy for stock market efficiency. J. Ecohumanism 3(8), 1382–1399."

**Thực tế (verified [Journal of Ecohumanism](https://ecohumanism.co.uk/joe/ecohumanism/article/view/4819)):**
- Tác giả: **Vu, L. T., Van Nguyen, A., Dao, Q. N., Do, H. M., & Doan, H. T. T.** (5 tác giả)
- Title đầy đủ: "An Integrated Approach with **Permutation Entropy Measure and Conventional Tests for Study on** Stock Market Efficiency"

Manuscript chỉ list 3 tác giả, 2 trong 3 sai họ tên. **Substantive claim** ("57 markets, frontier lowest efficiency") đúng ✓.

**Hành động:** Sửa thành "Vu, L.T., Van Nguyen, A., Dao, Q.N., Do, H.M., Doan, H.T.T., 2024. An Integrated Approach with Permutation Entropy Measure and Conventional Tests for Study on Stock Market Efficiency..."

### M-2. Citation Maneejuk et al. 2022 — author list discrepancy

**Manuscript:**
> "Maneejuk, P., Kaewsompong, N., Yamaka, W., Sriboonchitta, S., 2022."

**Web search (article 101816, NAJEF v.63):** "Paravee Maneejuk, **Nuttaphong Kaewtathip, Peemmawat Jaipong**, Woraphon Yamaka". Manuscript "Kaewsompong, N." có thể là sai họ; "Sriboonchitta, S." có thể không có trong author list của bài này. Substantive claim (Markov-switching, WHO Jan 30 2020) đúng theo abstract.

**Hành động:** Author tự verify lại list; nếu paper đúng là pii/S1062940822001516 (article 101816) thì sửa author names.

### M-3. H3 falsification rule fails on PSEI nhưng không được nêu trong main text

**Pre-reg rule ([hypotheses_v2_combined.md §H3](../project/pre_registration/hypotheses_v2_combined.md)):**
> "H3 rejected if: any frontier market shows p(Transitional) < 0.45 OR any developed market shows p(Transitional) > 0.60."

**Observed (Table D.2):**
- VNINDEX (frontier) p_tra = **0.451** (within 0.001 of floor)
- **PSEI (frontier) p_tra = 0.403 — below 0.45 floor → H3 REJECTED on PSEI per pre-reg rule**

**Self-audit ([critique.md §3 Net for H3](../project/pre_registration/critique.md)):**
> "Paper abstract should soften 'Transitional Dominance holds on frontier markets' to '**p_tra is elevated on high-RPS markets and sits near the pre-reg 0.45–0.55 band on VNINDEX/PSEI; continuous companion ρ = 0.56, p = 0.15 (underpowered).**'"

**Manuscript §6.2 thực tế:** Chỉ nói "Continuous Spearman ρ(p_tra, RPS) is positive but underpowered at n = 8" — không gọi tên việc PSEI đã falsify pre-reg threshold.

**Hành động:** Trong §6.2 hoặc §9 Limitations, thêm 1 paragraph: "Under the pre-registered binary rule (frontier p_tra < 0.45 falsifies), PSEI's observed p_tra = 0.403 (95% CI [0.315, 0.488]) falls below the floor, rejecting H3 in its original categorical form. The pre-reg rule is recognized post-hoc as threshold-circular relative to VNINDEX's calibration band (4–10 flips/yr ↔ p_tra ≈ 0.45–0.55). The continuous companion Spearman ρ(p_tra, RPS) = 0.5629 (p = 0.146, 95% CI [-0.290, 0.961]) is suggestive but underpowered at n = 8 and is reported as a softened claim."

### M-4. Leave-one-out sensitivity (drop VNINDEX) — không reported

Nếu loại VNINDEX khỏi panel:
- Recompute Spearman: ρ ≈ 0.634 (n=7)
- p ≈ 0.13 (one-sided) — **không còn significant tại α=0.10**

VNINDEX là calibration market cho hysteresis (CONTEXT.md), có RPS=0.90 (cao nhất), H=83.90 (cao nhất, một bậc tự do tự nhiên kéo gradient). Tác giả §B.3 reports stratified subpanel (Frontier+Emerging n=4: ρ=0.400) nhưng không có explicit LOO. Bootstrap CI [0.089, 0.994] đã cho biết kết quả nhạy với 1-2 quan sát; LOO sẽ làm bài báo thẳng thắn hơn.

**Hành động:** Thêm Appendix B (hoặc §4.3) một bảng LOO leave-one-out cho cả raw và filtered. Nếu drop-VNINDEX ρ rơi xuống ~0.6 và mất significance, **báo cáo trung thực**. Reviewer sẽ cảm ơn.

### M-5. KOSPI là outlier nghiêm trọng nhưng không được engage

**Table B.1:** KOSPI RPS=0.70 (gần PSEI=0.68) nhưng H=5.88 (vs PSEI=48.10). Khoảng cách order of magnitude. Spearman bao bọc qua rank, nhưng narrative §4 "monotone gradient over four orders of magnitude" làm lu mờ điều này.

**Khả năng giải thích chưa được paper engage:**
- ASIFMA 2022 RPS=0.70 đã 4 năm; 2024-2025 KRX có thể đã thay đổi
- KOSPI có circuit breakers + daily limits + high-frequency institutional flow → "RPS" không capture được hết microstructure
- Entropy features có thể mis-classify trên KOSPI vì lý do nào đó

**Hành động:** §4 hoặc §8 Discussion thêm 1 paragraph engage thẳng KOSPI outlier. Nếu LOO drop-KOSPI ρ rises substantially, nói rõ.

### M-6. SimpleVol-RPS Spearman không được report — undermines structural-feature claim

**§8.5 / Appendix F.2:** "SimpleVol features achieve higher raw discrimination on every market" — paper frame là "categorical distinction" structural vs measurement.

**Câu hỏi reviewer chắc chắn sẽ hỏi:** "Spearman ρ(H_SimpleVol, RPS) là bao nhiêu?" — vì:
- Nếu ρ_SimpleVol > ρ_Entropy (cả về magnitude và rank), claim "only structural features support mechanistic interpretation" sụp đổ — vì SimpleVol cũng track microstructure gradient
- Nếu ρ_SimpleVol ≈ ρ_Entropy, distinguishing argument trở thành "same gradient, different mechanistic story" — yếu hơn nhiều
- Nếu ρ_SimpleVol < ρ_Entropy, đây là LẬP LUẬN MẠNH cho structural features — phải report

Bỏ trống số này khiến §8.5 đọc như defensive caveat (đúng theo cảm giác của một reviewer khắt khe).

**Hành động:** Tính và report 4 giá trị Spearman cho 3 feature sets × {raw, filtered}: ρ_Entropy, ρ_SimpleVol, ρ_Combined trong Appendix F.2. Có thể đã có sẵn trong [entropy_vs_simple_8market.json](../project/validation/results_v2/entropy_vs_simple_8market.json) chưa được surface.

### M-7. Hysteresis VNINDEX-calibration → threshold-HARKing không được nêu trong main text

**Self-audit ([critique.md §3.1](../project/pre_registration/critique.md)) verbatim:**
> "VNINDEX's paper-v2 post-2020 p_tra with the pre-reg hysteresis calibration was ≈ 0.45–0.55 — the calibration target was the 4–10 flips-per-year band on VNINDEX, which mechanically produces p_tra in that range. 'Frontier > 0.55' and 'Frontier fail < 0.45' both sit inside or immediately adjacent to VNINDEX's own observed band. **A sceptical reader cannot rule out that the thresholds were chosen to fit VNINDEX's observed number. This is *threshold*-HARKing.**"

Manuscript §9 Limitations chỉ nói chung "Hysteresis calibration ... primary-analysis parameter choice remains anchored to one market." — yếu hơn nhiều so với critique.md.

**Hành động:** Lift đoạn critique.md §3.1 vào §9 Limitations.

### M-8. Pre-reg "choose 2 of 3" panel composition — flexible composition không được disclose

**Pre-reg [hypotheses_v2_combined.md §"Pre-registered markets"](../project/pre_registration/hypotheses_v2_combined.md):**
> "Frontier: VNINDEX (VNINDEX), KSE 100 (^KSE) or SET (^SET.BK), PSEi (PSEI.PS) (choose 2 of 3 by data quality)"
> "Emerging: ... (choose 2 of 3)"
> "Developed: ... (choose 2 of 3)"

**Self-audit ([critique.md §6.1](../project/pre_registration/critique.md)):** "the final panel was not declared ex-ante; 'choose 2 of 3 by data quality' leaves room for post-data inspection. The actual panel was reasonable, but a strict pre-reg would have frozen the selection before data was pulled."

**Manuscript:** Không nêu.

**Hành động:** §A.1 (Pre-registration architectural transparency) hoặc §9 Limitations thêm dòng "the pre-registered panel allowed 'choose 2 of 3' flexibility per microstructure category for data-quality reasons; the final 8-market selection was made before computing test statistics but after data ingestion. Strict pre-registration discipline would freeze the panel ex-ante; this is identified for v3 pre-reg."

### M-9. H3/H4/H5 scripts post-pre-reg-commit chưa được nêu

**Self-audit ([critique.md §3.4 / §4.4 / §5.5 / §6.4](../project/pre_registration/critique.md)):** "`hysteresis_cross_market_v2.py`, `hysteresis_robustness_v2.py` did not exist at pre-reg commit b130b0f. The pre-reg committed verdict language but not the code that would execute it."

**Manuscript:** Không nêu trong text.

**Hành động:** §A.1 hoặc §9 thêm 1 dòng disclosure.

### M-10. Filtered H jumps 4.5× (BTC), 3.7× (KOSPI) — narrative "smoothing" yếu hơn data

**[cross_market_summary_v2.csv](../project/validation/results_v2/cross_market_summary_v2.csv):**
- BTC: H_raw=7.13 → H_filt=32.24 (4.5×)
- KOSPI: H_raw=5.88 → H_filt=21.84 (3.7×)
- VNINDEX: H_raw=83.90 → H_filt=96.33 (1.15×) — như mong đợi nếu chỉ "smoothing"
- SPX: H_raw=2.12 → H_filt=1.51 (0.71× — giảm) — không phải chỉ smoothing
- FTSE: H_raw=4.15 → H_filt=1.34 (0.32× — giảm 3×)

Paper §3.4 + §4.4 + §8.4 framing hysteresis là "single-bar flicker removal" → "smoothing rather than signal-removal". Nhưng dữ liệu cho thấy **filter có tác động re-structuring đáng kể trên KOSPI/BTC** (tăng) và **giảm tín hiệu trên SPX/FTSE** (developed). Narrative "preserves qualitative conclusions" che lấp đặc trưng phụ thuộc thị trường này.

**Hành động:** §4.4 hoặc §8.4 thêm 1 paragraph phân tích:
- VNINDEX, NIKKEI: H_filt ≈ H_raw → filter behaves as expected
- KOSPI, BTC: H_filt 3-4× H_raw → filter restructures discrimination, không chỉ smoothing
- SPX, FTSE: H_filt < H_raw → filter có thể strip signal khi Δ_hard quá cao
- Phân tích vì sao và liệu có heterogeneous filter response cần re-calibration không.

### M-11. RPS measurement noise sd=0.05 có thể không đại diện cho definitional uncertainty

§9 Limitations thừa nhận RPS sources có "definitional variation in the second decimal" (executed volume vs turnover vs account share). MC sensitivity dùng N(0, 0.05) clamp [0,1]. Tuy nhiên:
- BTC RPS=0.55 từ "aggregated crypto-exchange reports" — không có định nghĩa khắt khe; uncertainty thực tế có thể ±0.10 đến ±0.20
- SPX=0.22 từ midpoint SIFMA (~17.9%) + MEMX (30-37%) — spread nội tại 17→37 = 20pp, midpoint với uncertainty 0.05 không phản ánh

**Hành động:** Bổ sung MC sensitivity với sd=0.10 và sd=0.15. Nếu P(ρ>0.5) vẫn cao → robustness mạnh; nếu rơi → caveat trong Abstract.

---

## 5. Minor Issues

### m-1. §1.2 vs §10 — "two" vs "three" secondary contributions

§1.2 (line 31): "two principal contributions and **two** secondary contributions"
§10 (line 386): "**Three** secondary contributions emerge"

§10 reclassify "label-stabilization" — vốn là Principal Contribution 2 trong §1.2 — thành "secondary contribution thứ 2" trong §10. Inconsistency. **Hành động:** Chọn 1 cách phân loại, đồng bộ giữa §1.2 và §10.

### m-2. §1.4 "Dual relevance" lặp lại §1.2 contributions

Có thể compress thành 2-3 câu hoặc nhúng vào §1.2.

### m-3. "Production deployment" / "ML system design" framing (§3.7, §3.7.1)

Thuật ngữ ML-paper voice. Nếu submit finance journal (NAJEF, JBF, J Empirical Finance), nên giảm bớt. Nếu submit Entropy / Chaos Solitons Fractals / J Banking & Finance Letters / dual ML+finance venue, OK.

### m-4. Math notation Eq (1) và Eq (4)

- **Eq (1):** $p_\pi^w = \sum_{t : \text{ord}(X_t)=\pi} w(X_t) / \sum_t w(X_t)$ — cần làm rõ rằng cả tử và mẫu đều sum trên các $t$ trong cửa sổ $W$; hiện tại có thể đọc nhầm là sum global.
- **Eq (4):** $\mu_{t-504:t}$ với prose "strictly-backward" → notation rõ phải là $[t-504, t-1]$; hiện tại $[t-504, t]$ đọc gây hiểu nhầm vì $t$ là chính nó.

### m-5. Abstract dài ~370 từ, single paragraph

Có thể chia 2 paragraph (empirical + methodological) cho dễ đọc.

### m-6. Section ordering H2 trước H1

Trình tự "magnitude (cross-market) trước direction (per-market)" defensible vì luận chứng nhưng unconventional. Reviewer có thể hỏi tại sao. Trong response letter chuẩn bị giải thích.

### m-7. Schmitt-trigger K=2 → K=3 generalization framing (§3.4)

Schmitt 1938 trigger là binary 2-state. Mở rộng lên K=3 mixture posterior với margin-comparison và persistence counter là một **generalization**, không phải "direct adaptation". Wording "adapted from the Schmitt-trigger principle" hợp lý; "generalized" sẽ chính xác hơn. Tham khảo Brokate & Sprekels 1996 cho hysteresis multi-state.

### m-8. Foundation-model comparison deferred (§8.5, §9)

Acceptable as future work, nhưng nếu có thể bổ sung 1 head-to-head cell (vd Chronos zero-shot phân biệt regime trên VNINDEX) → bài đậm hơn cho ML audience.

### m-9. KOSPI outlier explanation (xem M-5) — tương tác với m-7

Engaging KOSPI outlier có thể yêu cầu thêm sub-section nhỏ (§4.7 chẳng hạn).

### m-10. PR-7: H1 fixed-magnitude H thresholds

Critique.md §1.2: H magnitude scales with sample size; threshold "H<20 frontier" pre-reg không phải effect-size. §9 Limitations có thể thêm 1 dòng đề cập (khi v3 pre-reg sẽ dùng ε² hoặc Cliff δ).

### m-11. S-3: Stratified subpanel "Frontier+Emerging" ρ=0.400 chưa được đánh giá đầy đủ

Table B.3 reports ρ=0.400 (n=4, p=0.600) cho frontier+emerging. Đây là leave-cluster-out test — cho thấy **trong cùng cluster microstructure (high-RPS markets), gradient yếu**. Paper xếp "descriptive only" nhưng số này informative. §4.3 nên thêm 1 câu: "Within the high-RPS sub-panel (frontier + emerging, n=4), ρ drops to 0.400 with p=0.600, suggesting the headline gradient is driven primarily by between-cluster (frontier+emerging vs developed) contrast rather than within-cluster microstructure fineness."

---

## 6. Reproducibility and Verification

### Code reproducibility — VERIFIED (partial — limited to paper claims, không re-run)

**Phạm vi reviewer access:** Tôi có quyền đọc [project/](../project/) repository qua filesystem, không chạy code.

**Numerical claims spot-checked vs h2_rps_validation.json:**

| Claim (manuscript) | JSON value | Match |
|---|---|---|
| ρ(H_raw, RPS) = 0.754 | 0.7545 | ✓ |
| p = 0.031 | 0.0305127... | ✓ |
| 95% CI [0.089, 0.994] | [0.0886, 0.9937] | ✓ |
| MC P(ρ > 0.5) = 100% | 1.0 | ✓ |
| MC mean ρ = 0.796 | 0.7957 | ✓ |
| Filtered ρ = 0.814 | 0.8144 | ✓ |
| Filtered p = 0.014 | 0.0138 | ✓ |
| Δρ filtered − raw = 0.060 | 0.0599 | ✓ |
| Frontier+Emerging ρ = 0.400 | 0.400 | ✓ |
| Circuit-breaker-present (n=6) ρ = 0.771 | 0.7714 | ✓ |

**Spot check IC-1:** Manual recompute Spearman từ Table B.1 với midrank cho FTSE/NIKKEI ties → ρ ≈ 0.756, khớp 0.754 trong rounding. ✓

**Per-market H values (Table B.1) match cross_market_summary_v2.csv ✓**

**H1 direction (Table C.1) match CSV ✓** — PSEI là thị trường duy nhất `direction_verdict_formal=Paradox` raw 20d.

**H3 continuous (h3_continuous.json) ρ=0.5629, p=0.146** — manuscript §6.2 chỉ nói "positive but underpowered", không quote số. Paper đã choose to soft-disclose. ✓ honesty.

**Pre-reg `b130b0f` artifacts:** [validation/results_v2/prereg_b130b0f/](../project/validation/results_v2/prereg_b130b0f/) — referenced in CONTEXT.md nhưng tôi chưa đọc nội dung; khả năng cao chứa composite ρ=0.952 frozen.

### What I did NOT verify:
- Source data (vnstock VNINDEX OHLCV, yfinance international) — no fetch
- GMM convergence stability (n_init=10) — no re-run
- Hysteresis calibration target band (4-10 flips/yr on VNINDEX) — no re-run
- Bootstrap CI bounds beyond rounding match
- Figure G.1 image — file referenced but not attached to manuscript
- arXiv pre-reg archive composition

**Verification level:** **PARTIAL** — limited to byte-for-byte comparison of paper text vs JSON outputs the author committed. The paper's "byte-for-byte regression assertion at atol=1e-4" claim **holds for all numbers I checked**.

### Threats to reproducibility from a reviewer perspective:
1. **vnstock + yfinance rate limits** mentioned in CLAUDE.md "When something feels off" section. Reproducibility depends on data availability.
2. **GMM random_state=42** pinned but EM with 10 random initializations might still produce slightly different cluster centroids if scipy/numpy versions differ.
3. **Repository URL anonymized** for double-blind. Post-acceptance the canonical reproducibility tag must be unredacted.

### Reproducibility section in paper itself:
§3.8 + Code/Data Availability section claim public availability + canonical reproducibility tag + reproduction commands + license MIT. **Adequate** — among best-in-class for finance. However, claim of "byte-for-byte regression assertions in active validation scripts" — recommend the journal require these scripts to be re-run by editor / reproducibility editor at acceptance time.

---

## 7. Inline Annotations

Annotations gắn trực tiếp với section/claim cụ thể; phục vụ author's revision draft.

### Abstract (line 5)
- **[CRITICAL C-2]:** "preserves qualitative conclusions across … regime composition tests" — sửa per critique.md §5 Net for H5 và §7.1 Table 4 (4 REJECT + 1 dead-zone).
- **[MINOR m-5]:** Cân nhắc chia abstract thành 2 paragraph.

### §1.2 Contributions (line 31, 33-39)
- **[MINOR m-1]:** "two secondary contributions" — đồng bộ với §10 "Three secondary contributions"
- **[MINOR m-7]:** Principal Contribution 2 wording "non-parametric label-stabilization mechanism … applicable beyond entropy features" — chuyển "adapted from the Schmitt-trigger principle" thành "generalized from the Schmitt-trigger principle (Schmitt, 1938) to K-component soft-assignment classifiers"

### §1.3 (line 43)
- **[CRITICAL C-3]:** "pre-registration: hypotheses, market list, parameter values, and pass/reject criteria were committed to the public repository before the panel tests were run" — câu này KHÔNG sai về mặt fact (pre-reg b130b0f thực sự committed) nhưng cần ngay sau câu này thêm 1 câu honest về H2 instrument swap.

### §1.4 (line 45-47)
- **[MINOR m-2]:** Compress hoặc merge với §1.2.

### §3.4 (line 138-143)
- **[MINOR m-7]:** "Following Schmitt (1938)" → "Generalizing the two-threshold principle of Schmitt (1938) and the multi-state hysteresis framework of Brokate and Sprekels (1996) to K-component mixture posteriors"

### §3.7 + §3.7.1 (line 167-172)
- **[MINOR m-3]:** "Production deployment / ML system design" ngôn ngữ — nếu finance venue: trim hoặc move to Appendix.

### §3.8 (line 175-176)
- AI-assistance disclosure — adequate ✓.

### §4 (line 180-218)
- **[CRITICAL C-3]:** Mở đầu §4 (hoặc cuối §4.1) thêm paragraph về composite→RPS swap với ρ pre-reg = 0.952 vs RPS = 0.754.
- **[MAJOR M-4]:** Thêm §4.x Leave-one-out sensitivity table (raw + filtered).
- **[MAJOR M-5]:** Thêm 1 paragraph engage KOSPI outlier (RPS=0.70 nhưng H=5.88).
- **[MINOR m-11]:** §4.3 thêm 1 câu về Frontier+Emerging subpanel ρ=0.400 informative meaning.

### §4.4 (line 202-214)
- **[MAJOR M-10]:** Thêm 1 paragraph về heterogeneity của filter impact (BTC/KOSPI 3-4× tăng vs SPX/FTSE giảm).

### §5.1 (line 230-232)
- **[VERIFIED OK]:** "Only one market — PSEI at the 20-day horizon — clears both the pairwise CI bar and the Newey–West t-test under raw labels" — matches data. ✓

### §5.4 (line 257)
- "weaker than the direction claim in earlier single-market entropy paradox literature, but consistent with the cross-market magnitude finding (§4)" — ✓ honest.

### §6.2 (line 269-271)
- **[MAJOR M-3]:** "Continuous Spearman ρ(p_tra, RPS) is positive but underpowered at n = 8" — bổ sung phần PSEI p_tra=0.403 falsifies pre-reg threshold + acknowledge threshold-HARKing per critique.md §3.

### §6.3 (line 273-277)
- **[VERIFIED OK]:** Honest disclosure of H4 weak null ✓.

### §7.1 (line 283-285) — Table 4
- Số trong table đúng theo critique.md §5.2 corrected reading (3 PASS, 1 dead, 4 REJECT). ✓ — chỉ Abstract phải align với table này (xem C-2).

### §7.2 (line 302-306)
- ✓ Per-domain calibration analysis. Strong contribution.

### §8.2 (line 318-330)
- **[CRITICAL C-1]:** "Boehmer et al. (2005)" — sửa thành "Boehmer and Kelley (2009)" mọi nơi (line 73, 322, 384, 418).

### §8.4 (line 338-340)
- **[MAJOR M-10]:** "behaving as a Schmitt-trigger smoothing operation that removes single-bar flicker without creating new structure" — over-claim với KOSPI/BTC; thêm caveat về heterogeneous response.

### §8.5 (line 342-352)
- **[MAJOR M-6]:** Thiếu Spearman ρ(H_SimpleVol, RPS) và ρ(H_Combined, RPS). Phải report.

### §9 Limitations (line 358-376)
- **[MAJOR M-3, M-7, M-8, M-9]:** Add 4 disclosures: H3 PSEI fail, threshold-HARKing, panel flexibility, scripts post-pre-reg.
- **[MAJOR M-11]:** Add MC sensitivity với sd=0.10, sd=0.15.
- **[MINOR m-10]:** Add H magnitude vs effect size note.

### §10 Conclusion (line 380-388)
- **[MINOR m-1]:** "Three secondary contributions" — đồng bộ với §1.2.
- **[CRITICAL C-1]:** Đoạn Boehmer reference (line 384).

### References
- **[CRITICAL C-1]:** line 418 sửa Boehmer.
- **[MAJOR M-1]:** line 500 sửa Vu et al.
- **[MAJOR M-2]:** line 464 verify lại Maneejuk co-authors.

### Appendix A.1 (line 510-526)
- **[CRITICAL C-3]:** Refinement (2) needs full disclosure of composite ρ=0.952 vs RPS ρ=0.754 + "strict pre-reg protection applies to composite only".
- **[MAJOR M-9]:** Add note that H3/H4/H5 scripts post-pre-reg-commit.

### Appendix B (line 530-565)
- **[MAJOR M-4]:** Add LOO sensitivity table.
- **[MAJOR M-11]:** Add MC sensitivity với sd=0.10/0.15.

### Appendix F.2 (line 666-668)
- **[MAJOR M-6]:** Add ρ(H_SimpleVol, RPS), ρ(H_Combined, RPS).

---

## 8. Recommendation

### Verdict: **Major Revision**

Bài báo có **kết quả thực nghiệm có giá trị**, mức **kỷ luật phương pháp luận hiếm gặp** (pre-registration thực thụ + 556-line self-audit + byte-for-byte regression), và **đóng góp methodological** (Schmitt-trigger label stabilization) đủ để publishable. Nhưng manuscript-as-submitted **dưới mức phòng thủ** so với những gì self-audit của tác giả đã chuẩn bị: 3 Critical issues + 11 Major issues hầu hết là **lỗi propagation** (kết luận audit không được lift vào main text), không phải lỗi science.

### Concrete revision plan (theo thứ tự ưu tiên)

**Phase 1 — Critical fixes (tuần 1):**
1. **Sửa citation Boehmer 2005 → Boehmer & Kelley 2009.** Update toàn bộ trích dẫn (lines 73, 322, 384, 418).
2. **Re-write Abstract đoạn "preserves qualitative conclusions"** thành câu phân tách: direction labels invariant ✓; H–RPS coupling sharpens ✓; H5 4 REJECT + 1 dead-zone (KHÔNG preserve uniformly).
3. **Thêm paragraph H2 instrument swap disclosure** vào §4 mở đầu hoặc cuối §3.5: composite pre-reg ρ=0.952 → RPS ρ=0.754, strict pre-reg protection áp dụng cho composite, RPS là post-hoc rigor.

**Phase 2 — Major fixes (tuần 2-3):**
4. Sửa citation Vu 2024 author list (line 500) + verify Maneejuk 2022 (line 464).
5. §6.2: explicit disclosure PSEI p_tra=0.403 falsifies pre-reg <0.45 floor + threshold-HARKing acknowledgment.
6. §4.x: Leave-one-out sensitivity table cho cả raw + filtered.
7. §4 hoặc §8: KOSPI outlier engagement (1 paragraph).
8. §8.5 / Appendix F.2: Report ρ(H_SimpleVol, RPS) và ρ(H_Combined, RPS).
9. §9 Limitations: lift các disclosures từ critique.md (threshold-HARKing, panel flexibility "choose 2 of 3", scripts post-pre-reg, MC sensitivity sd=0.10/0.15).
10. §4.4 hoặc §8.4: heterogeneous filter impact (BTC/KOSPI 3-4× tăng vs SPX/FTSE giảm).

**Phase 3 — Minor + polish (tuần 4):**
11. §1.2 vs §10 đồng bộ contribution counts.
12. §1.4 compress.
13. Math notation Eq (1) Eq (4) clarifications.
14. Schmitt-trigger framing wording → "generalized from".
15. Frontier+Emerging subpanel interpretation note.

### Resubmission readiness

Sau Phase 1+2, bài báo sẽ ở trạng thái có thể submit lại với đa số reviewer concerns đã preempted. Self-audit của tác giả đã đi trước reviewer; revision chính là **lift work that's already done** vào main text.

### Suitable venues (sau revision)
- **Quantitative Finance** (Brouty-Garcin 2023 published here; method+empirics fit)
- **Journal of Empirical Finance** (cross-market focus)
- **North American Journal of Economics and Finance** (Maneejuk 2022 published here)
- **Entropy** (Cohen 2026, Papla-Siedlecki 2024 published here; ML+entropy fit cao)
- **Chaos Solitons Fractals** (Matsushit 2026, Shternshis 2022 published here; econophysics fit)

Note: tránh venues thuần microstructure như JFE / RFS — bài này là cross-market panel với n=8, không có investor-classified flow per-trade data.

### Sources

URLs verification trail (tất cả truy cập trong review session 2026-05-06):
- Boehmer & Kelley 2009 RFS: [academic.oup.com](https://academic.oup.com/rfs/article-abstract/22/9/3563/1573896) + [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1468202) + [IDEAS RePEc](https://ideas.repec.org/a/oup/rfinst/v22y2009i9p3563-3594.html)
- Kang 2026 arXiv: [2603.20271](https://arxiv.org/abs/2603.20271)
- Brouty & Garcin 2023 QF: [tandfonline](https://www.tandfonline.com/doi/full/10.1080/14697688.2023.2211108) + [arXiv 2208.11976](https://arxiv.org/abs/2208.11976)
- Vu et al. 2024 J Ecohumanism: [ecohumanism.co.uk](https://ecohumanism.co.uk/joe/ecohumanism/article/view/4819)
- Maneejuk et al. 2022 NAJEF: [ScienceDirect S1062940822001516](https://www.sciencedirect.com/science/article/pii/S1062940822001516)
- Fadlallah et al. 2013 PRE: [APS journals](https://journals.aps.org/pre/abstract/10.1103/PhysRevE.87.022911)

Author-supplied artifacts inspected:
- [project/CONTEXT.md](../project/CONTEXT.md)
- [project/CLAUDE.md](../project/CLAUDE.md)
- [project/pre_registration/hypotheses_v2_combined.md](../project/pre_registration/hypotheses_v2_combined.md)
- [project/pre_registration/critique.md](../project/pre_registration/critique.md)
- [project/paper_artifacts/rps_rationale.md](../project/paper_artifacts/rps_rationale.md)
- [project/validation/results_v2/h2_rps_validation.json](../project/validation/results_v2/h2_rps_validation.json)
- [project/validation/results_v2/cross_market_summary_v2.csv](../project/validation/results_v2/cross_market_summary_v2.csv)
- [project/validation/results_v2/h3_continuous.json](../project/validation/results_v2/h3_continuous.json)

Reviewer working notes: [.drafts/entropy-rps-coupling-review-evidence.md](.drafts/entropy-rps-coupling-review-evidence.md)
Review plan: [.plans/entropy-rps-coupling-review-plan.md](.plans/entropy-rps-coupling-review-plan.md)
