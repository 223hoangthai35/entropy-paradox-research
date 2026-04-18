# Paper v1 — Entropy Paradox (April 2026)

**Title.** *Entropy-Based Regime Classification for Financial Market Risk
Surveillance: Evidence from Frontier, Developed, and Cryptocurrency Markets.*

**Reproducibility tag.** `v1.0-paper` (pre-hysteresis v7.0 baseline; master branch).

---

## 1. Core claim — the Entropy Paradox

Low permutation entropy on a frontier equity index (VNINDEX) is associated
with **higher** realised forward volatility, not lower. The sign flips
between VNINDEX (frontier) and SPX (developed), identifying the paradox as
microstructure-dependent rather than universal.

> Thermodynamic intuition: low entropy ⇒ order ⇒ stability.
> Market microstructure: low entropy ⇒ coordinated retail herding ⇒ fragility.

## 2. Data window

Three markets, ~10-year window (spans pre-COVID + COVID + post-COVID):

| Market   | Ticker    | Source   |
|----------|-----------|----------|
| VNINDEX  | VNINDEX   | vnstock  |
| SP500    | ^GSPC     | yfinance |
| BTC-USD  | BTC-USD   | yfinance |

## 3. Methodology (frozen in v7.0)

- **Plane 1 features:** WPE (m=3, τ=1, window=22) and SPE_Z
  (z-score of rolling Sample Entropy on log-returns).
  In v7.0 SPE_Z used a **global** z-score — known to leak look-ahead;
  tightened to rolling window=504 in v7.1.
- **Classifier:** Gaussian Mixture Model, k=3, full covariance, random_state=42.
  Centroids sorted by entropy → labels **Deterministic (0) / Transitional (1) / Stochastic (2)**.
- **Risk engine:** tri-vector composite score (SPE+WPE+volume divergence).
  Deprecated in v7.1 in favour of GARCH-X.

## 4. Headline validation (V1–V5)

| Test | Result | Headline |
|------|--------|----------|
| V1   | Plane-1 structure | Raw [WPE, SPE_Z] topology separates three clusters cleanly |
| V2   | GARCH benchmarking | Regime-conditional vol bands better-calibrated than static GARCH |
| V3   | Tail lift | ~5.5× Lift on >7% drawdown events when Deterministic regime active |
| V4   | Simple-vol comparison | Simple-vol wins on overall-vol prediction; entropy wins on tail events / regime identity |
| V5   | Cross-market paradox direction | VNINDEX H=192.43 (Paradox); SPX H=14.25 (Inverted); BTC H=thin |

Kruskal–Wallis on regime vs forward realized volatility: VNINDEX p < 0.0001
(decisive), SPX inverted, BTC marginal.

## 5. What v1 did not resolve

- **Flip-rate cadence** was not directly evaluated — raw GMM labels flip
  ~28/yr on VNINDEX, which paper v1 treated as noise to be smoothed
  downstream, not as signal.
- **Regime duration** was not characterised; the paper's claims concern
  *regime-conditional return distributions*, not *how long a regime lasts*.
- **Global SPE_Z** was retained for dashboard overlays; look-ahead was not
  flagged as a threat in v1.

These omissions motivated paper v2.

## 6. Reproducibility

```
git checkout v1.0-paper
python validation/cross_market_flip_rate.py   # V5 (note: v1 used global SPE_Z)
```

Original 3-market results are preserved in `validation/results/`.
The paper v1 numbers use the **global** SPE_Z and **pre-hysteresis** labels;
they are not directly comparable to the numbers in papers v2 and v2.1.
