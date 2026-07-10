# Forward direction test — pre-registered predictions on data that does not yet exist

**Registration date:** 2026-07-10 (validity = the commit/tag timestamp of this file in the
public repository; the registration is effective only once committed and pushed)
**Registered by:** the authors of the entropy regime-volatility coupling manuscript (v3_4)
**Status:** FROZEN. This file must never be edited after the registration commit.
Post-hoc notes, if any, go in a separate dated file.

---

## 1. Purpose

Every existing evidence layer for the per-market D-S direction claims (asymptotic CIs,
rotation-placebo calibration, the 2026-Q2 out-of-sample extension, the n = 27 replication)
was computed on data that already existed when analytic choices were made. Rolling-window
feature construction and Purged K-Fold cross-fitting prevent the *algorithm* from looking
ahead; nothing prevents *researcher-level* selection (markets highlighted, estimator
canonicalized, thresholds chosen) from being conditioned on the realized 2018–2026 sample.
This registration closes that last channel: the predictions below concern data that does
not exist at the registration date, so no analytic path can have conditioned on it.

## 2. Registered predictions

**Evaluation window W:** first trading day on or after **2026-07-13** through **2027-06-30**
(all bars strictly postdate this registration).

**Primary predictions (per-market direction of the conditional partial effect):**

- **P1 — SPX:** ATE(Det vs Sto → forward 20-day realized vol) **> 0** (D-S Paradox direction).
- **P2 — BTC:** ATE **< 0** (D-S Inverted direction).
- **P3 — SHANGHAI:** ATE **> 0** (D-S Paradox direction).

**Secondary predictions (ordering + mechanism):**

- **S1:** the Jonckheere–Terpstra ordered-alternative test on per-market $\eta^2$
  (Developed < Crypto < Emerging < Frontier) over the n = 27 panel, evaluated on the
  extended sample, remains decisive: permutation $p < 0.05$ on raw AND filtered labels.
- **S2:** $\rho(\text{raw SampEn p95}, \text{RPS})$ over the n = 27 panel remains **negative**
  on the extended sample (permutation p reported; sign is the registered claim).

## 3. Frozen evaluation specification

- **Pipeline invariants (unchanged from the manuscript):** WPE m=3, τ=1, window=22;
  price SampEn window=60; SPE_Z strictly-backward rolling 504; GMM K=3 full-covariance
  random_state=42 with centroid-sorted semantic labels; Schmitt-trigger hysteresis
  (δ_hard=0.60, δ_soft=0.35, t_persist=8). Data pull from 2018-01-01.
- **Estimator (P1–P3):** CausalForestDML (n_estimators=300, max_depth=6) + PurgedKFold
  (K=5, embargo=20) on filtered labels, controls and dataset construction exactly as in
  `validation/h1_dml.py::build_dml_dataset` / `validation/h1_dml_cpcv.py`
  at the registration commit. Seeds derive from `zlib.crc32(market_name)`;
  PYTHONHASHSEED=0.
- **Primary evaluation quantity:** the SIGN of the ATE estimated on the full extended
  sample (2018-01-01 → 2027-06-30, fetched fresh at evaluation time and frozen as a
  checksummed snapshot; yfinance end-exclusivity handled as in
  `validation/oos_n27_common.py`). Full-sample estimation is pre-chosen for power;
  the post-registration slice W alone (~240 bars) is additionally reported
  descriptively but is NOT the registered criterion.
- **Evaluation script:** `validation/forward_test_2026H2_eval.py` at the registration
  commit (P1–P3). S1–S2 are evaluated by re-running the frozen n = 27 campaign scripts
  (`validation/oos_n27_phase0_data.py`, `_phase1_repro.py`, `_phase345_h2mech.py`)
  with `OOS_END = "2027-06-30"`.
- **Evaluation date:** the registered evaluation is the FIRST run of the evaluation
  script on or after **2027-07-01**. Interim runs are permitted for monitoring but are
  not the registered outcome (the script labels them as such).

## 4. Pre-specified success / failure criteria

| Grade | Criterion |
|---|---|
| **Pass (primary)** | Sign of full-sample ATE matches prediction (per P1/P2/P3, judged independently) |
| Pass (strong) | Additionally, the asymptotic 95% CI excludes zero in the predicted direction |
| Pass (strongest) | Additionally, rotation-placebo calibrated one-sided $p \leq 0.10$ (N = 100 rotations, same protocol as manuscript App F.6) |
| **Fail** | Sign of full-sample ATE opposite to prediction |

S1: pass iff both permutation p-values < 0.05. S2: pass iff the correlation is negative.

## 5. Pre-specified interpretation (written before outcomes are known)

- Each prediction is judged independently; partial outcomes are reported as such.
- A **failed** direction prediction does not falsify the paper's heterogeneity
  characterization; it indicates the per-market direction is time-varying — itself
  informative and to be reported as a finding, not rescued post hoc.
- A failed S1 would materially weaken the H2 tier-scaling claim and will be stated so.
- **The outcome will be published regardless of result** (revision, companion note, or
  public archive update), together with the evaluation snapshot checksums.

## 6. What may NOT change after registration

Predictions; window W; estimator specification; evaluation quantity; success criteria;
interpretation rules. Anything not listed here (e.g., additional exploratory analyses on
the new data) is permitted but must be labeled post hoc.
