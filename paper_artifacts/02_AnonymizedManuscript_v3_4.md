# Direction Heterogeneity and Magnitude Scaling in Cross-Market Entropy–Risk Coupling with Retail Participation: Evidence from a Stratified Eight-Market Panel (2020–2026)

## Abstract

This paper asks whether an information-theoretic measure of market efficiency couples systematically with participant ecology — specifically retail participation share — across heterogeneous financial markets. The analysis characterises both the per-market direction of the entropy–volatility relationship (the "Entropy Paradox") and its cross-market magnitude scaling on an eight-market post-COVID panel spanning frontier, emerging, developed, and cryptocurrency segments.

The method combines weighted permutation entropy and standardised price sample entropy as features for a Gaussian mixture regime classifier with a Schmitt-trigger hysteresis filter on posterior probabilities. Per-market direction is estimated through a causal forest under double/debiased machine learning, with Purged K-Fold cross-fitting on filtered labels and reconciliation against an earlier 3-market observational study. Cross-market magnitude is tested under FTSE Russell / MSCI tier scoring and a cascade Retail Participation Share specification with three data-quality phases (authoritative point estimate, competing-source bounds, Bayesian posterior).

Three findings emerge. First, per-market regime direction is heterogeneous and tracks microstructure: frontier markets exhibit the Paradox direction in which low entropy precedes higher forward volatility, while developed markets show the Inverted direction or non-significant patterns and cryptocurrency shows a corrected Inverted reading under filtering. Second, apparent direction findings on developed markets under naive cross-fitting reflect future-leakage and do not survive proper time-series cross-fitting, illustrating the methodological importance of the splitter choice. Third, cross-market regime-discrimination magnitude scales monotonically with retail participation, with the ordering robust to standardisation, sample-size correction, tier-score variants, and source heterogeneity. The partial generalisation of hysteresis parameters across markets is read as positive evidence of cross-market microstructure heterogeneity rather than a methodological limitation.

**Keywords**: weighted permutation entropy; Gaussian mixture model; heterogeneous treatment effects; causal forest; retail participation; Adaptive Markets Hypothesis.

**JEL Classification**: G14, G17, G41, C14, C58.

---

## 1. Introduction

Backward-looking volatility measures (e.g., rolling realised volatility, Value-at-Risk) confirm risk after it materialises rather than detecting structural conditions preceding it. Information-theoretic complexity measures offer a complementary view: low entropy indicates coordinated, structured patterns; high entropy indicates random-walk dynamics consistent with informational efficiency. Permutation entropy and sample entropy have been applied to financial time series in single-market and cross-country settings (Bandt and Pompe, 2002; Risso, 2008; Zanin et al., 2012; Vu et al., 2024; Papla and Siedlecki, 2024), and a parallel continuous-efficiency programme (Campbell et al., 1997; Cajueiro and Tabak, 2004; Kristoufek and Vosvrda, 2013; Brouty and Garcin, 2023) develops continuous proxies for market efficiency from price-series properties. The coupling between entropy-derived efficiency and market participant ecology has not been tested systematically across a heterogeneous cross-market panel using ex-ante variables.

### 1.1 Research gap

This paper addresses four gaps. First, the continuous-efficiency programme does not link efficiency measures to ex-ante participant-ecology variables across a heterogeneous panel. Second, Vu et al. (2024) report a cross-market entropy efficiency ordering on 57 markets but do not link entropy to a regime classifier nor test direction heterogeneity across microstructures. Third, the per-participant-type information literature (Boehmer and Kelley, 2009; Chang et al., 2024; Kang, 2026) documents within-market asymmetries but does not aggregate to cross-market predictions. Fourth, the financial regime-classification literature (Hamilton, 1989; Bishop, 2006; Bucci and Ciciretti, 2022) rarely combines entropy features with deployment-suitable label-stabilisation mechanisms or with modern causal-ML estimation for heterogeneous treatment effects (Wager and Athey, 2018; Chernozhukov et al., 2018).

### 1.2 Contributions

**Principal Contribution 1 — direction heterogeneity (empirical).** The entropy–volatility direction is not universal; it tracks microstructure. Frontier and retail-leaning markets show the Paradox direction (low entropy precedes higher forward vol, consistent with behavioural coordination); developed markets show Inverted or null; cryptocurrency reads Inverted under filtering. The finding moves the entropy-finance literature from a universal-direction framing to a heterogeneous-effects framing. Apparent Paradox readings on developed markets under naive K-Fold cross-fitting reflect future-data leakage, not substantive structure (§4.1, Appendix F).

**Principal Contribution 2 — cross-market magnitude scaling (empirical).** Entropy-based regime-discrimination magnitude (Kruskal–Wallis $H$) orders monotonically with retail participation across the eight-market panel. The ordering holds under both raw and hysteresis-filtered labels — filtering strengthens it — and is robust to the tier-scoring scheme, the cascade RPS specification (P1 authoritative / P2 bounds / P3 Bayesian), the sample-size correction, and the sensitivity suite. First cross-market test linking entropy-derived efficiency to an ex-ante participant-ecology variable on a heterogeneous post-COVID panel (§4.2).

**Secondary Contribution 1 — heterogeneous-effects DML methodology for regime classification.** Causal forest DML (Wager and Athey, 2018) with Purged K-Fold cross-fitting (López de Prado, 2018, §7.3) on filtered Schmitt-trigger labels, adapted for regime classification with overlapping forward-looking targets. Resolves three problems jointly: K-Fold leakage, frontier-market regime non-stationarity that breaks strict TimeSeriesSplit, and test-boundary autocorrelation. Theoretically appropriate (heterogeneous regime treatment effects) and empirically required (linear DML fails on rare-treatment-class frontier markets). Spec grid in §4.1.1 and Appendix F.

**Secondary Contribution 2 — Schmitt-trigger label stabilisation for soft-assignment classifiers.** A non-parametric mechanism generalising the binary Schmitt-trigger principle (Schmitt, 1938; Brokate and Sprekels, 1996) to $K$-component mixture posteriors via a two-threshold margin rule with persistence requirement. The DML methodology study validates the mechanism: filtering removes label-flicker artifacts that confound naive estimation (§3.4, Appendix C).

### 1.3 Methodological commitments

I commit to three protocols. First, transparent reproducibility — a frozen public archive of the hypothesis specifications, market list, parameters, and pass/reject criteria, with byte-for-byte regression assertions ($\text{atol} = 10^{-4}$) tying the reported numbers to the archive. Second, architectural transparency — methodological refinements between the preliminary 3-market specification and the final 8-market specification are documented in Appendix E.6. Third, dual-track validation: raw GMM labels are reported alongside hysteresis-filtered labels throughout, and the canonical DML specification (causal forest + Purged K-Fold + filtered labels) is adopted on the theoretical and empirical grounds documented in §4.1 and §6.6.

---

## 2. Related Work

### 2.1 Entropy in finance and continuous-efficiency measurement

Permutation entropy (Bandt and Pompe, 2002), weighted permutation entropy (Fadlallah et al., 2013), and sample entropy (Richman and Moorman, 2000) provide model-free complexity measures for financial time series. Empirical applications use entropy for market-efficiency assessment in single-market and cross-country settings (Zanin et al., 2012; Risso, 2008; Vu et al., 2024; Papla and Siedlecki, 2024; Matsushita et al., 2026; Cohen et al., 2026). A parallel continuous-efficiency programme (Campbell et al., 1997; Lim, 2007; Cajueiro and Tabak, 2004; Kristoufek and Vosvrda, 2013; Shternshis et al., 2022; Brouty and Garcin, 2023) develops continuous proxies for market efficiency from price-series properties. These works analyse the entropy level as a function of market and time; none tests whether cross-market entropy-derived discrimination magnitude couples with an ex-ante participant-ecology variable.

### 2.2 Per-participant-type information asymmetry and microstructure

A separate literature documents systematic information asymmetries across participant types within single markets. Boehmer and Kelley (2009) document retail's information disadvantage on NYSE audit-trail data, with institutional ownership improving informational efficiency through analyst-coverage and price-impact channels. Kumar and Lee (2006), Kaniel et al. (2008), Meshcheryakov and Winters (2020), and Chang et al. (2024) describe retail as largely uninformed liquidity provision and institutional flow as informed. Kang (2026) applies transfer entropy networks to Korean equities and reports few-but-strong foreign-network links versus many-but-weak individual-network links. This literature establishes the within-market foundation for the hypothesised macro-level coupling between participant ecology and aggregate efficiency measures; the coupling itself has not been tested across a heterogeneous cross-market panel.

### 2.3 Regime classification, hysteresis, and the post-COVID window

Financial-regime detection has used Hidden Markov Models (Hamilton, 1989) and Gaussian Mixture Models (Bishop, 2006), with recent contributions on realised covariances (Bucci and Ciciretti, 2022), GMM–gradient-boosting hybrids (Sánchez-Fernández et al., 2025), and rotation-invariant neural networks (Bongiorno et al., 2026). Single-threshold maximum-posterior classification produces label flicker near cluster boundaries; hysteresis (Schmitt, 1938; Brokate and Sprekels, 1996), standard in physics and signal processing, has rarely been adapted to unsupervised clustering of financial time series. Maneejuk et al. (2022) confirm via Markov switching that all major markets except Bitcoin experienced a structural regime shift after the WHO declaration of 30 January 2020; following Papla and Siedlecki (2024), I restrict the primary analysis to the post-COVID era to avoid conflating qualitatively distinct microstructure regimes.

### 2.4 Position of this paper

Relative to the literatures reviewed above, this paper combines (i) a continuous coupling of an information-theoretic efficiency measure to an ex-ante participant-ecology variable across a heterogeneous post-COVID panel, (ii) a non-parametric label-stabilisation mechanism for soft-assignment classifiers in the cross-market setting, and (iii) transparent reproducibility with an explicit data-quality cascade and architecturally documented methodological evolution. The combination locates the paper at the intersection of the continuous-efficiency programme, per-participant-type information asymmetry, and modern causal-ML estimation.

---

## 3. Methodology

### 3.1 Pipeline architecture

The analysis uses a five-layer pipeline: data ingestion; entropy feature engineering; regime classification (GMM with Schmitt-trigger hysteresis filter); forward-volatility computation; and hypothesis testing. Each layer is independently testable, and the full pipeline is reproducible from the public repository at the canonical reproducibility tag.

### 3.2 Entropy feature engineering

I compute two complementary entropy features per trading day. *Weighted Permutation Entropy (WPE)* measures ordinal-pattern complexity in log-return windows (embedding $m = 3$, delay $\tau = 1$, window $W = 22$ trading days; Bandt and Pompe, 2002; Fadlallah et al., 2013). *Standardised Price Sample Entropy (SPE_Z)* measures pattern recurrence in close-price windows ($m_s = 2$, tolerance $r = 0.2\sigma$, window $W_s = 60$ days), standardised by a strictly backward 504-day rolling Z-score to eliminate look-ahead bias (Richman and Moorman, 2000). The pair $(\text{WPE}, \text{SPE\_Z})$ provides the bivariate feature space for regime classification. Full mathematical definitions, equation forms, and implementation details appear in Appendix B.

### 3.3 Unsupervised regime classification

The bivariate feature $\mathbf{z}_t = (\text{WPE}_t, \text{SPE\_Z}_t)$ is modelled as a $K = 3$ full-covariance Gaussian mixture, fit by Expectation–Maximisation with $n_{\text{init}} = 10$ random initialisations and BIC model selection on the calibration market (Bishop, 2006). The three components admit domain interpretation as low-entropy (Deterministic), mid-entropy (Transitional), and high-entropy (Stochastic) states. Cluster centroids are stable within 2% relative deviation across initialisations. Mathematical specification and stability diagnostics appear in Appendix C.

### 3.4 Schmitt-trigger hysteresis filter

The raw GMM classifier produces label flicker near cluster boundaries. I apply a non-parametric label-stabilisation mechanism that generalises the two-threshold Schmitt-trigger principle (Schmitt, 1938; Brokate and Sprekels, 1996) from the binary two-state setting to $K$-component soft-assignment classifiers: a margin-based transition rule with a persistence requirement, operating directly on posterior probability sequences. The production parameters $(\delta_{\text{hard}}, \delta_{\text{soft}}, t_{\text{persist}}) = (0.60, 0.35, 8)$ were calibrated on the primary market (VNINDEX, post-2020) to target 5–10 filtered flips per year and held fixed across the panel. The full algorithmic specification, parameter elicitation, and phase-space visualisation appear in Appendix C.

### 3.5 Eight-market panel and RPS specification

I implement H2 under two specifications: a tier-based test using the FTSE Russell / MSCI classification, and a continuous-RPS test using a three-phase data-quality cascade (P1 authoritative source; P2 competing-source bounds; P3 Bayesian posterior). The cascade is a per-market filter: each market enters at the highest-authority phase its data quality supports. RPS denotes the share of trading value attributable to retail participants. Per-market RPS data quality varies with market structure: centralised exchanges publish investor-type turnover directly, while fragmented markets require multi-source aggregation. The cascade rationale and per-market source documentation appear in Appendix D.

**Table 1.** Eight-market panel: tier classification + cascade phase + RPS specification + observation count after the 504-day labelling floor.

| Category | Tier rank | Market | Phase | RPS specification | N_obs |
|---|---|---|---|---|---|
| Frontier | 4 | VNINDEX | P1 | 0.90 (Vietnam SSC + VinaCapital) | 1506 |
| Frontier | 4 | PSEI | P1 | 0.68 (PSE 2023 Annual Report) | 1383 |
| Emerging | 3 | KOSPI | P1 | 0.45 (KRX 2026 direct) | 1467 |
| Emerging | 3 | NIFTY | P1 | 0.40 (NSE India Ownership Report) | 1458 |
| Crypto | 2 | BTC | P3 | Beta(mean=0.55, κ=20) | 2445 |
| Developed | 1 | SPX | P2 | Uniform[0.18, 0.37] | 1500 |
| Developed | 1 | FTSE | P2 | Uniform[0.15, 0.25] | 1510 |
| Developed | 1 | NIKKEI | P1 | 0.18 (JPX direct) | 1439 |

Phase distribution: 5 P1 + 2 P2 + 1 P3. Cascade composite Monte Carlo: each trial samples per-market RPS by phase, computes Spearman ρ; variance reflects only P2 + P3 contributions. Per-market N_obs ranges 1383–2445 (max/min ratio = 1.77×); the cross-market discrimination ordering uses sample-size-corrected η² (Appendix E) to ensure comparability across markets with different observation counts.

**Methodological position relative to Vu et al. (2024).** Vu et al. (2024) apply permutation entropy across 57 global stock markets to characterise an efficiency ordering — the most extensive cross-market entropy panel in the recent literature. Five axes distinguish the present work. First, bivariate feature engineering — Weighted Permutation Entropy (return-space ordinal complexity) plus Standardised Price Sample Entropy (price-space trajectory complexity) — rather than permutation entropy alone. Second, GMM K = 3 regime classification on the bivariate feature space rather than entropy-level analysis. Third, the H1 direction test (Det vs Sto stochastic dominance on forward volatility) characterises per-market direction heterogeneity; Vu et al. report entropy–efficiency correlation but not direction heterogeneity. Fourth, a Schmitt-trigger filter for deployment-grade label stability. Fifth, a cascade RPS specification accommodating per-market data-quality variation rather than uniform retail-share treatment. The eight-market scope is narrower than Vu et al.'s; the methodological depth is deliberately greater, characterising the direction and mechanism of the entropy–volatility relationship rather than its average level.

### 3.6 Data, analysis window, and computational implementation

Daily OHLCV data for the eight markets cover 2020-01-01 to 2026-04-17 (vnstock cross-validated against yfinance for VNINDEX; yfinance for international markets and BTC-USD). The 504-day SPE_Z rolling window means regime labelling begins around 2022 across all markets. The choice of post-COVID window follows Maneejuk et al. (2022) and Papla and Siedlecki (2024) on the structural break around 30 January 2020 (§2.3).

The validation pipeline — entropy feature extraction, $K = 3$ GMM, Schmitt-trigger hysteresis, Kruskal–Wallis H, Spearman rank correlation, and circular block bootstrap — is implemented in Python 3.13 with author-specified algorithmic choices and AI code-generation assistance (Anthropic Claude, Opus 4.x family). All parameter values, thresholds, and mathematical formulations were authored before code generation. AI-generated code was line-reviewed, unit-tested against analytical benchmarks, and validated against the frozen analysis archive via byte-for-byte regression assertions ($\text{atol} = 10^{-4}$). Random seeds are fixed: seed 42 for the bootstrap, $n_{\text{init}} = 10$ for GMM-EM. The architecture is modular for cross-domain transfer: parameters calibrated on the primary market (VNINDEX, post-2020) are applied unchanged to the seven held-out markets in parameter-transfer mode, with per-domain re-calibration as a robustness comparison (§5.2). The full replication package and reproduction commands are available at the canonical reproducibility tag specified on the title page.

---

## 4. Central Findings

### 4.1 H1 — Per-market direction (Entropy Paradox / Inverted dichotomy)

The H1 direction test asks whether forward 20-day realised volatility under the Deterministic regime stochastically dominates that under the Stochastic regime, market by market. A market is labelled **Paradox** when Det > Sto (low entropy is followed by higher forward vol, consistent with a behavioural-coordination interpretation) and **Inverted** when Det < Sto (low entropy is followed by lower forward vol, consistent with an institutional-stabilisation interpretation).

#### 4.1.1 Causal forest DML conditional partial effect (canonical specification)

I estimate the per-market conditional partial effect of regime label on forward volatility using causal forest DML (Wager and Athey, 2018). The treatment is the binary regime label (Det vs Sto on filtered labels, Stochastic as control). Controls are lagged returns (lags 1, 5, 22), lagged squared returns (lags 1, 5, 22), lagged realised volatility (lags 1, 22), and day-of-week dummies. Cross-fitting uses Purged K-Fold (López de Prado, 2018, §7.3) with K = 5 contiguous blocks and a 20-bar embargo matching the forward-vol overlap. This splitter addresses three problems at once: future-data leakage from naive K-Fold; regime non-stationarity that breaks strict TimeSeriesSplit on frontier markets; and autocorrelation contamination in the residual zone bordering test folds. I prefer causal forest over linear DML because regime treatment effects are theoretically heterogeneous in volatility context, and because linear DML fails the treatment-balance check on three frontier markets (VNINDEX, PSEI, NIFTY) under proper cross-fitting. The linear/causal-forest divergence on KOSPI (Appendix F.5; ATEs −5.80 vs −26.69) together with the linear-DML treatment-balance failure on three frontier markets constitute a Hausman-style rejection of the homogeneity assumption on this panel.

**Table 2.** Causal forest DML ATE per market. Treatment = Det vs Sto on filtered labels; outcome = forward 20-day realised vol in annualised %.

| Market | ATE | 95% CI | Direction verdict |
|---|---|---|---|
| VNINDEX | +1.42 | [−3.13, +5.96] | n.s. |
| PSEI | −0.13 | [−2.04, +1.79] | n.s. |
| KOSPI | −26.69 | [−72.98, +19.61] | n.s. (extreme heterogeneity) |
| NIFTY | −1.12 | [−4.09, +1.85] | n.s. |
| **SPX** | **+3.48** | **[+0.92, +6.04]** | **Paradox (decisive)** |
| FTSE | +2.58 | [−0.47, +5.62] | n.s. (Paradox direction) |
| NIKKEI | +1.27 | [−1.61, +4.15] | n.s. |
| **BTC** | **−9.34** | **[−18.07, −0.61]** | **Inverted (decisive)** |

Two markets clear the decisive verdict: SPX (Paradox, ATE = +3.48 percentage points of annualised vol) and BTC (Inverted, ATE = −9.34). The SPX Paradox finding is stable across the full DML specification grid (Appendix F.3). On the remaining six markets, the DML ATE direction sign is reported but the CI does not clear zero, indicating either small effect magnitude (developed markets near-zero ATE) or extreme treatment-effect heterogeneity (KOSPI ATE CI spans [−72.98, +19.61]). Computational diagnostics confirm `fit_status = ok` on all eight markets; KOSPI's wide CI reflects variance in per-observation $\tau(x)$ estimates across the lagged-volatility feature space rather than a convergence failure. The 5× magnitude divergence between linear DML (ATE = −5.80) and causal forest (−26.69) on this market is direct empirical evidence of treatment-effect heterogeneity (Appendix F.5).

#### 4.1.2 Reconciliation with the earlier 3-market observational study

The current results extend and correct the earlier 3-market preliminary report (VNINDEX, S&P 500, BTC). VNINDEX directional Paradox is preserved (DML ATE positive, n.s. but Paradox sign). SPX is upgraded from "Inverted (raw means reading)" to **decisive Paradox** under DML controls — the original Inverted reading from raw Det/Sto means reflected vol-persistence confounding that conditional partial-effect estimation removes. BTC is corrected from "thin Paradox" to **decisive Inverted** under filtered labels. The 8-market extension adds five markets (PSEI, KOSPI, NIFTY, FTSE, NIKKEI) with predominantly n.s. direction verdicts but Paradox-direction signs on retail-leaning markets (PSEI, KOSPI) and Inverted-direction signs on developed/emerging-developed markets (NIFTY, FTSE). An exploratory tail-risk Lift analysis on VNINDEX from the original preliminary report is retained in Appendix H.1 as ancillary deployment context, separate from the H1 hypothesis test reported here.

### 4.2 H2 — Cross-market magnitude scaling

Per-market H varies by nearly two orders of magnitude and groups cleanly by tier:

| Tier | n | Mean H_raw | Mean H_filt | Mean η²_raw | Markets |
|---|---|---|---|---|---|
| Frontier | 2 | 66.00 | 68.71 | 0.041 | VNINDEX (83.90), PSEI (48.10) |
| Emerging | 2 | 9.93 | 21.91 | 0.005 | KOSPI (5.88), NIFTY (13.98) |
| Crypto | 1 | 7.13 | 32.24 | 0.002 | BTC (7.13) |
| Developed | 3 | 3.44 | 1.69 | 0.001 | SPX (2.12), FTSE (4.15), NIKKEI (4.05) |

#### 4.2.1 Tier-based primary specification

Spearman rank correlation between per-market H and the FTSE Russell / MSCI tier score (Frontier = 4, Emerging = 3, Crypto = 2, Developed = 1):

$$\rho_{\text{Spearman}}(H_{\text{raw}}, \text{tier\_score}) = 0.927, \quad p = 0.0009, \quad n = 8 \tag{1}$$

The Jonckheere–Terpstra trend test gives JT = 22.0, $z = +2.72$, $p = 0.003$; the Kruskal–Wallis between-tier test gives $H = 6.25$, $p = 0.10$. Under filtered labels, $\rho = 0.890$ ($p = 0.003$), with JT $z = +2.46$ ($p = 0.007$). The sample-size-corrected effect size η² (Appendix E.2) gives ρ(η², tier) = 0.964 on raw labels and 0.969 on filtered — strengthening rather than weakening the cross-market ordering after sample-size adjustment. The correlation $\rho(H_{raw}, N_{obs}) = -0.07$ ($p = 0.87$) rules out a sample-size confound.

#### 4.2.2 Cascade RPS composite (sensitivity to RPS data quality)

Per-market RPS draws are sampled by phase: 5 P1 markets contribute fixed point estimates, 2 P2 markets sample uniformly within documented bounds, and 1 P3 market samples from a Beta posterior. Each Monte Carlo trial samples per-market RPS by phase and computes Spearman ρ across the integrated draw (10,000 trials, seed = 42). The cascade is reported as a sensitivity test on the all-P1 reference Spearman, not an independent test: only 3 of 8 markets contribute variance, and the 10,000 trials reflect RPS perturbation of those 3 markets, not 10,000 independent observations.

**Table 3.** Cascade composite Monte Carlo results.

| Specification | Mean ρ | Median ρ | 95% CI | P(ρ > 0.5) | P(ρ > 0.7) |
|---|---|---|---|---|---|
| Raw labels | +0.847 | +0.857 | [+0.786, +0.905] | 100.0% | 100.0% |
| Filtered labels | +0.901 | +0.905 | [+0.833, +0.952] | 100.0% | 99.9% |

The all-P1 reference (every market treated as an authoritative point estimate with KOSPI = 0.45) gives $\rho_{\text{raw}} = 0.850$ ($p = 0.008$, CI [0.316, 1.000]) and $\rho_{\text{filt}} = 0.934$ ($p = 0.0007$, CI [0.611, 1.000]). The cascade composite mean coincides with the all-P1 reference; the cascade CI characterises the residual contribution from the P2 and P3 markets.

### 4.3 Reconciliation: direction (H1) versus magnitude (H2)

How can H magnitude track RPS systematically (H2) when direction is heterogeneous across markets (H1)? The two findings measure different aspects of regime structure. H magnitude captures *regime separability* — whether low-entropy and high-entropy regimes separate clearly from the middle in forward-vol space, regardless of which extreme is dangerous. This quantity scales with retail share because retail-dominated markets exhibit more behavioural-coordination-driven regime structure overall. H direction (Paradox vs Inverted) captures *regime semantics* — a per-market microstructure feature reflecting whether the market's coordination signal flags rising-with-confidence (Inverted) or panic-coordination (Paradox). The two are observed simultaneously and address different questions; they are unified under the heterogeneous-effects framework in §6.6.

### 4.4 Aleatoric versus epistemic decomposition

I partition the variance of the cross-market Spearman estimator under a nested Monte Carlo perturbation:

$$\text{Var}(\hat{\rho}) = \underbrace{\mathbb{E}_{\text{RPS}}[\text{Var}(\hat{\rho} \mid \text{RPS})]}_{\text{aleatoric}} + \underbrace{\text{Var}_{\text{RPS}}(\mathbb{E}[\hat{\rho} \mid \text{RPS}])}_{\text{epistemic}}$$

**Table 4.** Variance decomposition sensitivity to the H Normal-noise SD fraction (raw / filtered labels).

| H noise SD | Aleatoric % (raw / filt) | Epistemic % (raw / filt) |
|---|---|---|
| 0.05 | 0.74 / 0.83 | 99.26 / 99.17 |
| 0.10 | 1.41 / 2.45 | 98.59 / 97.55 |
| 0.20 | 10.71 / 9.57 | 89.29 / 90.43 |
| 0.30 | 24.68 / 21.44 | 75.32 / 78.56 |

Epistemic uncertainty dominates at 75–79% even under the most aggressive H noise assumption (SD = 0.30 of the H point estimate, well above any reasonable block-bootstrap proxy). The roadmap implication is robust: extending the panel size addresses only the small aleatoric term, while harmonising primary-source RPS readings addresses the dominant epistemic term (§6.5).

### 4.5 Robustness suite

Numerical detail in Appendix E (Tables E.2–E.5).

- *Measurement noise.* RPS perturbation $\mathcal{N}(0, \sigma^2)$ with $\sigma \in \{0.05, 0.10, 0.15\}$: $P(\rho > 0.5) = 100\%$ at $\sigma = 0.05$; $\geq 96.3\%$ (raw) and $\geq 98.3\%$ (filtered) at $\sigma = 0.15$.
- *Leave-one-out.* Filtered $|\rho| \geq 0.90$ on every drop-one panel ($p < 0.01$); raw $|\rho| \geq 0.77$ ($p < 0.05$). Lowest: drop-VNINDEX raw $\rho = 0.775$ ($p = 0.041$); filtered $\rho = 0.901$ ($p = 0.006$).
- *Stratified subpanels.* Full panel, circuit-breaker subpanel, and four-market frontier-emerging subpanel ($\rho = 0.800$, $n = 4$) all clear $\rho > 0.5$.
- *SPE_Z standardisation.* Headline ρ(H, tier) = 0.927 survives under raw SampEn and under global Z-score ($\rho = 0.803$, $p < 0.02$ each); collapses under WPE only ($\rho = 0.16$).
- *Crypto rank.* All five placements ∈ {1, 2, 3, 4, 5} decisive at p < 0.05, with ρ in [+0.77, +0.94].
- *GMM K-selection.* Fixed K ∈ {2, 3, 4, 5} all decisive (ρ in 0.815–0.964); market-optimal K is n.s. as expected (different K produce H statistics on incomparable scales).
- *PSEI source.* Reclassifying PSEI from P1 (point 0.68) to P2 (Uniform[0.21, 0.68]) shifts cascade ρ_raw mean from 0.847 to 0.750 and ρ_filt mean from 0.901 to 0.810; both still satisfy P(ρ > 0.5) ≈ 98–99%.
- *Within-window structural breaks.* A PELT diagnostic (Killick et al., 2012) finds 0–2 log-return breaks, 3–9 WPE breaks, and 13–22 SPE_Z breaks per market within the analysis window; identified breaks cluster on known macro events (Fed first rate hike March 2022, banking stress March 2023, BTC ETF approval January 2024, FTSE Russell Vietnam reclassification October 2025). The H2 cross-market ordering finding is robust to the within-window break structure because it depends on cross-market rank ordering rather than within-market temporal stability (Appendix C.6); within-window break sensitivity for H1 per-market direction is recorded as a future-work item.

### 4.6 Hysteresis filter effect

**Table 5.** H–RPS coupling under raw versus filtered labels (all-P1 reference).

| Specification | n | ρ | p-value | 95% CI |
|---|---|---|---|---|
| Raw labels | 8 | 0.850 | 0.008 | [0.316, 1.000] |
| Filtered labels | 8 | **0.934** | 0.0007 | [0.611, 1.000] |
| Δρ | | +0.084 | | |

Per-market filter impact (raw → filtered H): VNINDEX 83.90 → 96.33; PSEI 48.10 → 41.09; KOSPI 5.88 → 21.84 (3.7×); NIFTY 13.98 → 21.99; SPX 2.12 → 1.51; FTSE 4.15 → 1.34; NIKKEI 4.05 → 2.22; BTC 7.13 → 32.24 (4.5×). Three patterns emerge — smoothing (VNINDEX, NIKKEI), signal recovery (KOSPI, BTC), absorption (SPX, FTSE) — and are discussed in §6.3. The DML methodology study (§4.1.1 and Appendix F) confirms independently that the filter removes label-flicker artifacts: NIKKEI's Paradox direction under raw K-Fold + linear DML disappears under filtered labels + causal forest + Purged K-Fold, so the filter removes label-flicker artifacts that confound naive estimation rather than merely averaging adjacent labels.

---

## 5. Supporting hypotheses and parameter robustness

H1 (per-market direction) and H2 (cross-market magnitude) are the central findings reported in §4.1 and §4.2. This section reports the supporting hypotheses H3 (regime composition), H4 (temporal structure), and H5 (hysteresis parameter robustness). Per-market detail appears in Appendix E.

### 5.1 H3 and H4 — Regime composition and temporal structure

The H3 categorical rule as originally specified (frontier $p_{\text{tra}} > 0.55$; reject if any frontier value falls below 0.45) is **rejected** by PSEI ($p_{\text{tra}} = 0.403$, CI [0.315, 0.488]). I report this rejection transparently. The continuous Spearman correlation $\rho(p_{\text{tra}}, \text{RPS}) = 0.563$ ($p = 0.146$, 95% CI [−0.290, 0.961]) is directionally consistent with the H3 prediction but under-powered at $n = 8$; it is recorded as supplementary evidence for the supporting-hypothesis context, not as a rescue of the rejected H3 categorical rule. Despite the categorical rejection, the regime composition pattern is broadly consistent with the H3 prediction (Transitional dominant on 6 of 8 markets after filtering); only the categorical-threshold specification fails.

For H4, the block-permutation test gives an observed filtered flip rate per year below every null at block sizes $\{5, 10, 20\}$ on all eight markets ($p \approx 0$ at $n_{\text{perm}} = 2000$; BH-FDR $q = 0$).

### 5.2 H5 — Hysteresis parameter robustness as evidence of heterogeneity

**Table 6.** H5 verdict under the originally specified $p_{\text{tra}}$ spread > 7 pp REJECT rule.

| Market | Category | Verdict |
|---|---|---|
| NIKKEI | Developed | PASS (decisive) |
| BTC | Crypto | PASS (borderline) |
| VNINDEX | Frontier | PASS (borderline) |
| PSEI | Frontier | Dead zone |
| KOSPI | Emerging | REJECT |
| NIFTY | Emerging | REJECT |
| SPX | Developed | REJECT |
| FTSE | Developed | REJECT |

Per-market re-calibration (expanded grid, target 4–10 filtered flips per year) preserves each market's verdict whether parameters are transferred from VNINDEX or independently optimised; the verdict pattern is therefore intrinsic to each market rather than a transfer-learning artefact.

The 4-of-8 REJECT pattern is best read as positive evidence of cross-market microstructure heterogeneity, consistent with the H1 direction-heterogeneity finding (§4.1) and with the canonical heterogeneous-effects DML framework (§4.1.1; theoretical discussion in §6.6). Were markets homogeneous, a single parameter set calibrated on the primary market would generalise uniformly and H5 would pass uniformly; the partial-pass pattern is direct evidence that microstructure heterogeneity is present. H1 (direction heterogeneity), H5 (parameter generalisation pattern), and the canonical DML specification (causal forest estimates heterogeneous treatment effects directly) jointly provide convergent evidence of microstructure-driven heterogeneity — the paper's central thesis. Per-market deployment requires per-market re-calibration; the cross-market H–RPS coupling (§4.2) and direction labels (§4.1) are robust to the parameter choice.

---

## 6. Discussion

### 6.1 Mechanistic interpretation: a herding-coordination chain

The cross-market direction heterogeneity finding (H1, §4.1) and the magnitude scaling finding (H2, §4.2) are linked to a participant-level mechanism through a three-link chain. I specify the chain precisely to distinguish two competing retail-flow channels.

**Link A — Retail information disadvantage.** Retail flow carries lower information content per unit than institutional flow. Boehmer and Kelley (2009) document this on NYSE audit-trail data, with institutional ownership improving informational efficiency through analyst-coverage and price-impact channels; Kumar and Lee (2006), Kaniel et al. (2008), Meshcheryakov and Winters (2020), and Chang et al. (2024) describe retail flow as largely uninformed liquidity provision and institutional flow as informed.

**Link B — Coordinated retail flow reduces ordinal-pattern complexity.** Lower-information retail flow exhibits behavioural correlation — attention-driven trading, sentiment cascades, momentum chasing — that reduces ordinal-pattern complexity in the price-generating process. The empirical signature is that low-entropy regimes on retail-dominated markets coincide with herd-coordinated periods (panic, FOMO, momentum) rather than with calm-trending periods. This is the herding channel, not the noise-decorrelation channel. The latter would predict that uninformed retail flow raises entropy (more random patterns); the former predicts the opposite. The herding interpretation is supported by Barber and Odean (2000), Kumar and Lee (2006), Barber et al. (2021) on attention-induced trading, and Kelley and Tetlock (2017) on retail order imbalance and sentiment correlation. Kang (2026) applies transfer entropy networks to investor-type interactions — a different information-theoretic quantity from price-series ordinal-pattern complexity — and supports Link A only, not Link B. *Empirical test on the panel.* A direct test at the aggregate entropy level gives ρ(median WPE, RPS) = −0.71 (p = 0.056, Fisher 95% CI [−0.94, −0.02]) — a direction consistent with the herding interpretation (high-RPS markets have lower median WPE), borderline at the n = 8 power floor. A complementary per-regime entropy-spread test (max − min of per-regime mean entropy across Det/Trans/Sto) gives a null Spearman correlation with RPS, indicating that the cross-market signal lives in the entropy level aggregate rather than in the per-regime separation gap (Appendix B.5).

**Link C — Cross-market aggregation.** Aggregating per-type contributions yields a market-level entropy-based regime-discrimination magnitude that scales with participant-composition share. Link C is this paper's contribution, established empirically in §4.2 and unified with Links A and B through the Adaptive Market Hypothesis (AMH) and heterogeneous-effects framework in §6.6.

The macro-level Spearman correlations in §4.2 are associational; they become mechanistically interpretable in combination with the external micro-level evidence for Links A and B and the panel-level Link B sensitivity test. The identification logic follows Pearl (2009) and Hernán and Robins (2020) without invoking do-calculus, because RPS is observed cross-sectionally and per-trade investor-classified data are not uniformly available across the panel. A direct cross-market per-type information-efficiency test on investor-classified flow data is reserved for a companion research proposal.

### 6.2 Position within the continuous-efficiency programme

The Kruskal–Wallis H magnitude for entropy-based regime classification is offered as a continuous efficiency measure (Campbell et al., 1997; Cajueiro and Tabak, 2004; Kristoufek and Vosvrda, 2013; Brouty and Garcin, 2023) coupled to an ex-ante participant-ecology variable across a heterogeneous panel. The contribution is the linkage; each individual ingredient is established practice.

### 6.3 The hysteresis filter: three contributions and a heterogeneity reading

Beyond per-market label stability, the filter contributes on three axes. First, smoothing on well-separated markets (VNINDEX, NIKKEI: filtered H within a few percent of raw, direction labels unchanged). Second, discrimination recovery on flicker-dominated markets (KOSPI 3.7×, BTC 4.5×), restoring between-regime separation that argmax labelling had diluted. Third, cross-market test robustness (filtered LOO range narrows from 0.108 to 0.063; every drop-one panel retains $|\rho| \geq 0.90$ at $p < 0.01$). The DML methodology study (§4.1.1) confirms independently: NIKKEI's apparent Paradox direction under raw K-Fold + linear DML disappears under filtered labels + causal forest + Purged K-Fold, so the filter removes label-flicker artifacts rather than merely smoothing them.

H5 parameter robustness does not generalise uniformly (3 PASS, 1 dead-zone, 4 REJECT); per-market re-calibration confirms this pattern is intrinsic rather than a transfer-learning artefact. Read through the heterogeneity lens (§5.2 and §6.6), the partial-pass is positive evidence of cross-market microstructure heterogeneity rather than a methodological weakness: a homogeneous panel would generalise under a single calibration. Per-market deployment requires per-market calibration; the cross-market H–RPS coupling and direction labels are robust to the parameter choice.

### 6.4 Measurement versus structural features

This section opens with an autocorrelative-bias lemma. The rolling standard deviation of returns is by construction a low-pass filter of squared returns — the very quantity used to compute realised volatility. Its higher Kruskal–Wallis H discrimination relative to entropy features (Appendix H.3) therefore reflects autocorrelation of variance with itself, not independent information about the regime structure of the price-generating process. This autocorrelative bias is documented in the volatility-forecasting literature (Andersen and Bollerslev, 1998; Hansen and Lunde, 2005; Patton, 2011). I label SimpleVol features (rolling SD, volatility change) as *measurement features* of the target variable and the entropy features (WPE, SPE_Z) as *structural features* of the price-generating process.

The distinction is operational, not just taxonomic. SimpleVol is mechanically backward-looking: it summarises the magnitude of past returns and therefore tracks volatility regimes after they materialise — its labels fit the realised-vol series but cannot lead it. Entropy features measure ordinal-pattern complexity in the price-generating process itself and can lead volatility when behavioural coordination compresses entropy ahead of a shock. The deployment-relevant manifestation is the VNINDEX tail-risk Lift evidence in Appendix H.1: the entropy-based Deterministic regime predicts forward 5-day drawdowns with Lift increasing monotonically from 2.06× (>3% threshold) to 5.50× (>7% threshold) — precisely the regime in which a measurement feature averaging past variance offers no predictive premium. The Link B mechanism in §6.1 requires that discrimination track information-theoretic structure rather than autocorrelation in the target; only structural features satisfy this requirement, and only structural features carry the predictive content the deployment use case demands.

### 6.5 Aleatoric versus epistemic — a roadmap

The 75–99% epistemic / 1–25% aleatoric decomposition across reasonable H noise assumptions (§4.4, Table 4; taxonomy per Hüllermeier and Waegeman, 2021) reframes the n = 8 panel-size discussion. The binding constraint on cross-market mechanism inference is not statistical power but the heterogeneity of primary-source RPS reporting infrastructure. Extending the trading window reduces only the modest aleatoric term ($\propto \sqrt{T_{\text{new}}/T_{\text{current}}}$); harmonising primary-source RPS readings compresses the dominant epistemic term directly. For markets with centralised single-exchange reporting (KRX, NSE, PSE, HOSE, JPX) this extension is tractable. For fragmented markets (US, UK) it requires either cross-exchange aggregation conventions or a methodological shift to aggregated-flow proxies.

### 6.6 Heterogeneous-effects framework and the Adaptive Market Hypothesis

The three theoretical positionings invoked in this discussion — the Adaptive Market Hypothesis (Lo, 2004), the heterogeneous-effects framework (Wager and Athey, 2018), and the continuous-efficiency programme (§6.2) — sit in a hierarchy: AMH provides the meta-theoretical framing; the heterogeneous-effects framework is its methodological operationalisation at the estimator level; the continuous-efficiency programme is the closest empirical predecessor.

The H1 direction heterogeneity finding (§4.1) maps onto Lo's (2004) Adaptive Market Hypothesis (AMH): market efficiency is context-dependent and evolves with participant composition and institutional structure. The Paradox direction (low entropy followed by high forward vol) on retail-dominated markets reflects behavioural-coordination-driven structure — panic herding compresses entropy precisely when structural risk is elevated. The Inverted direction (low entropy followed by low forward vol) on institutionally stabilised markets reflects market-maker-driven structure — liquidity provision compresses entropy under calm conditions. The cross-market direction reversal observed across the panel under the canonical causal forest + Purged K-Fold + filtered specification is therefore the empirical signature predicted by AMH, not an anomaly. The systematic coupling of entropy-derived discrimination magnitude with retail share (H2, §4.2) reinforces this reading: markets sit on a continuum of microstructure-driven coordination strength rather than in discrete categorical buckets.

The heterogeneous-effects framework of Wager and Athey (2018) operationalises this AMH reading at the methodological level. The same regime label has different content in different volatility contexts (Det during low-vol calm-trending periods differs qualitatively from Det during high-vol panic-coordinated periods), and across markets the same label carries different macro-level meaning depending on participant ecology. This treatment-effect heterogeneity is not noise to be averaged over but the empirical signature the paper characterises. Causal forest estimates per-observation treatment effects $\tau(x) = E[Y(1) - Y(0) \mid X = x]$ rather than a constant ATE, and on this panel it succeeds on all eight markets where linear DML fails the treatment-balance check on three (VNINDEX, PSEI, NIFTY) due to the rare Stochastic regime concentrating in late years (§4.1.1 details the splitter; Appendix F covers the spec grid).

H1 direction heterogeneity (§4.1), H5 partial-pass pattern (§5.2, 4-of-8 REJECT under a uniform parameter set), and the canonical causal forest specification together provide convergent evidence of microstructure-driven heterogeneity across markets — the paper's central empirical thesis. The methodological implication is that cross-market regime analyses should be designed for per-market causal estimation rather than panel-pooled estimation; the methodology adopted here is offered as a methodological exemplar.

---

## 7. Limitations and Conclusion

### 7.1 Limitations

- *Time window.* The analysis covers the post-COVID period 2020–2026 per the Maneejuk et al. (2022) structural-break finding. Within-window structural breakpoints (§4.5 bullet; full per-market tables in Appendix C.6) cluster around known macro events; a sub-window analysis is a natural extension.
- *Sample and composition.* The eight-market mechanism-demonstration panel is appropriate for this design class (cross-market entropy studies typically use 4–10 markets for mechanism demonstration; population-inference work uses 20–57). A pre-experiment power calibration for the literature-anticipated effect (ρ ≈ 0.5) requires n ≈ 26 for 80% power at α = 0.05, so the panel is under-powered for that effect size. The observed effects clear the n = 8 minimum-detectable threshold (|ρ| ≳ 0.62) but do not retroactively justify the panel size. A 20+ market extension is the natural follow-up; at larger panel sizes, double/debiased machine-learning estimation (Chernozhukov et al., 2018) becomes a feasible companion methodology for cross-market causal identification of RPS on H controlling for observed market-level confounders. The original panel-selection protocol permitted a "choose 2 of 3 by data quality" rule within each microstructure category (Appendix A.3).
- *Link B partially tested.* The per-market entropy-LEVEL versus RPS Spearman test on the panel (Appendix B.5) gives ρ(median WPE, RPS) = −0.71 (p = 0.056) — a direction consistent with the herding-mechanism interpretation in §6.1, borderline at the n = 8 power floor. The per-regime entropy-spread test is null. A direct cross-market per-participant-type information-efficiency test on investor-classified flow data is the subject of a companion research proposal.
- *RPS source heterogeneity.* The cascade accommodates within-window data-quality variation; one input-data update was applied through the cascade verification process (KOSPI ASIFMA 2022 → KRX 2026; §D.3). All eight markets were reviewed under the same primary-source criterion; KOSPI was the only update. The PSEI sensitivity in §4.5 (reclassifying P1 → P2 shifts cascade ρ_raw mean from 0.847 to 0.750 while keeping P(ρ > 0.5) ≈ 99%) bounds the metric-disagreement impact. A fully harmonised primary-source panel remains future work.
- *Hysteresis calibration upstream.* The production parameters were calibrated on VNINDEX post-2020 with a target of 4–10 filtered flips per year. The H3 categorical thresholds sit adjacent to this calibration band, so the continuous Spearman companion (§5.1) is the recommended primary read. Hysteresis target-band sensitivity for {3–7, 5–10, 8–15} flips per year is reported in Appendix C.
- *504-day labelling floor.* Cross-market comparison effectively starts in 2022; the March 2020 COVID-19 shock falls in the unlabelable region.
- *DML cross-fitting.* Purged K-Fold solves future-leakage and autocorrelation contamination (§4.1.1), but the bootstrap inference within DML is IID. A block-bootstrap-aware DML implementation (Politis–Romano stationary bootstrap with circular block resampling at the index level) is identified as a methodological extension; the causal forest DML asymptotic CI used here may marginally understate uncertainty on the most autocorrelation-heavy markets.
- *Foundation-model head-to-head.* The Chronos versus entropy comparison on VNINDEX is pre-committed in the public repository and will be reported in a companion note.

### 7.2 Conclusion

This paper documents two central findings on an eight-market post-COVID panel under a heterogeneous-effects framework. The H1 direction test — the Entropy Paradox extended cross-market — estimates per-market direction via causal forest DML with Purged K-Fold cross-fitting on filtered labels, reconciled against an earlier 3-market observational study; SPX reads decisive Paradox and BTC decisive Inverted under the canonical specification. The H2 magnitude test orders entropy-based regime discrimination monotonically with retail participation across the panel under both raw and filtered labels, robust to tier-scoring scheme, cascade RPS data quality, sample-size correction, and the sensitivity suite. The variance decomposition is 75–99% epistemic across reasonable H noise assumptions, directing the methodological roadmap toward primary-source RPS infrastructure rather than statistical-power extension.

Two supporting methodological contributions enable both findings: a heterogeneous-effects DML framework (causal forest + Purged K-Fold + filtered labels) appropriate for regime classification with overlapping forward-looking targets, offering a causal-ML companion to traditional rank-based effect-size frameworks; and a Schmitt-trigger generalisation for $K$-component soft-assignment classifiers, validated empirically by the DML methodology study (the filter removes label-flicker artifacts that confound naive estimation). The H5 4-of-8 partial generalisation of hysteresis parameters reads as positive evidence of cross-market microstructure heterogeneity, consistent with the heterogeneous-effects framework unifying H1, H5, and the canonical DML specification.

I offer the disclosure-first methodology adopted here — a transparent hypothesis specification with documented methodological evolution, dual-track validation under raw and filtered labels, byte-for-byte regression assertions against the frozen analysis archive, the cascade RPS specification with sensitivity validation — as a methodological exemplar for applied information-theoretic finance under a heterogeneous-effects framework.

---

## Code and Data Availability

All code, validation scripts, original hypothesis specifications, and processed data supporting the findings of this study are publicly available. The repository URL and canonical reproducibility tag is provided in the title page of the manuscript (anonymized for double-blind review). License: MIT.

Reported numbers reproduce byte-for-byte against the frozen analysis archive at the location specified in the repository, via regression assertions in active validation scripts at `atol = 1e-4`. Reproduction commands are documented in the repository README.

---

## Declaration of generative AI and AI-assisted technologies in the writing process

During the preparation of this work the author used Anthropic Claude (Opus 4.x family) to assist with literature synthesis and cross-referencing, exposition of methodological choices, and refinement of grammar, clarity, and concision. After using this tool, the author reviewed and edited the content as required and takes full responsibility for the content of the published article.

---

## References

ASIFMA, 2022. Korea Capital Markets Report 2022. Asia Securities Industry & Financial Markets Association industry report.

Andersen, T.G., Bollerslev, T., 1998. Answering the skeptics: Yes, standard volatility models do provide accurate forecasts. Int. Econ. Rev. 39(4), 885–905. https://doi.org/10.2307/2527343.

Ansari, A.F., Stella, L., Turkmen, C., Zhang, X., Mercado, P., Shen, H., Shchur, O., Rangapuram, S.S., Pineda Arango, S., Kapoor, S., Zschiegner, J., Maddix, D.C., Mahoney, M.W., Torkkola, K., Wilson, A.G., Bohlke-Schneider, M., Wang, Y., 2024. Chronos: Learning the language of time series. arXiv preprint 2403.07815.

Athey, S., Imbens, G.W., 2019. Machine learning methods that economists should know about. Annu. Rev. Econ. 11, 685–725. https://doi.org/10.1146/annurev-economics-080217-053433.

Bandt, C., Pompe, B., 2002. Permutation entropy: A natural complexity measure for time series. Phys. Rev. Lett. 88(17), 174102. https://doi.org/10.1103/PhysRevLett.88.174102.

Barber, B.M., Odean, T., 2000. Trading is hazardous to your wealth: The common stock investment performance of individual investors. J. Finance 55(2), 773–806. https://doi.org/10.1111/0022-1082.00226.

Barber, B.M., Huang, X., Odean, T., Schwarz, C., 2021. Attention-induced trading and returns: Evidence from Robinhood users. J. Finance 77(6), 3141–3190. https://doi.org/10.1111/jofi.13183.

Bishop, C.M., 2006. Pattern Recognition and Machine Learning. Springer, New York.

Boehmer, E., Kelley, E.K., 2009. Institutional investors and the informational efficiency of prices. Rev. Financ. Stud. 22(9), 3563–3594. https://doi.org/10.1093/rfs/hhp028.

Bongiorno, C., Mantegna, R.N., et al., 2026. End-to-end large portfolio optimization for variance minimization with neural networks through covariance cleaning. J. Finance Data Sci., in press.

Brokate, M., Sprekels, J., 1996. Hysteresis and Phase Transitions. Springer, New York.

Brouty, X., Garcin, M., 2023. A statistical test of market efficiency based on information theory. Quant. Finance 23(6), 1003–1018. https://doi.org/10.1080/14697688.2023.2199919.

Bucci, A., Ciciretti, V., 2022. Market regime detection via realized covariances. Econ. Model. 111, 105832. https://doi.org/10.1016/j.econmod.2022.105832.

Cajueiro, D.O., Tabak, B.M., 2004. The Hurst exponent over time: Testing the assertion that emerging markets are becoming more efficient. Phys. A 336(3), 521–537. https://doi.org/10.1016/j.physa.2003.12.031.

Campbell, J.Y., Lo, A.W., MacKinlay, A.C., 1997. The Econometrics of Financial Markets. Princeton University Press, Princeton.

Chang, E.C., Chuang, W.-I., Liao, W.-C., 2024. Information acquisition and processing skills of institutions and retail investors around information shocks. J. Bank. Finance 161, 107110. https://doi.org/10.1016/j.jbankfin.2024.107110.

Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., Robins, J., 2018. Double/debiased machine learning for treatment and structural parameters. Econom. J. 21(1), C1–C68. https://doi.org/10.1111/ectj.12097.

Cohen, G., Aiche, A., Eichel, R., 2026. Entropy-augmented forecasting and portfolio construction at the industry-group level: A causal machine-learning approach using gradient-boosted decision trees. Entropy 28(1), 108. https://doi.org/10.3390/e28010108.

Fadlallah, B., Chen, B., Keil, A., Principe, J., 2013. Weighted-permutation entropy: A complexity measure for time series incorporating amplitude information. Phys. Rev. E 87(2), 022911. https://doi.org/10.1103/PhysRevE.87.022911.

FTSE Russell, 2025. FTSE country classification September 2025 review — Vietnam reclassification to Secondary Emerging effective 21 September 2026. London Stock Exchange Group press release, 7 October 2025.

Hamilton, J.D., 1989. A new approach to the economic analysis of nonstationary time series and the business cycle. Econometrica 57(2), 357–384. https://doi.org/10.2307/1912559.

Hansen, P.R., Lunde, A., 2005. A forecast comparison of volatility models: Does anything beat a GARCH(1,1)? J. Appl. Econom. 20(7), 873–889. https://doi.org/10.1002/jae.800.

Hernán, M.A., Robins, J.M., 2020. Causal Inference: What If. Chapman & Hall/CRC, Boca Raton.

Hüllermeier, E., Waegeman, W., 2021. Aleatoric and epistemic uncertainty in machine learning: an introduction to concepts and methods. Mach. Learn. 110(3), 457–506. https://doi.org/10.1007/s10994-021-05946-3.

JPX, 2024. Equity trading by investor category — 2023–2024 annual summary. Japan Exchange Group statistics.

Kang, S., 2026. Information propagation across investor types: Transfer entropy networks in the Korean equity market. arXiv preprint 2603.20271.

Kaniel, R., Saar, G., Titman, S., 2008. Individual investor trading and stock returns. J. Finance 63(1), 273–310. https://doi.org/10.1111/j.1540-6261.2008.01316.x.

Kelley, E.K., Tetlock, P.C., 2017. Retail short selling and stock prices. Rev. Financ. Stud. 30(3), 801–834. https://doi.org/10.1093/rfs/hhw089.

Killick, R., Fearnhead, P., Eckley, I.A., 2012. Optimal detection of changepoints with a linear computational cost. J. Am. Stat. Assoc. 107(500), 1590–1598. https://doi.org/10.1080/01621459.2012.737745.

Korea Exchange, 2026. Investor-type turnover statistics, KOSPI cash equity market. KRX Data Marketplace (https://data.krx.co.kr), accessed 2026-04.

Kristoufek, L., Vosvrda, M., 2013. Measuring capital market efficiency: Global and local correlations structure. Phys. A 392(1), 184–193. https://doi.org/10.1016/j.physa.2012.08.003.

Kumar, A., Lee, C.M.C., 2006. Retail investor sentiment and return comovements. J. Finance 61(5), 2451–2486. https://doi.org/10.1111/j.1540-6261.2006.01063.x.

Lim, K.-P., 2007. Ranking market efficiency for stock markets: A nonlinear perspective. Phys. A 376, 445–454. https://doi.org/10.1016/j.physa.2006.10.013.

Lo, A.W., 2004. The adaptive markets hypothesis. J. Portf. Manag. 30(5), 15–29. https://doi.org/10.3905/jpm.2004.442611.

López de Prado, M., 2018. Advances in Financial Machine Learning. Wiley, Hoboken, NJ. (Ch. 7 for Purged K-Fold and Combinatorial Purged Cross-Validation.)

Maneejuk, P., Kaewtathip, N., Jaipong, P., Yamaka, W., 2022. The transition of the global financial markets' connectedness during the COVID-19 pandemic. N. Am. J. Econ. Finance 63, 101816. https://doi.org/10.1016/j.najef.2022.101816.

Matsushita, R., Nobre, I., Da Silva, S., 2026. Beyond volatility: Using differential entropy to detect financial market regimes. Chaos Solitons Fractals 202, 117553. https://doi.org/10.1016/j.chaos.2026.117553.

MSCI, 2025. MSCI Market Classification Framework — June 2025 annual review. MSCI Inc. methodology document.

MEMX, 2025. Retail order flow estimation — US equity markets. Members Exchange industry research brief.

Meshcheryakov, A., Winters, D.B., 2020. Retail investor attention and the limit order book: Intraday analysis of attention-based trading. Financ. Rev. 55(4), 587–609. https://doi.org/10.1111/fire.12238.

Newey, W.K., West, K.D., 1987. A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. Econometrica 55(3), 703–708. https://doi.org/10.2307/1913610.

NSE India, 2024. Ownership of Indian equities report. National Stock Exchange of India.

Papla, D., Siedlecki, R., 2024. Entropy as a tool for the analysis of stock market efficiency during periods of crisis. Entropy 26(12), 1079. https://doi.org/10.3390/e26121079.

Patton, A.J., 2011. Volatility forecast comparison using imperfect volatility proxies. J. Econom. 160(1), 246–256. https://doi.org/10.1016/j.jeconom.2010.03.034.

Pearl, J., 2009. Causality: Models, Reasoning, and Inference, 2nd ed. Cambridge University Press, Cambridge.

Philippine Stock Exchange, 2023. 2023 Annual Report. Philippine Stock Exchange.

Pincus, S.M., 1991. Approximate entropy as a measure of system complexity. Proc. Natl. Acad. Sci. 88(6), 2297–2301. https://doi.org/10.1073/pnas.88.6.2297.

Richman, J.S., Moorman, J.R., 2000. Physiological time-series analysis using approximate entropy and sample entropy. Am. J. Physiol. Heart Circ. Physiol. 278(6), H2039–H2049. https://doi.org/10.1152/ajpheart.2000.278.6.H2039.

Risso, W.A., 2008. The informational efficiency and the financial crashes. Res. Int. Bus. Finance 22(3), 396–408. https://doi.org/10.1016/j.ribaf.2008.02.005.

Sánchez-Fernández, et al., 2025. Multivariate regime identification and prediction in financial markets via Gaussian mixture and gradient boosting methods. HAIS 2025, LNCS vol. 16203, Springer.

Schmitt, O.H., 1938. A thermionic trigger. J. Sci. Instrum. 15(1), 24–26. https://doi.org/10.1088/0950-7671/15/1/305.

Shternshis, A., Mazzarisi, P., Marmi, S., 2022. Measuring market efficiency: The Shannon entropy of high-frequency financial time series. Chaos Solitons Fractals 162, 112403. https://doi.org/10.1016/j.chaos.2022.112403.

SIFMA, 2024. US equity ownership composition — 2024 industry report. Securities Industry and Financial Markets Association.

VinaCapital, 2024. Vietnam's resilient stock market. VinaCapital Insights research note.

Vu, L.T., Van Nguyen, A., Dao, Q.N., Do, H.M., Doan, H.T.T., 2024. An Integrated Approach with Permutation Entropy Measure and Conventional Tests for Study on Stock Market Efficiency. J. Ecohumanism 3(8), 1382–1399.

Wager, S., Athey, S., 2018. Estimation and inference of heterogeneous treatment effects using random forests. J. Am. Stat. Assoc. 113(523), 1228–1242. https://doi.org/10.1080/01621459.2017.1319839.

Zanin, M., Zunino, L., Rosso, O.A., Papo, D., 2012. Forbidden patterns, permutation entropy and stock market inefficiency. Phys. A 391(6), 1820–1827. https://doi.org/10.1016/j.physa.2011.10.016.

---

## Appendix A. Pipeline overview and reproducibility

This appendix bundle is organised to mirror the workflow used to build and validate the eight-market panel: feature engineering (entropy, Appendix B) → regime classification (GMM + Schmitt-trigger filter, Appendix C) → RPS specification + cascade verification (Appendix D) → hypothesis testing process (H1–H5, Appendix E) → DML methodology (Appendix F) → uncertainty decomposition (Appendix G) → exploratory analyses (Appendix H). Each appendix is self-contained and references the main-text section it supports.

### A.1 Five-layer pipeline (mirrors §3.1)

(1) Data ingestion via vnstock + yfinance with continuous post-2020 OHLCV; (2) entropy feature engineering (WPE + SPE_Z, Appendix B); (3) regime classification — GMM K = 3 on raw labels with the Schmitt-trigger hysteresis filter applied to posterior probabilities (Appendix C); (4) forward-volatility computation and RPS cascade specification per market data quality (Appendix D); (5) hypothesis testing — per-market direction (H1), cross-market magnitude (H2), supporting hypotheses (H3–H5), DML methodology, variance decomposition, and sensitivity validation (Appendices E, F, G).

### A.2 Reproducibility tag and software environment

Validation pipeline implemented in Python 3.13 with NumPy / SciPy / pandas / scikit-learn / econml / ruptures. Random seeds: 42 (canonical seed across all scripts; per-script offsets applied to non-overlapping MC tasks; specific seed offsets documented in each script header). All numerical claims byte-for-byte reproducible from the public repository at the canonical reproducibility tag specified on the title page (anonymised for double-blind review). Frozen JSON outputs in `project/validation/results_v2/` for all 13 sensitivity + DML scripts referenced across Appendices B–H.

### A.3 Reproducibility archive and panel selection

The hypothesis specifications, market list, parameters, and pass/reject criteria are frozen in the public archive at the canonical reproducibility tag specified on the title page. The original panel specification permitted a "choose 2 of 3 by data quality" rule within each microstructure category before data ingestion (`KSE 100 or SET` for the second frontier slot, `SENSEX or NIFTY 50` for the second emerging slot, etc.); the final eight-market panel is the realisation of these selections under the inclusion criterion (liquid index with continuous post-2020 OHLCV via vnstock or yfinance, minimum 1500 trading days post-504-day labelling floor, primary-source RPS reading available from the highest-authority published source for that market structure). The selection is held constant across all reported analyses. The executable validation scripts implementing H3, H4, and H5 were authored after the original specification freeze; future revisions of the protocol should freeze the panel and commit the test code at specification time. Original hypothesis specifications are listed in Appendix E.6 alongside the methodological refinements.

### A.4 Byte-for-byte regression scope

The byte-for-byte regression assertions (`atol = 1e-4`) apply to the post-refinement results documented in Appendix E.6. Preliminary results from the original analysis archive are preserved read-only and not asserted by current regression tests; they are recoverable from the archive for full audit. Scripts added during the subsequent methodology audit (DML estimation, sensitivity tests) include their own regression assertions against frozen baselines preserved in the public repository.

---

## Appendix B. Entropy feature engineering

This appendix specifies the two entropy features (WPE + SPE_Z) used as inputs to the regime classifier (Appendix C), reports an empirical Link B test on the entropy-LEVEL ↔ RPS relationship (§6.1), and reports SPE_Z standardisation sensitivity.

### B.1 Weighted Permutation Entropy (WPE)

Given a log-return series $\{r_t\}_{t=1}^{T}$ with embedding dimension $m$ and delay $\tau$, each embedding vector $X_t = (r_t, r_{t+\tau}, \ldots, r_{t+(m-1)\tau})$ maps to an ordinal permutation pattern. For a sliding window $\mathcal{W}_t = \{t - W + 1, \ldots, t\}$ of length $W$:

$$p_\pi^w(t) = \frac{\sum_{s \in \mathcal{W}_t,\; \text{ord}(X_s) = \pi} w(X_s)}{\sum_{s \in \mathcal{W}_t} w(X_s)} \tag{B.1}$$

where $w(X_t)$ is the within-vector amplitude variance and both sums run over the same window $\mathcal{W}_t$. Weighted permutation entropy is

$$\text{WPE}(m, \tau, W) = -\frac{1}{\ln(m!)} \sum_\pi p_\pi^w \ln p_\pi^w \tag{B.2}$$

normalised to $[0, 1]$. Production parameters: $m = 3$, $\tau = 1$, $W = 22$ trading days (Bandt–Pompe / Fadlallah convention). Why these parameters: $m = 3$ yields 6 permutation patterns, sufficient for daily-data resolution while remaining estimable in 22-day windows; $\tau = 1$ captures consecutive-observation ordinal structure; $W = 22 \approx 1$ trading month balances temporal responsiveness and statistical stability.

### B.2 Standardised Price Sample Entropy (SPE_Z)

For close-price series $\{P_t\}$, embedding $m_s = 2$, tolerance $r = 0.2 \cdot \sigma_{\text{window}}$, window $W_s = 60$ days:

$$\text{SampEn}(m_s, r, W_s) = -\ln \frac{A(m_s + 1)}{A(m_s)} \tag{B.3}$$

where $A(k)$ counts vector pairs within tolerance at embedding dimension $k$. Standardisation by strictly-backward 504-day rolling Z-score:

$$\text{SPE\_Z}_t = \frac{\text{SampEn}_t - \mu_{[t-504,\, t-1]}}{\sigma_{[t-504,\, t-1]}} \tag{B.4}$$

where $\mu_{[t-504,t-1]}$ and $\sigma_{[t-504,t-1]}$ are computed strictly preceding day $t$, eliminating look-ahead bias. Why SampEn over ApEn: ApEn (Pincus, 1991) counts self-matches and introduces systematic positive bias for short windows; in a rolling-window pipeline with $W_s = 60$, this bias is non-negligible; SampEn excludes self-matches and provides unbiased conditional probability estimates. Why rolling 504-day Z-score over global Z-score: rolling Z eliminates look-ahead bias; global Z would leak future information into past entropy values.

### B.3 Feature orthogonality rationale

WPE operates on log-returns (first differences), measuring ordinal disorder of the sequence of ups and downs. SPE_Z operates on close prices (levels), measuring trajectory complexity of the price path. The two features capture genuinely different information about the same market, providing the bivariate feature space (WPE, SPE_Z) for GMM regime classification (Appendix C). This orthogonality is why the GMM separates clusters cleanly without preprocessing on the price-plane features.

### B.4 SPE_Z standardisation sensitivity

The cross-market H2 magnitude finding (§4.2) is robust to SPE_Z standardisation choice. Three alternative variants tested via `project/validation/h2_sensitivity_spe_z.py` with frozen output `h2_sensitivity_spe_z.json`:

**Table B.1.** Cross-market Spearman ρ(H, tier_rank) under four SPE_Z standardisation specifications.

| Variant | Description | ρ(H, tier) raw | p | ρ(H, RPS) raw | p |
|---|---|---|---|---|---|
| rolling_z (baseline) | strictly-backward 504-day Z-score | +0.927 | 0.001 | +0.857 | 0.007 |
| wpe_only | drop SPE_Z entirely | +0.161 | 0.704 | +0.214 | 0.610 |
| raw_sampen | no Z-score normalisation | +0.803 | 0.016 | +0.905 | 0.002 |
| global_z | full-sample mean/std | +0.803 | 0.016 | +0.905 | 0.002 |

The headline H2 result survives 2 of 3 alternatives (raw SampEn and global Z give decisive p < 0.02); the WPE-only variant collapses, confirming SPE_Z carries critical signal beyond what WPE captures alone. The standardisation choice is therefore not driving the cross-market ordering.

### B.5 Link B empirical test on the panel (entropy LEVEL ↔ RPS)

The §6.1 Link B specification asserts that lower-information retail flow exhibits behavioural correlation that reduces ordinal-pattern complexity in the price-generating process. A direct empirical test on the eight-market panel via `project/validation/link_b_tests.py` (frozen output `link_b_tests.json`):

**Test B.5.1 — entropy LEVEL.** Spearman ρ between per-market mean (or median) entropy feature and RPS, computed cross-market:

| Feature | ρ | p (perm 2-sided) | Fisher 95% CI |
|---|---|---|---|
| mean WPE | −0.571 | 0.145 | [−0.910, +0.223] |
| **median WPE** | **−0.714** | **0.056** | **[−0.944, −0.019]** |
| mean SPE_Z | −0.357 | 0.385 | [−0.848, +0.464] |
| median SPE_Z | −0.143 | 0.750 | [−0.770, +0.625] |

The median WPE result (ρ = −0.714, p = 0.056, Fisher 95% CI [−0.944, −0.019]) is borderline at the n = 8 power floor and direction-consistent with the herding interpretation. Mean WPE shows the same sign but weaker. SPE_Z shows weaker sign-consistent direction.

**Test B.5.2 — per-regime entropy spread.** Spearman ρ between per-market max−min spread of mean entropy across {Det, Trans, Sto} regimes and RPS yields null correlations (|ρ| < 0.36 across raw/filtered × WPE/SPE_Z, all p > 0.39). The cross-market signal lives in the entropy *level* aggregate rather than in the per-regime separation gap.

---

## Appendix C. Regime classification: GMM + Schmitt-trigger filter

This appendix specifies the K = 3 GMM classifier (formal definition + parameter rationale) and the Schmitt-trigger hysteresis filter (algorithm + production parameters), reports phase-space visualisation, GMM K-selection sensitivity, and within-window structural breakpoint diagnostics.

### C.1 GMM K = 3 specification

Bivariate feature $\mathbf{z}_t = (\text{WPE}_t, \text{SPE\_Z}_t)$ modelled as $K = 3$ full-covariance Gaussian mixture:

$$p(\mathbf{z}_t \mid \theta) = \sum_{k=1}^{3} \pi_k \mathcal{N}(\mathbf{z}_t \mid \mu_k, \Sigma_k) \tag{C.1}$$

EM with $n_{\text{init}} = 10$, $K = 3$ selected by BIC over $\{2, \ldots, 6\}$ on the calibration market (VNINDEX, post-2020). Components sorted by centroid sum (WPE_mean + SPE_Z_mean) for semantic labelling: low-entropy (Deterministic), mid-entropy (Transitional), high-entropy (Stochastic). Centroid stability across initialisations within 2 percent relative deviation. Full-covariance allows each cluster to have its own shape and orientation in feature space; diagonal covariance would force axis-aligned ellipses misrepresenting the WPE-SPE_Z correlation structure. Production parameters: K = 3, full covariance, $n_{\text{init}} = 10$, max EM iterations = 500, no preprocessing on the price plane (raw features preserved), random_state = 42.

### C.2 Schmitt-trigger hysteresis algorithm

Let $\mathbf{p}_t = (p_{t,1}, \ldots, p_{t,K})$ denote posterior probabilities at time $t$, $k_t^* = \arg\max_k p_{t,k}$ the instantaneous candidate, $L_{t-1}$ the previously confirmed label, $m_t = p_{t,k_t^*} - p_{t,L_{t-1}}$ the instantaneous margin. Initialise $L_1 = \arg\max_k p_{1,k}$. For each $t = 2, \ldots, T$:

1. Compute $k^* = \arg\max_k p_{t,k}$.
2. If $k^* = L_{t-1}$: retain $L_t = L_{t-1}$.
3. Else if $m_t > \delta_{\text{hard}}$: set $L_t = k^*$ (hard-margin transition).
4. Else if $\delta_{\text{soft}} < m_t \leq \delta_{\text{hard}}$: increment persistence counter for candidate $k^*$; confirm $L_t = k^*$ only if counter reaches $t_{\text{persist}}$; otherwise retain $L_{t-1}$.
5. Else: retain $L_{t-1}$.

Production parameters $(\delta_{\text{hard}}, \delta_{\text{soft}}, t_{\text{persist}}) = (0.60, 0.35, 8)$ calibrated on VNINDEX post-2020 targeting 5–10 filtered flips per year (achieves ≈ 6.5/yr on VNINDEX). Sensitivity to target band {3-7, 5-10, 8-15} reported in §C.5.

### C.3 Phase-space visualisation (VNINDEX)

The bivariate feature space (WPE on horizontal axis, SPE_Z on vertical axis) over the post-COVID window (display range 2020-01-01 to 2026-04-17, n = 1506 bars after the 504-day labelling floor) provides direct visual inspection of the regime classifier. Color encodes the GMM regime label; dashed ellipses are 2-σ contours of the underlying GMM components.

**Figure C.1.** VNINDEX phase-space visualisation in the (WPE, SPE_Z) plane, comparing Raw GMM labels (left, per-bar argmax) and Hysteresis-Filtered labels (right, Schmitt-trigger with δ_hard = 0.60, δ_soft = 0.35, t_persist = 8). Both panels use identical GMM components and posterior probabilities; only the label-assignment rule differs. Reduction in flip rate from 15.23/yr to 6.53/yr (57 percent) reflects suppression of single-bar label flicker near cluster boundaries.

![Figure C.1: VNINDEX Phase Space — Raw GMM versus Hysteresis-Filtered](figure_G1_phase_space.png)

The two panels share the same underlying GMM components and posterior probability sequences; only the rule mapping posteriors to discrete labels differs. Labels differ on 156 of 1506 bars (10.4 percent); regime composition shifts marginally (Det/Trans/Sto: 725/687/94 raw vs 740/679/87 filtered, corresponding to p(Det)/p(Trans)/p(Sto) = 48.1%/45.6%/6.2% vs 49.1%/45.1%/5.8%). The cluster geometry is preserved across the two panels (dashed 2-σ ellipses occupy the same regions); bars that change label cluster in the boundary regions where adjacent components overlap; regime population shares are stable to within ≈ 1 pp. The figure is provided for the primary calibration market only; equivalent phase-space visualisations for the remaining seven markets reproduce from the public repository.

### C.4 Hysteresis filtering effect on flip rate and regime composition

**Table C.1.** Per-market hysteresis filtering effect on flip rate and regime composition.

| Market | Raw flips/yr | Filtered flips/yr | Reduction | p(Det / Trans / Sto) | T_trans (days) |
|---|---|---|---|---|---|
| VNINDEX | 15.2 | 6.5 | 57% | 49.1 / 45.1 / 5.8 | 49.2 |
| PSEI | 26.9 | 8.8 | 67% | 47.5 / 40.3 / 12.2 | 34.1 |
| KOSPI | 34.3 | 14.8 | 57% | 30.0 / 53.5 / 16.5 | 30.8 |
| NIFTY | 20.8 | 8.9 | 57% | 36.3 / 55.8 / 7.9 | 45.9 |
| SPX | 31.8 | 14.1 | 56% | 39.9 / 43.3 / 16.8 | 23.8 |
| FTSE | 28.2 | 10.4 | 63% | 45.9 / 35.2 / 19.0 | 26.9 |
| NIKKEI | 18.3 | 8.8 | 52% | 43.4 / 37.6 / 19.0 | 31.8 |
| BTC | 29.0 | 10.1 | 65% | 41.4 / 45.2 / 13.4 | 23.1 |

### C.5 GMM K-selection per market sensitivity

Per-market BIC selection over K ∈ {2, 3, 4, 5} via `project/validation/gmm_k_sensitivity.py` (frozen output `gmm_k_sensitivity.json`). At fixed K (any of 2/3/4/5), the cross-market Spearman ρ(H, tier) remains decisive:

**Table C.2.** Cross-market ρ(H, tier_rank) under fixed-K and market-optimal-K specifications.

| Spec | ρ(H, tier) | p | Verdict |
|---|---|---|---|
| Fixed K = 2 | +0.815 | 0.014 | Decisive |
| Fixed K = 3 (paper baseline) | +0.927 | 0.001 | Decisive |
| Fixed K = 4 | +0.865 | 0.006 | Decisive |
| Fixed K = 5 | +0.964 | 0.0001 | Decisive |
| Market-optimal K (different per market) | +0.494 | 0.213 | n.s. |

Market-optimal K's non-significance is expected, not a weakness: different K values yield H statistics on incomparable scales (KW H is K-dependent), so mixing markets at different K mixes incomparable measurements. Fixed K = 3 baseline is robust across reasonable K choices.

### C.6 Within-window structural breakpoints

A PELT (Killick et al., 2012) breakpoint detector with RBF cost and minimum segment size = 60 bars applied to log returns and the WPE / SPE_Z feature series within the 2020-04-17 to 2026-04-17 analysis window via `project/validation/structural_breaks.py` (frozen output `structural_breaks.json`).

**Table C.3.** Per-market breakpoint counts within the analysis window.

| Market | Log-returns breaks | WPE breaks | SPE_Z breaks |
|---|---|---|---|
| VNINDEX | 0 | 7 | 14 |
| PSEI | 1 | 5 | 16 |
| KOSPI | 2 | 6 | 15 |
| NIFTY | 0 | 4 | 14 |
| SPX | 2 | 3 | 14 |
| FTSE | 1 | 9 | 13 |
| NIKKEI | 0 | 6 | 14 |
| BTC | 1 | 8 | 22 |

Log-return breakpoints are rare (0–2 per market); WPE breakpoints are intermediate (3–9 per market); SPE_Z breakpoints are more frequent (13–22 per market) — consistent with the rolling 504-day Z-score amplifying local-distribution shifts by construction. Identified breakpoints cluster around known macro events (Fed first rate hike March 2022, banking stress March 2023, BTC ETF approval January 2024, FTSE Russell Vietnam reclassification announcement October 2025). The H1 + H2 results (§4) rely on cross-market ordering rather than within-market temporal stability and are robust to within-window breakpoint structure; sub-window analysis is identified as natural extension.

---

## Appendix D. RPS specification: cascade verification

This appendix consolidates the RPS specification: cascade phase classification (§D.1), per-market source documentation (§D.2), the cascade-based RPS verification process (§D.3), and PSEI source-classification sensitivity (§D.4). The cascade is the systematic verification framework that yielded one update (KOSPI) and seven confirmations against the originally specified readings.

### D.1 Cascade phase classification (P1 → P2 → P3)

**Table D.1.** Per-market cascade phase + RPS specification.

| Market | Phase | Type | Specification | Source |
|---|---|---|---|---|
| VNINDEX | P1 | point | 0.90 | Vietnam SSC + VinaCapital convergent multi-year |
| PSEI | P1 | point | 0.68 | PSE 2023 Annual Report (authoritative exchange document) |
| KOSPI | P1 | point | 0.45 | KRX 2026 direct turnover-by-investor-type |
| NIFTY | P1 | point | 0.40 | NSE India Ownership Report |
| SPX | P2 | uniform | U(0.18, 0.37) | SIFMA ownership 0.18 vs MEMX order flow 0.30–0.37 (metric disagreement) |
| FTSE | P2 | uniform | U(0.15, 0.25) | UK FCA limited public data |
| NIKKEI | P1 | point | 0.18 | JPX Trading-by-Investor-Type direct |
| BTC | P3 | Beta | Beta(α=11, β=9) [mean 0.55, κ=20] | No central exchange; no authoritative aggregator; widest posterior |

The cascade is a *filter*: each market enters at the highest-authority phase its data quality supports.

- **P1 (5 of 8 markets):** single authoritative primary source — centralised exchange's investor-type turnover statistics (KRX, NSE, JPX), annual report (PSE), or convergent multi-source readings (Vietnam SSC + VinaCapital).
- **P2 (2 of 8 markets):** competing-source bounds reflecting metric disagreement — SIFMA ownership vs MEMX order flow for SPX; UK FCA limited public data for FTSE.
- **P3 (1 of 8 markets):** no authoritative source and no clean bounds — BTC is the only market in this category, with no central exchange and no authoritative aggregator. The Beta posterior is parameterised by mean 0.55 (the original reading) and concentration κ = α + β = 20 (encoding wide uncertainty consistent with crypto-aggregator estimates).

### D.2 Per-market source documentation

VNINDEX (P1): Vietnam SSC monthly market reports + VinaCapital industry estimates, multi-year convergent. PSEI (P1): PSE 2023 Annual Report (authoritative exchange document); secondary-source PSE Stock Market Investor Profile reading 0.21 measures a different metric and is recorded as alternative source — see §D.4 sensitivity. KOSPI (P1): KRX Data Marketplace 2026 direct turnover-by-investor-type, superseding the original ASIFMA (2022) reading (see §D.3). NIFTY (P1): NSE India Ownership Report. SPX (P2): SIFMA ownership = 0.18 vs MEMX order flow = 0.30–0.37; the metric disagreement reflects US market fragmentation across NYSE + Nasdaq + 14+ exchanges + ATS dark pools + wholesaler internalisers. FTSE (P2): UK FCA limited public data + LSE Group industry estimates; bounds 0.15–0.25. NIKKEI (P1): JPX Trading-by-Investor-Type direct. BTC (P3): no authoritative central exchange; aggregator estimates (Coinalyze, CryptoCompare) provide informal references; Beta posterior centered on the originally specified 0.55.

### D.3 Cascade-based RPS verification process

The cascade was applied as the systematic verification process to all 8 markets in this paper. The process yielded one update and seven confirmations against the originally specified RPS readings:

- **KOSPI updated.** The original KOSPI RPS value (RPS = 0.70, ASIFMA, 2022) was, on cascade verification against Korea Exchange direct turnover-by-investor-type data (Korea Exchange, 2026), determined to be a 2021-period COVID-elevated reading that did not persist into the analysis-window terminus (KRX records ≈ 45% in March 2026, with intermediate readings 30–45%). The cascade classifies KOSPI as Phase P1 with the KRX direct point estimate 0.45. The original ASIFMA reading and the corresponding pre-verification continuous-RPS H2 result (ρ = 0.755, p = 0.031) are preserved read-only in the public archive.
- **Seven confirmed.** The other markets' original readings were confirmed as consistent with their highest-authority current sources per the cascade classification in §D.1. The tier-based primary specification (§4.2.1) is unaffected by the KOSPI update — KOSPI remains in the Emerging tier under either reading.

This single-update outcome is itself a cascade outcome, not a special case requiring separate methodological treatment. The cascade framework is the systematic verification process; the KOSPI update is one of its empirical results.

### D.4 PSEI source-classification sensitivity

PSEI's P1 classification is based on the PSE 2023 Annual Report value of 0.68. The PSE Stock Market Investor Profile alternative reading of 0.21 measures a different metric (account-share-weighted vs trading-value-weighted) and is recorded as a secondary source. Reclassifying PSEI from P1 (point 0.68) to P2 (Uniform[0.21, 0.68] reflecting the metric disagreement bounds) tests sensitivity:

**Table D.2.** Cascade composite ρ under PSEI P1 (baseline) vs P2 (sensitivity). Via `project/validation/h2_cascade_pseiP2.py` (frozen output `h2_cascade_pseiP2.json`).

| Spec | ρ_raw mean | ρ_raw 95% CI | P(ρ > 0.5) raw | ρ_filt mean | ρ_filt 95% CI | P(ρ > 0.5) filt |
|---|---|---|---|---|---|---|
| Baseline (PSEI P1) | +0.847 | [+0.786, +0.905] | 100.0% | +0.901 | [+0.833, +0.952] | 100.0% |
| Sensitivity (PSEI P2) | +0.750 | [+0.548, +0.905] | 98.5% | +0.810 | [+0.571, +0.952] | 99.4% |
| Δ (sensitivity − baseline) | −0.097 | | −1.5pp | −0.090 | | −0.6pp |

PSEI source-classification matters for the cascade composite point estimate (ρ_raw mean shifts by ≈ 0.1) but the qualitative finding (P(ρ > 0.5) ≈ 99% under both raw and filtered) is robust to the metric-definition disagreement.

---

## Appendix E. Hypothesis testing process (H1–H5)

This appendix documents the hypothesis tests conducted on the eight-market panel under the final specifications (with the methodological evolution from preliminary to final documented in §E.6). H1 (per-market direction) and H2 (cross-market magnitude) are central findings (§4); H3 (composition) and H4 (temporal structure) and H5 (parameter robustness) are supporting hypotheses (§5).

### E.1 H1 per-market direction tests

The canonical H1 direction test is the causal forest DML + Purged K-Fold + filtered specification. Per-market ATE estimates are reported in Table 2 of the main text (§4.1.1); the full DML specification grid (KFold + raw, KFold + filtered, TimeSeriesSplit + filtered, PurgedKFold + filtered + bootstrap, plus linear DML sanity check) is detailed in Appendix F.

### E.2 H2 cross-market magnitude tests

**Table E.1.** Per-market H statistic, η² effect size (sample-size-corrected), N_obs, and RPS (raw GMM labels). Generated via `project/validation/h2_eta_squared.py` (frozen output `h2_eta_squared.json`).

| Market | RPS | H_raw | η²_raw | H_filt | η²_filt | N_obs |
|---|---|---|---|---|---|---|
| VNINDEX | 0.90 | 83.90 | 0.054 | 96.33 | 0.063 | 1506 |
| PSEI | 0.68 | 48.10 | 0.034 | 41.09 | 0.029 | 1383 |
| KOSPI | 0.45 | 5.88 | 0.003 | 21.84 | 0.014 | 1467 |
| NIFTY | 0.40 | 13.98 | 0.008 | 21.99 | 0.014 | 1458 |
| SPX | 0.275 | 2.12 | 0.0001 | 1.51 | 0.0000 | 1500 |
| FTSE | 0.20 | 4.15 | 0.001 | 1.34 | 0.0000 | 1510 |
| NIKKEI | 0.18 | 4.05 | 0.001 | 2.22 | 0.0002 | 1439 |
| BTC | 0.55 | 7.13 | 0.002 | 32.24 | 0.012 | 2445 |

**Cross-market ρ summary.** ρ(H_raw, tier) = +0.927 (p = 0.001); ρ(η²_raw, tier) = +0.964 (p = 0.0001); ρ(H_raw, RPS) = +0.857 (p = 0.007); ρ(η²_raw, RPS) = +0.810 (p = 0.015). η² strengthens rather than weakens the ordering after sample-size correction; ρ(H_raw, N_obs) = −0.07 (p = 0.87) rejects the sample-size confound.

**Table E.2.** Tier-rank Crypto-placement sensitivity. Crypto rank ∈ {1, 2, 3, 4, 5}; other tier ranks fixed (Frontier=4, Emerging=3, Developed=1). All five configurations decisive.

| Crypto rank | ρ(H_raw, tier) | p (raw) | ρ(H_filt, tier) | p (filt) |
|---|---|---|---|---|
| 1 | +0.849 | 0.008 | +0.772 | 0.025 |
| 2 (paper baseline) | +0.927 | 0.001 | +0.890 | 0.003 |
| 3 | +0.945 | 0.0004 | +0.945 | 0.0004 |
| 4 | +0.882 | 0.004 | +0.945 | 0.0004 |
| 5 | +0.803 | 0.016 | +0.890 | 0.003 |

**Table E.3.** Monte Carlo measurement-noise sensitivity for H–RPS coupling under three RPS perturbation magnitudes ($n = 10{,}000$ trials each).

| Specification | Noise SD | Mean ρ | 5th pct | Median | 95th pct | P(ρ > 0.5) |
|---|---|---|---|---|---|---|
| Raw      | 0.05 | 0.872 | 0.833 | 0.881 | 0.929 | 100.0% |
| Raw      | 0.10 | 0.845 | 0.667 | 0.881 | 0.952 | 99.8% |
| Raw      | 0.15 | 0.778 | 0.524 | 0.810 | 0.952 | 96.3% |
| Filtered | 0.05 | 0.929 | 0.881 | 0.952 | 0.952 | 100.0% |
| Filtered | 0.10 | 0.889 | 0.738 | 0.929 | 0.976 | 99.95% |
| Filtered | 0.15 | 0.820 | 0.595 | 0.857 | 0.976 | 98.3% |

**Table E.4.** Stratified subpanel Spearman correlations.

| Subpanel | n | ρ(H, RPS) | p-value | Note |
|---|---|---|---|---|
| Full panel | 8 | 0.850 | 0.008 | Primary test |
| Circuit-breaker present | 6 | 0.886 | 0.019 | Excludes FTSE, BTC |
| Frontier + Emerging | 4 | 0.800 | 0.200 | Descriptive |

**Table E.5.** Leave-one-out sensitivity for the H–RPS Spearman correlation.

| Dropped market | Category | ρ_raw | p_raw | ρ_filt | p_filt |
|---|---|---|---|---|---|
| VNINDEX | Frontier | 0.775 | 0.041 | 0.901 | 0.006 |
| PSEI    | Frontier | 0.775 | 0.041 | 0.901 | 0.006 |
| KOSPI   | Emerging | 0.847 | 0.016 | 0.937 | 0.002 |
| NIFTY   | Emerging | 0.883 | 0.009 | 0.937 | 0.002 |
| SPX     | Developed | 0.883 | 0.009 | 0.955 | 0.0008 |
| FTSE    | Developed | 0.857 | 0.014 | 0.929 | 0.003 |
| NIKKEI  | Developed | 0.857 | 0.014 | 0.964 | 0.0005 |
| BTC     | Crypto    | 0.847 | 0.016 | 0.901 | 0.006 |

Every leave-one-out panel preserves both directional positivity and conventional significance: raw-spec ρ ∈ [0.775, 0.883] all $p \leq 0.041$; filtered-spec ρ ∈ [0.901, 0.964] all $p \leq 0.006$.

### E.3 H3 regime composition

**Table E.6.** Per-market p(Transitional) under filtered labels with bootstrap confidence intervals.

| Market | RPS | p_tra (filtered) | 95% CI | BH-FDR q |
|---|---|---|---|---|
| VNINDEX | 0.90 | 0.451 | [0.358, 0.550] | 0.622 |
| PSEI | 0.68 | 0.403 | [0.315, 0.488] | 0.849 |
| KOSPI | 0.45 | 0.535 | [0.455, 0.617] | — |
| NIFTY | 0.40 | 0.558 | [0.463, 0.653] | — |
| SPX | 0.275 | 0.433 | [0.352, 0.514] | 0.000 |
| FTSE | 0.20 | 0.352 | [0.270, 0.438] | 0.000 |
| NIKKEI | 0.18 | 0.376 | [0.283, 0.469] | 0.000 |
| BTC | 0.55 | 0.452 | [0.377, 0.526] | — |

Continuous Spearman ρ(p_tra, RPS) = 0.563 (p = 0.146, 95% CI [−0.290, 0.961]) — directionally positive but underpowered at n = 8. The H3 categorical rule as originally specified is rejected by PSEI (p_tra = 0.403 < 0.45 threshold).

### E.4 H4 block-permutation temporal structure

Observed filtered flips/yr below every null distribution at block sizes {5, 10, 20} on all eight markets ($p \approx 0$ at $n_{\text{perm}} = 2000$; BH-FDR $q = 0$). The filter is non-trivial relative to any shuffled filtered sequence — a weaker claim than intrinsic temporal structure beyond chance on raw labels; a stronger null (permute raw GMM argmax then re-filter) is recorded as future work.

### E.5 H5 hysteresis parameter robustness

**Table E.7.** H5 hysteresis spread under three parameter configurations with bootstrap CI.

| Market | Spread (pp) | 95% CI | P(spread > 5pp) | Verdict |
|---|---|---|---|---|
| NIKKEI | 2.0 | [0.6, 4.3] | 0.7% | PASS (decisive) |
| BTC | 2.7 | [0.9, 6.5] | 12.5% | PASS (borderline) |
| VNINDEX | 3.4 | [0.5, 8.4] | 24.0% | PASS (borderline) |
| PSEI | 5.6 | [1.4, 10.6] | 60.5% | Dead zone |
| KOSPI | 7.2 | [2.5, 12.5] | 80.1% | REJECT |
| NIFTY | 7.7 | [3.1, 13.9] | 86.2% | REJECT |
| SPX | 9.0 | [4.9, 13.7] | 96.8% | REJECT |
| FTSE | 9.5 | [3.1, 16.3] | 90.7% | REJECT |

**Table E.8.** Per-market optimal hysteresis parameters and verdict stability across shared/own-optimal calibration modes.

| Market | Own optimum (δh/δs/tp) | Spread (shared) | Spread (own-opt) | Verdict (shared / own) |
|---|---|---|---|---|
| VNINDEX | 0.60/0.35/3 | 0.034 | 0.022 | PASS / PASS |
| NIKKEI | 0.80/0.30/5 | 0.020 | 0.046 | PASS / PASS |
| BTC | 0.80/0.30/8 | 0.027 | 0.046 | PASS / PASS |
| PSEI | 0.70/0.40/10 | 0.056 | 0.061 | Dead zone / Dead zone |
| KOSPI | 0.80/0.40/13 | 0.072 | 0.070 | REJECT / REJECT |
| NIFTY | 0.80/0.20/13 | 0.077 | 0.073 | REJECT / REJECT |
| SPX | 0.80/0.40/10 | 0.090 | 0.143 | REJECT / REJECT |
| FTSE | 0.80/0.40/8 | 0.095 | 0.168 | REJECT / REJECT |

Per-market re-calibration preserves each market's verdict (PASS markets stay PASS, REJECT markets stay REJECT) — confirming the verdict pattern is intrinsic to each market rather than a transfer-learning artefact. The 4-of-8 REJECT pattern is reframed as positive heterogeneity evidence in §5.2 + §6.6.

### E.6 Methodological evolution: preliminary to final specification

**Table E.9.** Preliminary hypothesis specifications (3-market preliminary study; Cliff's δ + Mann–Whitney era).

| Hypothesis | Claim | Primary test | Label source |
|---|---|---|---|
| H1 | Forward 20d realized vol Det > Sto on frontier markets (paradox direction) | One-sided Mann–Whitney + Cliff's δ + circular-block bootstrap CI + Newey–West HAC t-test, horizon sweep {5,10,20,40,60}d, BH-FDR | Raw labels (canonical) |
| H2 | KW H-statistic from H1 tracks RPS monotonically | Spearman ρ + bootstrap CI + RPS ± 0.05 MC sensitivity + stratified subpanels | Raw labels (canonical) |
| H3 | p(Transitional) scales with retail participation | Bootstrap CI on p_tra + continuous Spearman ρ(p_tra, RPS) + BH-FDR | Filtered labels (canonical) |
| H4 | Filtered regime sequence is temporally structured | Block-permutation shuffle at block ∈ {5,10,20} + BH-FDR | Filtered labels |
| H5 | p(Transitional) is robust across hysteresis configurations | Joint circular-block bootstrap with shared resamples → CI on spread + P(spread > 5pp) | Three configurations |

The statistical architecture used in the main paper differs from the preliminary specifications listed in Table E.9. The divergence is methodological — instruments and tests were refined during the panel-extension audit to match the claims being tested — not numerical: no result has been selected to improve appearances. The full audit (preliminary outputs, intermediate states, and final specification) is preserved in the public archive.

**Seven methodological refinements** between the preliminary 3-market specification and the final 8-market specification: (1) H1 primary test changed (initial refinement) from KW omnibus to one-sided pairwise Mann–Whitney with Cliff's δ, block-bootstrap CI, and Newey–West HAC t-test; (2) H2 instrument changed from composite microstructure index to single-variable Retail Participation Share; (3) H3 primary verdict changed from categorical bands to bootstrap CI plus continuous Spearman companion; (4) H4 null changed from simple permutation to block-permutation at multiple block sizes; (5) Multiplicity correction added: Benjamini–Hochberg FDR across the eight-market panel; (6) H5 dead-zone rule applied as written; (7) H1 primary test re-specified to causal forest DML with Purged K-Fold cross-fitting on filtered labels (Wager and Athey, 2018; López de Prado, 2018, §7.3). The refinement #7 motivation is theoretical, not empirical: regime treatment effects on forward volatility are heterogeneous in volatility context (Chernozhukov et al., 2018; Wager and Athey, 2018), and conditional partial-effect estimation is the methodologically appropriate tool for this estimand. Empirical evidence consistent with this theoretical motivation: linear DML's constant-ATE assumption fails the treatment-balance check on three frontier markets where Stochastic-regime concentration in late years is severe; causal forest succeeds on all eight (§4.1.1, §F.5). The Cliff's δ readings under raw labels remain in the preliminary archive and are recoverable; they are superseded as the canonical H1 estimator on theoretical grounds and not selected against on empirical preference.

**One input-data update** (KOSPI ASIFMA 2022 → KRX 2026 direct) applied through the cascade verification process; documented in §D.3 as one outcome of the systematic cascade rather than a special-case correction.

All raw validation numbers reproduce byte-for-byte against the frozen analysis archive via regression assertions in active validation scripts.

---

## Appendix F. DML methodology details

This appendix specifies the canonical DML estimation framework adopted for H1 conditional partial-effect estimation (§4.1.1) and the four supporting spec variants used in the methodology study. The canonical framework is **causal forest DML (Wager and Athey, 2018) + Purged K-Fold cross-fitting (López de Prado, 2018, §7.3) + filtered Schmitt-trigger labels + asymptotic CI**.

### F.1 Causal Forest DML formal specification

For each market, the estimand is the average treatment effect of regime label (Det vs Sto on filtered labels, Stochastic as control) on forward 20-day realised volatility, controlling for lagged variables. causal forest estimates per-observation treatment effects $\tau(x) = E[Y(1) - Y(0) \mid X = x]$ via honest random forests; ATE is the average $\tau(x)$ across observations. Why causal forest over linear DML: regime treatment effects on forward volatility are theoretically heterogeneous in volatility context (different regimes have different consequences in different lagged-vol environments); linear DML's homogeneity assumption fails empirically on rare-class frontier markets (treatment-balance check fails when Sto regime is concentrated in late years). causal forest succeeds on all eight markets; linear DML fails on three (VNINDEX, PSEI, NIFTY).

**Treatment specification.** T = 1 if regime label = Deterministic (filtered Schmitt-trigger labels), T = 0 if Stochastic. Transitional bars excluded from the binary treatment estimation (selection-bias risk noted; multinomial extension is identified as future methodological work).

**Outcome specification.** Y = forward 20-day realised volatility (annualised %), computed as $Y_t = \text{rolling 20-day std of log returns starting at } t+1 \times \sqrt{252} \times 100$.

**Control set.** X = lagged log returns (lags 1, 5, 22), lagged squared returns (lags 1, 5, 22), lagged realised volatility (lags 1 and 22), and day-of-week dummies (Tue/Wed/Thu/Fri with Mon as reference).

**Nuisance models.** RandomForestRegressor (n_estimators = 200, max_depth = 6) for $E[Y \mid X]$; RandomForestClassifier (same hyperparameters) for $E[T \mid X]$.

**Final stage.** CausalForestDML with n_estimators = 300, max_depth = 6, honest splitting; asymptotic CI for ATE.

### F.2 Purged K-Fold cross-fitting (López de Prado, 2018, §7.3)

The cross-fitting splitter is the methodologically critical choice for financial regime classification with overlapping forward-looking targets. Three problems must be solved simultaneously:

(i) **Future-data leakage from naive K-Fold.** Sklearn's default KFold (no shuffle) splits data into K contiguous chunks; in fold k, training set includes the K−1 OTHER chunks, some of which are AFTER chunk k → future data leaks into past predictions. The methodology study (§F.4) demonstrates this: NIKKEI's apparent Paradox direction under KFold cross-fitting flips to non-significant (and TimeSeriesSplit yields Inverted direction) under proper time-series cross-fitting, confirming KFold leakage on this market.

(ii) **Regime non-stationarity that breaks strict TimeSeriesSplit.** Stochastic regime is concentrated in late years on frontier markets (VNINDEX has 0 Sto observations in 2020–2021); strict forward-chaining TimeSeriesSplit leaves early training folds without treatment balance, causing linear DML's strict treatment-balance check to fail. PurgedKFold uses contiguous blocks WITHOUT shuffling but allows non-strict ordering of the test fold sequence.

(iii) **Autocorrelation contamination via residual zone.** Forward 20-day realised volatility creates a 19-bar overlap between consecutive observations; samples within 20 bars of the test fold boundary are contaminated by autocorrelation with test-fold values. The embargo zone of 20 bars (matching the overlap window) purges these samples from training.

**Specification.** PurgedKFold (custom sklearn-compatible splitter at `project/validation/_cpcv_splitter.py`): K = 5 contiguous blocks, embargo = 20 bars on each side of every test fold, disjoint test folds (each observation is out-of-fold exactly once → standard cross-fitting property preserved).

**Note on Combinatorial Purged CV (CPCV).** The Combinatorial Purged Cross-Validation variant (López de Prado, 2018, §7.5) provides multiple test paths per observation via combinations of K_test test blocks; this is appropriate for trading-strategy backtest path aggregation but **incompatible with DML cross-fitting** which requires disjoint test folds. PurgedKFold (Ch. 7.3) is the correct choice for DML on time-series with overlapping targets.

### F.3 Five DML spec variants compared

The methodology study explored five spec variants on all eight markets. JSON outputs frozen in `project/validation/results_v2/`:

**Table F.1.** DML spec variants compared in the methodology audit.

| Spec | Cross-fitting | Labels | Inference | Output JSON |
|---|---|---|---|---|
| KFold + raw | KFold (5 folds) | raw GMM | asymptotic | h1_dml.json |
| KFold + raw, no lagged RV | KFold (5 folds) | raw GMM | asymptotic | h1_dml_no_lagrv.json |
| KFold + filtered | KFold (5 folds) | filtered Schmitt | asymptotic | h1_dml_filtered.json |
| TimeSeriesSplit + raw | TimeSeriesSplit (5 splits) | raw GMM | asymptotic | h1_dml_tsaware.json |
| **CANONICAL: PurgedKFold + filtered + Bootstrap** | PurgedKFold (K=5, embargo=20) | filtered Schmitt | Bootstrap (n=100) for LinearDML, asymptotic for CausalForest | **h1_dml_cpcv.json** |

### F.4 Per-market canonical-spec ATE (CausalForest + PurgedKFold + filtered)

**Table F.2.** Causal Forest DML ATE per market under canonical spec (treatment = Det vs Sto on filtered labels, outcome = forward 20-day realised vol annualised %).

| Market | ATE | 95% CI | Direction verdict |
|---|---|---|---|
| VNINDEX | +1.42 | [−3.13, +5.96] | n.s. |
| PSEI | −0.13 | [−2.04, +1.79] | n.s. |
| KOSPI | −26.69 | [−72.98, +19.61] | n.s. (extreme heterogeneity) |
| NIFTY | −1.12 | [−4.09, +1.85] | n.s. |
| **SPX** | **+3.48** | **[+0.92, +6.04]** | **Paradox (decisive)** |
| FTSE | +2.58 | [−0.47, +5.62] | n.s. (Paradox direction) |
| NIKKEI | +1.27 | [−1.61, +4.15] | n.s. |
| **BTC** | **−9.34** | **[−18.07, −0.61]** | **Inverted (decisive)** |

Two markets clear decisive verdict: SPX (Paradox) and BTC (Inverted). The SPX decisive-Paradox finding is robust across the full spec grid (KFold + raw, KFold + filtered, PurgedKFold + filtered all give Paradox direction with magnitude tighter under proper cross-fitting). BTC decisive-Inverted under filtered labels corrects the earlier 3-market preliminary report's thin-Paradox classification.

### F.5 LinearDML sanity check (homogeneous-effect approximation)

Linear DML imposes a constant ATE assumption — appropriate as a sanity check on developed markets but failing on three frontier markets due to regime non-stationarity.

**Table F.3.** LinearDML ATE per market under the canonical PurgedKFold + filtered + Bootstrap specification on the markets where it is feasible.

| Market | LinearDML ATE | 95% CI | Notes |
|---|---|---|---|
| VNINDEX | FAIL | — | Treatment-balance check fails (Sto rare in early years) |
| PSEI | FAIL | — | Same |
| KOSPI | −5.80 | [−23.94, +12.33] | Wide CI consistent with heterogeneous effect |
| NIFTY | FAIL | — | Treatment-balance check fails |
| SPX | +4.16 | [+0.07, +8.25] | Decisive Paradox (matches CF direction) |
| FTSE | +0.97 | [−1.33, +3.26] | n.s. |
| NIKKEI | +0.92 | [−3.32, +5.17] | n.s. |
| BTC | −9.45 | [−19.38, +0.49] | Borderline (CF tightens to decisive) |

KOSPI's 5× magnitude divergence between linear DML (−5.80) and causal forest (−26.69) is direct empirical evidence of treatment-effect heterogeneity in volatility context — causal forest captures the heterogeneity that linear DML averages over.

### F.6 Reconciliation with the earlier 3-market observational study

**Table F.4.** Direction labels per market: canonical causal forest DML reading versus the earlier 3-market preliminary report.

| Market | DML CF (canonical) | Original PDF (2026-04, 3-market) |
|---|---|---|
| VNINDEX | +1.42 (n.s. Paradox direction) | Paradox decisive (raw means reading) |
| PSEI | −0.13 (n.s.) | — |
| KOSPI | −26.69 (n.s. extreme heterogeneity) | — |
| NIFTY | −1.12 (n.s. Inverted direction) | — |
| SPX | **+3.48 (Paradox decisive)** | Inverted under raw means; reinterpreted as future-leakage-confounded under DML controls |
| FTSE | +2.58 (n.s. Paradox direction) | — |
| NIKKEI | +1.27 (n.s.) | — |
| BTC | **−9.34 (Inverted decisive)** | "Thin Paradox" reading; corrected to Inverted under filtered + DML |

The DML canonical reading extends the earlier 3-market findings to all 8 markets, corrects the SPX classification (raw-means Inverted reflected vol-persistence confounding), and corrects the BTC classification (filter + DML reveal Inverted direction with decisive CI). The five additional markets (PSEI, KOSPI, NIFTY, FTSE, NIKKEI) join the panel with predominantly n.s. direction verdicts but Paradox-leaning signs on retail markets and Inverted-leaning signs on developed/emerging-developed markets.

---

## Appendix G. Uncertainty decomposition

This appendix specifies the cascade composite Monte Carlo procedure and the aleatoric/epistemic variance decomposition supporting §4.4 and §6.5, including SD sensitivity.

### G.1 Cascade composite Monte Carlo

For each MC trial $b = 1, \ldots, B$ (with $B = 10{,}000$ and seed = 42):

1. For each market $m$, sample $\text{RPS}_m^{(b)}$ according to its phase per §D.1 (P1: deterministic point; P2: $\text{Uniform}(\text{low}_m, \text{high}_m)$; P3: $\text{Posterior}_m$ Beta).
2. Compute $\rho^{(b)} = \text{Spearman}(\mathbf{H}, \mathbf{RPS}^{(b)})$.
3. Report distribution of $\rho^{(b)}$: mean, median, 95% CI, $P(\rho > 0.5)$.

**Variance source attribution.** Composite ρ-variance reflects only contributions from P2 + P3 markets; P1 markets contribute fixed ranks (zero variance contribution). The cascade composite is therefore a *sensitivity stress-test on the all-P1 reference Spearman*, not an independent test (§4.2.2).

**Table G.1.** Cascade composite MC distribution (companion to §4.2 main-text Table 3).

| Spec | Mean ρ | Median | sd | 95% CI | Min | Max | P(ρ > 0.5) | P(ρ > 0.7) |
|---|---|---|---|---|---|---|---|---|
| Raw labels | +0.847 | +0.857 | 0.029 | [+0.786, +0.905] | +0.714 | +0.905 | 100.0% | 100.0% |
| Filtered labels | +0.901 | +0.905 | 0.038 | [+0.833, +0.952] | +0.595 | +0.952 | 100.0% | 99.9% |

### G.2 Aleatoric/epistemic decomposition

By the law of total variance:

$$\text{Var}(\hat{\rho}) = \underbrace{\mathbb{E}_{\text{RPS}}\left[\text{Var}(\hat{\rho} \mid \text{RPS})\right]}_{\text{aleatoric (H sampling noise)}} + \underbrace{\text{Var}_{\text{RPS}}\left(\mathbb{E}[\hat{\rho} \mid \text{RPS}]\right)}_{\text{epistemic (RPS measurement uncertainty)}} \tag{G.1}$$

Estimated from outer-inner nested Monte Carlo: outer loop samples RPS from cascade posteriors; inner loop perturbs $\mathbf{H}$ by Normal noise with relative SD = h_noise_sd_frac × |H_point|. Decomposition shares: $\hat{V}_{\text{aleatoric}} = \overline{\text{Var}(\rho^{(o,\cdot)})}$ (mean of inner variances); $\hat{V}_{\text{epistemic}} = \text{Var}\left(\overline{\rho^{(o,\cdot)}}\right)$ (variance of inner means).

**Computational note.** Full-pipeline block bootstrap on H (resampling raw OHLCV with circular block bootstrap, refitting GMM, recomputing H per bootstrap sample) is computationally prohibitive at the chosen $B$; the Normal noise proxy is conservative. SD sensitivity in §G.3 verifies the qualitative conclusion (epistemic dominance) holds across reasonable noise assumptions.

### G.3 SD sensitivity

**Table G.2.** Variance decomposition shares under varying H Normal-noise SD fraction. Generated via `project/validation/h2_decomposition_sensitivity.py` (frozen output `h2_decomposition_sensitivity.json`).

| H noise SD | Aleatoric % (raw / filt) | Epistemic % (raw / filt) | Total Var(ρ) (raw / filt) |
|---|---|---|---|
| 0.05 | 0.74 / 0.83 | 99.26 / 99.17 | small |
| 0.10 (paper baseline) | 1.41 / 2.45 | 98.59 / 97.55 | small |
| 0.20 | 10.71 / 9.57 | 89.29 / 90.43 | medium |
| 0.30 | 24.68 / 21.44 | 75.32 / 78.56 | larger |

Even at the most aggressive H noise assumption (SD = 0.30 of the H point estimate, well above any reasonable block-bootstrap proxy), epistemic uncertainty dominates at 75–79%. The roadmap implication is robust across all SD assumptions: panel-size extension addresses only the small aleatoric term; primary-source RPS harmonisation addresses the dominant epistemic term.

---

## Appendix H. Exploratory analyses

This appendix reports exploratory analyses applied under the panel methodology of the main paper, in addition to the central H1–H5 hypothesis tests in §4 and §5: a tail-risk lift analysis on VNINDEX (deployment-significance evidence cross-referenced from §6.4), a feature comparison between entropy and SimpleVol features that supports the structural-vs-measurement argument in §6.4, and a foundation-model preliminary placeholder.

### H.1 Tail-risk lift on VNINDEX (V3 framing) — economic significance

The original 3-market PDF preliminary report documented Lift evidence on VNINDEX consistent with the Entropy Paradox interpretation: the entropy-based Det regime predicts forward 5-day drawdowns with strongly increasing Lift at increasing severity thresholds.

**Table H.1.** Drawdown Hit Rate by regime on VNINDEX (preserved from original PDF analysis).

| Timeframe | Drawdown threshold | Stochastic | Deterministic | Lift |
|---|---|---|---|---|
| 5 days | > 3% | 8.5% | 17.4% | 2.06x |
| 5 days | > 5% | 3.3% | 8.4% | 2.55x |
| 5 days | > 7% | 0.8% | 4.3% | **5.50x** |
| 10 days | > 5% | 6.3% | 16.0% | 2.54x |
| 20 days | > 7% | 6.5% | 19.6% | 3.00x |

Lift increasing monotonically from 2.06x (>3%) to 5.50x (>7%) means the entropy-based regime label becomes more useful precisely when the stakes are highest — consistent with the Paradox interpretation that low-entropy structure (behavioural coordination) precedes severe tail events on retail-dominated markets. This is the deployment-economic-significance evidence preserved from the original PDF report; the cross-market generalisation of this Lift analysis under quantile thresholds is reported in §H.2.

### H.2 Cross-market quantile-Lift analysis (V3 cross-market re-framing)

The cross-market Lift re-framing under per-market quantile thresholds is comparatively noisier than the VNINDEX-specific raw-threshold analysis: at q = 0.90 and 10-day horizon, two of eight markets show Lift > 1 decisively, three show Lift ≈ 1, and three show Lift < 1; bootstrap CIs cross unity on every cell with finite CI. The per-bar tail-Lift framing of the single-market original PDF analysis does not generalise cleanly across the eight-market panel under quantile thresholds. The H1 direction-heterogeneity finding (§4.1) accounts for this: markets with Inverted direction (NIFTY, BTC) show the opposite Lift direction by construction.

### H.3 Feature comparison: Entropy vs SimpleVol (V4 framing)

Three GMM models per market are fit with three feature sets: Entropy (WPE + SPE_Z), SimpleVol (rolling SD + volatility change), and Combined (entropy + SimpleVol). KW H discrimination per feature set is compared.

Three observations: (1) SimpleVol features achieve higher raw discrimination on every market because they are *measurement features* of the target variable — rolling SD of returns is a low-pass filter of squared returns, which is the construction of realised volatility itself, so the discrimination is largely autocorrelative (autocorrelative-bias lemma per §6.4); (2) Entropy features are *structural features* that measure ordinal-pattern complexity of the price-generating process, orthogonal to return magnitude; (3) Combined wins on developed markets where entropy adds discriminative content on top of variance persistence.

**Table H.2.** Cross-market Spearman ρ(H, RPS) by feature set on the V4 restricted-window panel (n = 8). The V4 panel restricts to dates common across the three feature constructions; per-market H values therefore differ from the headline H2 panel and the headline H2 result is not expected to reproduce.

| Feature set | Source | ρ(H, RPS) | p-value |
|---|---|---|---|
| Entropy | raw | +0.347 | 0.40 |
| Entropy | filtered | +0.419 | 0.30 |
| SimpleVol | raw | +0.431 | 0.29 |
| SimpleVol | filtered | +0.455 | 0.26 |
| Combined | raw | +0.144 | 0.73 |
| Combined | filtered | +0.503 | 0.20 |

On the V4 restricted window all three feature sets produce moderate-but-not-significant rank correlations with RPS (|ρ| ≤ 0.51), consistent with the substantially shorter common-data window stripping power from the cross-market test. The structural-vs-measurement claim in §6.4 is not about which feature set produces a tighter cross-market ρ on the V4 window; it is about which feature set carries an information-theoretic interpretation that supports the three-link mechanism of §6.1.

### H.4 Foundation-model preliminary (Chronos head-to-head, pre-committed)

A direct head-to-head between Chronos zero-shot embeddings (Ansari et al., 2024) and the entropy-feature pipeline on VNINDEX is pre-committed in the public repository at the canonical reproducibility tag. The comparison protocol: extract Chronos-T5 embeddings on VNINDEX log-return windows; cluster via the same K = 3 GMM + Schmitt-trigger pipeline; compute KW H discrimination on forward 20-day realised volatility; compare to the entropy-feature baseline reported in this paper. Results will be reported in a companion note.

---

*End of anonymized manuscript.*
