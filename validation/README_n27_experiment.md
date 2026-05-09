# n=27 Expansion Experiment — Setup Notes

**Goal:** test whether H1 (per-market direction) and H2 (cross-market magnitude) findings survive when panel size is expanded from n=8 (paper canonical) to n=27 with MSCI-strict tier classification + ETH/BNB cryptos added alongside BTC.

**Status:** infrastructure ready; not yet executed. Paper unchanged.

## Panel composition (27 markets)

| Tier | n | Markets |
|---|---|---|
| MSCI Frontier (tier_rank=4) | 8 | VNINDEX, KSE100, NGSE, BETI, OMXIPI, MASI, CSEALL, KASE |
| MSCI Emerging (tier_rank=3) | 8 | KOSPI, NIFTY, PSEI, BVSP, JKSE, SET, SHANGHAI, TWII |
| MSCI Developed (tier_rank=1) | 8 | SPX, FTSE, NIKKEI, DAX, CAC, SSMI, ASX, HSI |
| Crypto (tier_rank=2) | 3 | BTC, ETH, BNB |

**Note on PSEI reclassification:** paper canonical n=8 has PSEI in Frontier (tier_rank=4); MSCI strict has Philippines as Emerging (tier_rank=3). The n=27 experiment uses MSCI strict — PSEI moves to Emerging tier. Paper's H2 result is unaffected since PSEI's RPS value (0.68 from PSE 2023 Annual Report) is unchanged; only the categorical tier label shifts.

## Cascade RPS specifications

- **P1 (5 markets, authoritative):** VNINDEX (0.90), PSEI (0.68), KOSPI (0.45), NIFTY (0.40), NIKKEI (0.18) — all carried over from paper canonical panel
- **P2 (2 markets, uniform bounds):** SPX [0.18, 0.37], FTSE [0.15, 0.25] — carried over
- **P3 (20 markets, Beta posterior):** all 19 new markets + BTC. Beta means are heuristic priors based on regional retail-share patterns; κ=10 (κ=20 for crypto) reflects wide uncertainty

## Files

| File | Purpose |
|---|---|
| `markets_n27.py` | Panel definition + cascade RPS specs |
| `h1_dml_cpcv_n27.py` | H1 canonical DML test on n=27 |
| `h2_eta_squared_n27.py` | H2 KW H + η² + cross-market Spearman |
| `h2_cascade_n27.py` | H2 cascade composite Monte Carlo |
| `results_v2/n27_experiment/` | Output directory (JSON files) |

## Execution order

```bash
# Step 1: data fetch + GMM fit + KW H per market (~10–15 min)
python validation/h2_eta_squared_n27.py

# Step 2: cascade composite MC (depends on Step 1 output; ~1–2 min)
python validation/h2_cascade_n27.py

# Step 3: H1 DML on each market (~80 min; depends on success rate of yfinance fetches)
python validation/h1_dml_cpcv_n27.py
```

Each script:
- **Skips markets that fail data fetch** (yfinance ticker invalid, insufficient bars after 504-day SPE_Z floor, or treatment-balance failure for H1) rather than crashing the whole panel
- Logs `skip_reason` per market in JSON output
- Reports n_succeeded / n_skipped at end

## Expected risks / known issues

1. **Data fetch reliability** — small frontier markets (NGSE, KASE, MASI, CSE) may have spotty yfinance coverage. Expect 1–3 markets to fail fetch.
2. **Treatment-balance failure** — for H1, markets with extremely concentrated regime distributions (rare Sto regime) will fail PurgedKFold treatment-balance check (paper: VNINDEX/PSEI/NIFTY fail under linear DML; under causal forest all 8 paper markets succeed).
3. **Cascade composite variance** — increase from paper's 1 P3 market to 20 P3 markets means P(ρ > 0.5) likely lower than 100% on n=27 cascade composite; the all-P1 reference is the cleaner comparison for "central tendency under best-data-quality assumption".
4. **Heuristic RPS priors** — P3 Beta means are educated guesses, not authoritative readings. For markets where this matters, replace with sourced values before drawing inferences.

## What to look for in results

### H1 (direction heterogeneity)

Question: does the per-market direction pattern (Paradox-leaning frontier/retail markets, Inverted-leaning developed markets) hold on n=27?

Expected: more markets clear "decisive" verdict (|CI| not crossing zero) at n=27 because some additional markets may have stronger raw effects. Look for:
- Pattern stability (Frontier paradox-direction signs, Developed inverted-direction signs)
- New decisive verdicts on additional markets
- Consistency with paper canonical SPX (decisive Paradox) + BTC (decisive Inverted) findings

### H2 (magnitude scaling)

Question: does Spearman ρ(H, tier) and Spearman ρ(H, RPS) survive at n=27?

Paper canonical n=8 reference:
- ρ(H_raw, tier) = 0.927 (p=0.001)
- ρ(η²_raw, tier) = 0.964 (p=0.0001)
- ρ(H_raw, RPS) = 0.857 (p=0.007)
- Cascade composite raw: mean ρ = 0.847, P(ρ>0.5)=100%

Expected at n=27:
- p-values much smaller (more power)
- ρ point estimates may shift (n=27 introduces 19 new markets with heuristic RPS priors)
- Tier-based test more reliable than RPS-based test (tier observed; RPS heuristic for new markets)

### Strategic effects

If H1 + H2 results survive at n=27 → strong confirmation; future paper revision can use larger panel.

If results weaken at n=27 → indicates n=8 results may have been sensitive to specific market choices; need to investigate which markets drive the change.

If specific subset of new markets misbehaves → that's empirical signal about cross-market heterogeneity itself (consistent with paper's heterogeneous-effects framework).

## Important: paper unchanged

This is a **separate experiment** for sensitivity testing. The paper's canonical n=8 panel and all results in §4–§5 + Appendices E–G remain unchanged. Results from n=27 experiment are NOT used in paper claims.
