"""
27-market panel for n>=26 expansion experiment (NOT canonical paper panel).

Goal: test whether H1 (per-market direction) and H2 (cross-market magnitude)
findings survive when panel is expanded from n=8 to n=27 with MSCI-strict
tier classification + ETH/BNB cryptos added alongside BTC.

REVISIONS:
- Round 1: 7 of 8 original Frontier markets failed yfinance. Replaced with
  Eastern European Frontier (Baltic, Romania) + Argentina + 2 Emerging markets.
- Round 2: OMXTGI Estonia failed CausalForestDML fit (n_sto=60 too thin).
  Replaced with Pakistan (PSX:KSE100) via tvDatafeed. Added Bangladesh
  (DSEBD:DSEX) + Slovenia (LJSE:SBITOP) via tvDatafeed (yfinance lacks history).
- Round 3 (current): user feedback — paper focuses on Paradox direction.
  Reduced Emerging from 10 to 7 (Asian-only); increased Developed by adding
  Singapore STI (Asian); increased Frontier to 8 (added Bangladesh, Slovenia).

Distribution (27 markets, post-revision):
- MSCI Frontier   (8): VNINDEX, BVB, KSE100, DSEX, SBITOP, OMXVGI, OMXRGI, MERV
- MSCI Emerging   (7): KOSPI, NIFTY, BVB, JKSE, SET, SHANGHAI, TWII (Asian-only)
- MSCI Developed  (9): SPX, FTSE, NIKKEI, DAX, CAC, SSMI, ASX, HSI, STI
- Crypto          (3): BTC, ETH, BNB

Geographic distribution: 14 Asian, 13 Non-Asian (Asian-prioritised).
- Asian:    VNINDEX, KSE100, DSEX (Frontier), KOSPI, NIFTY, BVB, JKSE, SET,
            SHANGHAI, TWII (Emerging), NIKKEI, HSI, ASX, STI (Developed)
- Non-Asian: BVB, SBITOP, OMXVGI, OMXRGI, MERV (Frontier), SPX, FTSE, DAX,
             CAC, SSMI (Developed), BTC, ETH, BNB (Crypto)

Note on tier reclassifications vs paper canonical panel (n=8):
- BVB: paper has Frontier (tier_rank=4); MSCI strict = Emerging (tier_rank=3).
  This experiment uses MSCI strict.
- All other paper markets (VNINDEX, KOSPI, NIFTY, SPX, FTSE, NIKKEI, BTC) keep
  the same tier_rank under MSCI as in the paper.

tier_rank scheme (paper convention, retail-share proxy):
- Frontier = 4
- Emerging = 3
- Crypto = 2
- Developed = 1

RPS specifications:
- P1 (authoritative source): 5 markets carried over from paper canonical panel
  (VNINDEX, BVB, KOSPI, NIFTY, NIKKEI)
- P2 (uniform bounds): SPX, FTSE (carried over from paper)
- P3 (Beta posterior): all 20 new markets + BTC. Beta means are heuristic priors
  based on regional retail-share patterns; kappa=10 reflects wide uncertainty.

Data sources:
- vnstock: VNINDEX (Vietnam-specific aggregator)
- yfinance: most markets (free, broad coverage of liquid indices)
- tvdatafeed: KSE100, DSEX, SBITOP (frontier markets unavailable on yfinance;
  TradingView via rongardF/tvdatafeed GitHub package)

This panel is for sensitivity / robustness experimentation only. Paper claims
(byte-for-byte reproducible) remain on the canonical n=8 panel.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 27-market panel
# ---------------------------------------------------------------------------
MARKETS_N27: list[dict[str, Any]] = [
    # ---- MSCI Frontier (n=8) — Asian-prioritised + EU-Frontier + LatAm -----
    {"name": "VNINDEX",  "ticker": "VNINDEX",       "source": "vnstock",     "tier_rank": 4, "category": "Frontier"},
    {"name": "KSE100",   "ticker": "PSX:KSE100",    "source": "tvdatafeed",  "tier_rank": 4, "category": "Frontier"},
    {"name": "DSEX",     "ticker": "DSEBD:DSEX",    "source": "tvdatafeed",  "tier_rank": 4, "category": "Frontier"},
    {"name": "BVB",      "ticker": "BVB:BET",        "source": "tvdatafeed",    "tier_rank": 4, "category": "Frontier"},
    {"name": "SBITOP",   "ticker": "LJSE:SBITOP",   "source": "tvdatafeed",  "tier_rank": 4, "category": "Frontier"},
    {"name": "OMXVGI",   "ticker": "^OMXVGI",       "source": "yfinance",    "tier_rank": 4, "category": "Frontier"},
    {"name": "OMXRGI",   "ticker": "^OMXRGI",       "source": "yfinance",    "tier_rank": 4, "category": "Frontier"},
    {"name": "MERV",     "ticker": "^MERV",         "source": "yfinance",    "tier_rank": 4, "category": "Frontier"},

    # ---- MSCI Emerging (n=7) — Asian-only ----------------------------------
    {"name": "KOSPI",    "ticker": "^KS11",         "source": "yfinance",    "tier_rank": 3, "category": "Emerging"},
    {"name": "NIFTY",    "ticker": "^NSEI",         "source": "yfinance",    "tier_rank": 3, "category": "Emerging"},
    {"name": "PSEI",     "ticker": "PSEI.PS",       "source": "yfinance",    "tier_rank": 3, "category": "Emerging"},
    {"name": "JKSE",     "ticker": "^JKSE",         "source": "yfinance",    "tier_rank": 3, "category": "Emerging"},
    {"name": "SET",      "ticker": "^SET.BK",       "source": "yfinance",    "tier_rank": 3, "category": "Emerging"},
    {"name": "SHANGHAI", "ticker": "000001.SS",     "source": "yfinance",    "tier_rank": 3, "category": "Emerging"},
    {"name": "TWII",     "ticker": "^TWII",         "source": "yfinance",    "tier_rank": 3, "category": "Emerging"},

    # ---- MSCI Developed (n=9) — Western + Asian Developed -----------------
    {"name": "SPX",      "ticker": "^GSPC",         "source": "yfinance",    "tier_rank": 1, "category": "Developed"},
    {"name": "FTSE",     "ticker": "^FTSE",         "source": "yfinance",    "tier_rank": 1, "category": "Developed"},
    {"name": "DAX",      "ticker": "^GDAXI",        "source": "yfinance",    "tier_rank": 1, "category": "Developed"},
    {"name": "CAC",      "ticker": "^FCHI",         "source": "yfinance",    "tier_rank": 1, "category": "Developed"},
    {"name": "SSMI",     "ticker": "^SSMI",         "source": "yfinance",    "tier_rank": 1, "category": "Developed"},
    {"name": "NIKKEI",   "ticker": "^N225",         "source": "yfinance",    "tier_rank": 1, "category": "Developed"},
    {"name": "ASX",      "ticker": "^AXJO",         "source": "yfinance",    "tier_rank": 1, "category": "Developed"},
    {"name": "HSI",      "ticker": "^HSI",          "source": "yfinance",    "tier_rank": 1, "category": "Developed"},
    {"name": "STI",      "ticker": "^STI",          "source": "yfinance",    "tier_rank": 1, "category": "Developed"},

    # ---- Crypto (n=3) ------------------------------------------------------
    {"name": "BTC",      "ticker": "BTC-USD",       "source": "yfinance",    "tier_rank": 2, "category": "Crypto"},
    {"name": "ETH",      "ticker": "ETH-USD",       "source": "yfinance",    "tier_rank": 2, "category": "Crypto"},
    {"name": "BNB",      "ticker": "BNB-USD",       "source": "yfinance",    "tier_rank": 2, "category": "Crypto"},
]


# ---------------------------------------------------------------------------
# Cascade RPS specifications (per-market data quality phase)
# ---------------------------------------------------------------------------
CASCADE_N27: dict[str, dict] = {
    # === P1 (authoritative single primary source — 5 markets from paper) ===
    "VNINDEX":  {"tier": "P1", "type": "point", "value": 0.90,
                 "source": "Vietnam SSC + VinaCapital (authoritative, multi-year convergent)"},
    "PSEI":     {"tier": "P1", "type": "point", "value": 0.68,
                 "source": "PSE 2023 Annual Report (authoritative exchange document)"},
    "KOSPI":    {"tier": "P1", "type": "point", "value": 0.45,
                 "source": "KRX 2026 direct turnover-by-investor-type marketplace"},
    "NIFTY":    {"tier": "P1", "type": "point", "value": 0.40,
                 "source": "NSE India Ownership Report (authoritative)"},
    "NIKKEI":   {"tier": "P1", "type": "point", "value": 0.18,
                 "source": "JPX Trading-by-Investor-Type direct (authoritative)"},

    # === P2 (uniform bounds, competing sources — 2 markets from paper) =====
    "SPX":      {"tier": "P2", "type": "uniform", "low": 0.18, "high": 0.37,
                 "source": "SIFMA ownership (0.18) vs MEMX order flow (0.30-0.37) bounds"},
    "FTSE":     {"tier": "P2", "type": "uniform", "low": 0.15, "high": 0.25,
                 "source": "UK FCA limited public data; bounds from LSE Group estimates"},

    # === P3 (Beta posterior — heuristic priors) =============================
    # ---- Frontier defaults (high retail typical) ----
    "BVB":      {"tier": "P2", "type": "uniform", "low": 0.20, "high": 0.25,
                 "source": "BVB Investor Relations + ASF Romania monthly market reports (trading-value-weighted retail share)"},
    "KSE100":   {"tier": "P3", "type": "beta", "mean": 0.60, "kappa": 10,
                 "source": "Pakistan Stock Exchange — high retail, heuristic prior"},
    "DSEX":     {"tier": "P3", "type": "beta", "mean": 0.55, "kappa": 10,
                 "source": "Dhaka Stock Exchange (Bangladesh) — high retail, heuristic prior"},
    "SBITOP":   {"tier": "P3", "type": "beta", "mean": 0.30, "kappa": 10,
                 "source": "Ljubljana Stock Exchange (Slovenia) — EU-integrated, low retail"},
    "OMXVGI":   {"tier": "P3", "type": "beta", "mean": 0.30, "kappa": 10,
                 "source": "OMX Vilnius (Lithuania) — EU-integrated, heuristic prior"},
    "OMXRGI":   {"tier": "P3", "type": "beta", "mean": 0.35, "kappa": 10,
                 "source": "OMX Riga (Latvia) — EU-integrated, heuristic prior"},
    "MERV":     {"tier": "P3", "type": "beta", "mean": 0.55, "kappa": 10,
                 "source": "Argentina MERVAL — high retail, currency-volatility-driven"},

    # ---- Emerging defaults (Asian) ----
    "JKSE":     {"tier": "P3", "type": "beta", "mean": 0.40, "kappa": 10,
                 "source": "Indonesia Stock Exchange — heuristic prior"},
    "SET":      {"tier": "P3", "type": "beta", "mean": 0.35, "kappa": 10,
                 "source": "Stock Exchange of Thailand — heuristic prior"},
    "SHANGHAI": {"tier": "P3", "type": "beta", "mean": 0.65, "kappa": 10,
                 "source": "Shanghai SE — historically very high retail (~70-80%); heuristic prior"},
    "TWII":     {"tier": "P3", "type": "beta", "mean": 0.40, "kappa": 10,
                 "source": "Taiwan Stock Exchange — heuristic prior"},

    # ---- Developed defaults ----
    "DAX":      {"tier": "P3", "type": "beta", "mean": 0.20, "kappa": 10,
                 "source": "Deutsche Börse — heuristic prior, institutional-dominant"},
    "CAC":      {"tier": "P3", "type": "beta", "mean": 0.20, "kappa": 10,
                 "source": "Euronext Paris — heuristic prior, institutional-dominant"},
    "SSMI":     {"tier": "P3", "type": "beta", "mean": 0.15, "kappa": 10,
                 "source": "SIX Swiss Exchange — heuristic prior, low retail"},
    "ASX":      {"tier": "P3", "type": "beta", "mean": 0.30, "kappa": 10,
                 "source": "ASX — superannuation system raises retail share; heuristic prior"},
    "HSI":      {"tier": "P3", "type": "beta", "mean": 0.35, "kappa": 10,
                 "source": "Hong Kong Stock Exchange — heuristic prior, mid retail"},
    "STI":      {"tier": "P3", "type": "beta", "mean": 0.25, "kappa": 10,
                 "source": "Singapore Exchange — heuristic prior, mid-low retail"},

    # ---- Crypto ----
    "BTC":      {"tier": "P3", "type": "beta", "mean": 0.55, "kappa": 20,
                 "source": "Aggregator estimates (Coinalyze, CryptoCompare); paper canonical"},
    "ETH":      {"tier": "P3", "type": "beta", "mean": 0.55, "kappa": 20,
                 "source": "Aggregator estimates — similar to BTC"},
    "BNB":      {"tier": "P3", "type": "beta", "mean": 0.60, "kappa": 20,
                 "source": "Binance ecosystem — slightly higher retail prior than BTC/ETH"},
}


def panel_summary() -> str:
    """Human-readable summary of the panel."""
    by_cat: dict[str, list[str]] = {}
    for m in MARKETS_N27:
        by_cat.setdefault(m["category"], []).append(m["name"])
    n_total = len(MARKETS_N27)
    lines = [f"n={n_total} panel summary (Asian-prioritised, paper-Paradox-focused):"]
    for cat in ("Frontier", "Emerging", "Developed", "Crypto"):
        ms = by_cat.get(cat, [])
        lines.append(f"  {cat:<10} (n={len(ms)}): {', '.join(ms)}")
    p1 = sum(1 for v in CASCADE_N27.values() if v["tier"] == "P1")
    p2 = sum(1 for v in CASCADE_N27.values() if v["tier"] == "P2")
    p3 = sum(1 for v in CASCADE_N27.values() if v["tier"] == "P3")
    lines.append(f"  Cascade phase distribution: {p1} P1 + {p2} P2 + {p3} P3 = {p1+p2+p3} (vs paper n=8: 5+2+1)")
    # Asian count
    asian = {"VNINDEX", "KSE100", "DSEX", "KOSPI", "NIFTY", "PSEI", "JKSE", "SET",
             "SHANGHAI", "TWII", "NIKKEI", "HSI", "ASX", "STI"}
    n_asian = sum(1 for m in MARKETS_N27 if m["name"] in asian)
    lines.append(f"  Asian markets: {n_asian}/{n_total} ({100*n_asian/n_total:.0f}%)")
    return "\n".join(lines)


if __name__ == "__main__":
    print(panel_summary())
