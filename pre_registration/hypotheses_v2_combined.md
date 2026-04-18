# Pre-Registered Hypotheses for Combined Paper V2

Commit date: 2026-04-18
Commit hash: [will be filled after commit]
Branch at pre-registration: v7.2-case-a-validation
Parent commit (HEAD at time of drafting): 03ddfcd152d01f5f98c645dc8d6f105af9d95cb4

## H1: Direction hypothesis (Entropy Paradox systematicity)
On markets where retail participation dominates and circuit breakers are
present (frontier), Kruskal-Wallis H for regime discrimination of forward
20-day realized volatility is statistically significant (p < 0.05) AND
mean(Deterministic fwd vol) > mean(Stochastic fwd vol). On developed markets
(deep liquidity, no daily limits, institutional dominance), this relationship
weakens substantially — defined as either:
  (a) H < 20 (compared to H > 100 on frontier markets), OR
  (b) Directional inversion: mean(Stochastic) >= mean(Deterministic).

## H2: Microstructure ordering hypothesis
Kruskal-Wallis H-statistic correlates positively (Spearman r > 0.5) with
an a priori microstructure index:
  MS_index = 0.4 * circuit_breaker + 0.3 * (1 - institutional_share) +
             0.3 * (1 - log(market_cap_usd))

where circuit_breaker ∈ {0, 1} and institutional_share ∈ [0, 1].

## H3: Persistence hypothesis (Transitional Dominance)
Under identical hysteresis parameterization (δ_hard=0.60, δ_soft=0.35,
t_persist=8), p(Transitional) correlates inversely with developed-market
microstructure. Specifically: frontier markets show p(Transitional) > 0.55;
developed markets show p(Transitional) < 0.50; difference is > 10 percentage
points.

## H4: Temporal structure hypothesis (replication of T3)
Across all markets tested, observed filtered flip rate < 5th percentile of
shuffled-null distribution (10,000 permutations, p < 0.01). This replicates
the T3 test from the VNINDEX-only analysis.

## H5: Parameter robustness hypothesis (replication of T4)
Across all markets tested, p(Transitional) spread across three hysteresis
configurations (A production, B looser, C tighter) is less than 5 percentage
points per market.

## Falsification conditions
- H1 rejected if: frontier market H < 20 OR direction inverted, OR developed
  market H > 50 with correct direction.
- H2 rejected if: Spearman correlation between H-stats and MS_index has
  p-value > 0.10.
- H3 rejected if: any frontier market shows p(Transitional) < 0.45 OR any
  developed market shows p(Transitional) > 0.60.
- H4 rejected if: any market's observed flip rate falls within null
  5th–95th percentile band.
- H5 rejected if: any market shows p(Transitional) spread > 7 percentage
  points across configurations.

## Pre-registered markets (to be tested)
Frontier: VNINDEX (VNINDEX), KSE 100 (^KSE) or SET (^SET.BK),
          PSEi (PSEI.PS) (choose 2 of 3 by data quality)
Emerging: KOSPI (^KS11), SENSEX (^BSESN) or NIFTY 50 (^NSEI),
          BIST 100 (XU100.IS) or BOVESPA (^BVSP) (choose 2 of 3)
Developed: S&P 500 (^GSPC), FTSE 100 (^FTSE) or DAX (^GDAXI),
           Nikkei 225 (^N225) (choose 2 of 3)
Crypto: BTC-USD

Total target: 7–8 markets (including original 3).

## Pre-registered parameters (frozen)
Entropy parameters (Phase 1):
  WPE: m=3, tau=1, window=22
  SPE_Z: m=2, r=0.2*sigma_window, window=60, rolling_z=504
  GMM: k=3, full-covariance, n_init=10, no preprocessing (Plane 1)

Hysteresis parameters (Phase 2):
  Production:        delta_hard=0.60, delta_soft=0.35, t_persist=8
  Robustness-B (looser):  delta_hard=0.50, delta_soft=0.30, t_persist=6
  Robustness-C (tighter): delta_hard=0.70, delta_soft=0.40, t_persist=10

Validation window:
  In-sample: 2016-01-01 to 2026-04-17 (each market, adjusted for data availability)
  Labelable from: 504 trading days after data start (~2 years in)

## Honest-reporting commitments
- All negative results will be reported.
- Any bug fixes will be disclosed in the paper.
- If a pre-registered market fails to produce valid data (e.g., insufficient
  trading days), exclusion will be documented.

## Cross-references to existing validation
These VNINDEX-only results (committed prior to this pre-registration) establish
the baseline that H1–H5 generalize. They are NOT re-tested here; this
pre-registration governs the cross-market generalization.

- T1 event study / robustness: validation/event_study.py (commit 4b146b1 frozen
  KNOWN_EVENTS_VNINDEX pre-T1)
- T2 cross-market flip rate: validation/cross_market_flip_rate.py
- T3 shuffle test: validation/shuffle_test.py (observed 7.77 vs null 118.36/yr,
  p < 1e-4 on VNINDEX)
- T-D regime duration: validation/regime_duration.py
- T4 hysteresis robustness: validation/transitional_dominance_robustness.py
  (2.7 pp spread across 3 configs on VNINDEX)

The V2-combined programme extends T4/T3/T-D from VNINDEX-only to the 7–8 markets
listed above under the same hysteresis and entropy parameterization.
