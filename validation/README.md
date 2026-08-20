# validation/ — script map

One frozen output under `results_v2/` per canonical script; every number in the manuscript traces to one of these. Shared modules are imported as `validation.<name>` — do not move them. Superseded one-shot scripts live in `attic/` (kept for the record; their frozen outputs remain in `results_v2/`).

## Shared infrastructure (imported by everything — do not move/rename)

| Module | Role |
|---|---|
| `_features.py` | Pinned feature recipe + `run_full_pipeline()` — the single entry point every test imports |
| `_cpcv_splitter.py` | PurgedKFold (K=5, embargo 20) |
| `markets_n27.py` | n=27 panel definition (tickers, sources, tiers) |
| `oos_n27_common.py` | Shared constants for the window-stability campaign |
| `_smoke_dml.py` | Dev smoke test |

## H1 — per-market direction (CF-DML)

`h1_dml.py` (dataset builder + MARKETS), `h1_dml_cpcv.py` (canonical estimator), `h1_dml_cpcv_n27.py` (expansion panel), spec-grid variants (`h1_dml_filtered.py`, `h1_dml_no_lagrv.py`, `h1_dml_tsaware.py`, `h1_method_comparison.py` — App F.1), `h1_sign_microstructure_test.py` (panel-level sign×RPS test), `rigor_h1_placebo.py` + `rigor_h1_placebo_shanghai.py` (rotation-placebo calibration, App F.6).

## H2 — cross-market magnitude (RPS-primary)

Core: `h2_eta_squared.py` / `h2_eta_squared_n27.py` (KW-H + η² per market), `h2_rps_validation.py` (RPS-primary artifact), `h2_registered_composite.py` (registered MS_index scored as registered), `h2_jt_n27.py` (ordered tier-block JT), `h2_calibrated_kwh.py` (rotation-calibrated H), `h2_simplevol_control.py` (trivial-feature control), `h2_tier_based.py` (tier JT z-test, n=8), `h2_cascade.py` + `h2_cascade_n27_full.py` (cascade MC), `rigor_composition_clr_eiv.py` (clr errors-in-variables, B.5.3).
Sensitivity: `h2_sensitivity_spe_z.py`, `gmm_k_sensitivity.py`, `h2_tier_rank_sensitivity.py`, `h2_rps_bounds.py`, `h2_bayesian_uq.py`, `h2_decomposition_sensitivity.py` (App G).

## H3 / H4 / H5 — supporting hypotheses

`regime_duration.py`, `shuffle_test.py` (H4 block-permutation), `hysteresis_cross_market_v2.py`, `hysteresis_robustness_v2.py` (H5 shared-parameter), `h5_per_market_grid_search.py` (H5 own-optimum).

## Link B / mechanism batteries (App B.5)

`link_b_tests.py`, `link_b_tests_n27.py`, `link_b_raw_sampen_test.py`, `link_b_volatility_test.py`, `tail_lift_8market.py`, `entropy_vs_simple_8market.py`.

## Controls and benchmarks

`h6_chronos_8market.py` (foundation-model negative control, App H), `garch_vnindex_v2.py`, `structural_breaks.py` (App C.6), `regime_phase_space_compare.py` (Fig C.1), `cross_market_v2.py` (panel constants + flip rates).

## Window-stability campaigns (App J archives)

`oos_2026q2_extension.py`, `oos_2026q2_extension_p2.py`, `oos_2026q2_h2_alt_estimators.py` (n=8); `oos_n27_phase0_data.py` … `oos_n27_phase345_h2mech.py` (n=27). These keep `REPRO_END = 2026-04-17` by design of their two-window comparison protocol.

## Forward pre-registration

`forward_test_2026H2_eval.py` — frozen evaluator for the 2026-07-10 registration (window through 2027-06-30). Do not modify.

## attic/

Superseded or one-shot scripts retained for provenance: broken-path eval helpers, pre-refinement cascade variants (`h2_cascade_n27.py`, `_corrected.py`, `_pseiP2.py`), the KOSPI-scenario re-test, the single-market Chronos predecessor, one-shot augmenters/addenda. Their frozen outputs remain in `results_v2/`; run nothing from here.
