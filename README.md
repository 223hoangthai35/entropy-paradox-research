# Entropy Paradox Research

**Academic research platform for entropy-based market regime analysis.**

## Purpose

Research artifacts, validation studies, and paper drafts on the Entropy Paradox — the market-microstructure-dependent relationship between permutation entropy and forward realized volatility.

**Companion production software**: [financial-entropy-agent](https://github.com/223hoangthai35/financial-entropy-agent)

## Publications

### Paper v1 (April 2026)

*Entropy-Based Regime Classification for Financial Market Risk Surveillance: Evidence from Frontier, Developed, and Cryptocurrency Markets*

**Key finding — Entropy Paradox**: Low entropy predicts higher forward volatility on frontier markets (VNINDEX H=192.43, p<0.0001), inverts on developed markets (SPX H=14.25).

### Paper v2 (May 2026, in preparation)

*Hysteresis-Filtered Regime Classification and Transitional Dominance*

**Key finding — Transitional Dominance**: VNINDEX spends 67.8% of trading bars in intermediate entropy regime with 62-day mean spells, revealing frontier fragility operates through regime persistence rather than transition frequency.

Reproducibility: `git checkout v2.0-paper`

## Validation Framework

### Paper v1 Tests (V1-V5)
- V1: Kruskal-Wallis regime discrimination (H=192.43, p<0.0001)
- V2: GARCH forecast benchmarking
- V3: Tail risk Lift ratios (5.5x for >7% drawdowns)
- V4: Entropy vs simple volatility feature comparison
- V5: Cross-market paradox direction (VN YES, SPX INVERTED, BTC YES-thin)

### Paper v2 Tests (T1-T4)
- T1: Event study (pre-registered macro events, null result honestly reported)
- T2: Cross-market flip rate (rejected initial hypothesis, revealed paradox level 2)
- T3: Shuffle test for temporal structure (p<1e-4, decisive PASS)
- T4: Hysteresis parameter robustness (2.7pp spread across configs, PASS)

## Repository Structure

```
papers/                 Paper PDFs and Section 5.6 drafts
validation/             V1-V5 + T1-T4 validation scripts
skills/                 Core computation modules
scripts/                Calibration and analysis
docs/                   Documentation
CONTEXT.md              Project state anchor for research sessions
architecture.md         Detailed system architecture (v7.2)
```

## Reproducibility

All paper results reproducible via tagged commits. All code public for verification.

Tags:
- `v2.0-paper` — Paper v2 state (current HEAD)
- `v7.1-production` — v7.1 production baseline

## Author

Hoang Thai — Independent Research (2026)
Pre-MSc candidate, Data Science applications 2027

## License

MIT License for code. Please cite papers if using methodology.
