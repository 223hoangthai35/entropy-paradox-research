# H5 retest — per-market hysteresis optima

Each market's optimum is the (delta_hard, delta_soft, t_persist) that produces a filtered flip rate closest to 7.0/yr (centre of the 4-10/yr band). H5 is retested by perturbing +-0.10 / +-0.05 / +-2 around THAT market's optimum.

| Market | Category | Optimum (dh/ds/tp) | Opt flips/yr | p(Tra) spread | H5 verdict |
|--------|----------|--------------------|--------------|---------------|------------|
| VNINDEX | Frontier | 0.60/0.35/3 | 6.86 | 0.022 | **PASS** |
| PSEI | Frontier | 0.70/0.40/10 | 7.08 | 0.061 | **REJECT** |
| KOSPI | Emerging | 0.80/0.40/13 | 8.58 | 0.070 | **REJECT** |
| NIFTY | Emerging | 0.80/0.20/13 | 6.82 | 0.073 | **REJECT** |
| SPX | Developed | 0.80/0.40/10 | 8.12 | 0.143 | **REJECT** |
| FTSE | Developed | 0.80/0.40/8 | 6.92 | 0.168 | **REJECT** |
| NIKKEI | Developed | 0.80/0.30/5 | 7.08 | 0.046 | **PASS** |
| BTC | Crypto | 0.80/0.30/8 | 7.02 | 0.046 | **PASS** |

## Comparison with fixed-triplet H5 (VNINDEX-calibrated)

The original hysteresis_robustness_v2.py fixed the three configs at {A=0.60/0.35/8, B=0.50/0.30/6, C=0.70/0.40/10} for every market. Those configs are optimal for VNINDEX; for markets with higher raw flip rates (SPX, KOSPI) they all sit tighter than the true optimum, which tends to inflate the observed p(Tra) spread. This retest removes that calibration bias by centring the perturbation on each market's own optimum.
