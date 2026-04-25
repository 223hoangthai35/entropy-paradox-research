# Entropy Paradox Research

**Academic research platform for entropy-based market regime analysis.**

## Purpose

Research artifacts, validation studies, and paper drafts on the Entropy Paradox — the market-microstructure-dependent relationship between permutation entropy and forward realized volatility.

**Companion production software**: [financial-entropy-agent](https://github.com/223hoangthai35/financial-entropy-agent)

## Publications

### Paper v2.1 (April 2026, canonical)

*The Entropy Paradox — 8-market post-COVID evidence under refined statistical architecture with pre-registration transparency.*

**Headline claim**: Paradox magnitude tracks Retail Participation Share (Spearman ρ = 0.754, p = 0.031, n = 8). Pairwise direction (Det > Sto) survives FDR correction on PSEI at the 20-day horizon. Transitional Dominance is a microstructure gradient (continuous ρ(p_tra, RPS) = 0.56).

Summary: [paper_artifacts/paper_v2_1_combined_summary.md](paper_artifacts/paper_v2_1_combined_summary.md). Pre-registration audit: [pre_registration/critique.md](pre_registration/critique.md).

Reproducibility: `git checkout v2.1.3-prereg-audit` (current HEAD) or `v2.1-paper-combined` (canonical paper tag).

### Paper v2 (May 2026, draft — historical, superseded by v2.1)

*Hysteresis-Filtered Regime Classification and Transitional Dominance*

**Earlier finding**: VNINDEX spends 67.8% of trading bars in the intermediate entropy regime with 62-day mean spells. Reframed in v2.1 as a microstructure gradient rather than a frontier-specific result.

### Paper v1 (April 2026 — historical, superseded by v2.1)

*Entropy-Based Regime Classification for Financial Market Risk Surveillance: Evidence from Frontier, Developed, and Cryptocurrency Markets*

**Earlier finding — Entropy Paradox**: Low entropy predicts higher forward volatility on frontier markets (VNINDEX H = 192.43, p < 0.0001), inverts on developed markets (SPX H = 14.25). The 8-market panel in v2.1 sharpens the claim into a microstructure ordering.

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
paper_artifacts/        Paper summaries (v1, v2, v2.1 canonical) and rationales
pre_registration/       Frozen H1-H5 pre-registration and scientific-foundation audit
validation/             V1-V5, T1-T4, and Phase 1/2/2.1 validation scripts and results
skills/                 Core computation modules (quant, ds, data)
scripts/                Calibration and analysis
docs/                   Documentation
CONTEXT.md              Project state anchor for research sessions
architecture.md         Detailed system architecture (v7.2)
```

## Reproducibility

All paper results reproducible via tagged commits. All code public for verification.

Tags:
- `v2.1.3-prereg-audit` — current HEAD (canonical paper + pre-registration audit)
- `v2.1-paper-combined` — canonical v2.1 paper (April 2026)
- `v2.0-paper` — historical Paper v2 state
- `v1.0-paper` — historical Paper v1 state
- `v7.1-production` — v7.1 production baseline

## Author

Hoang Thai — Independent Research (2026)
Pre-MSc candidate, Data Science applications 2027

## License

MIT License for code. Please cite papers if using methodology.
