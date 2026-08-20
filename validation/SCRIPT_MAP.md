# Script map — `validation/`

Seventy-one scripts sit flat in this directory rather than in subfolders, and
that is deliberate: sixty-eight of them resolve their own paths from
`os.path.dirname(__file__)` -- thirty-five write into `results_v2/` relative to
themselves and forty-six reach the repository root through `..`. Moving a script
one level down would silently redirect its frozen output into a new directory
instead of failing, which is the one failure mode this archive cannot afford.
This map is the navigation layer instead.

Scripts superseded during revision live in [`attic/`](attic/) and are kept so an
earlier result can always be traced to the script that produced it.

## Shared infrastructure — imported by everything else

- `_features.py`
- `_cpcv_splitter.py`
- `_regression_guard.py`
- `markets_n27.py`
- `_smoke_dml.py`

## Scoring the pre-registration

- `score_h1_h5_as_registered.py`
- `compare_n8_vs_n27.py`

## H1 — per-market direction (causal forest DML)

- `h1_dml.py`
- `h1_dml_cpcv.py`
- `h1_dml_cpcv_n27.py`
- `h1_dml_filtered.py`
- `h1_dml_no_lagrv.py`
- `h1_dml_tsaware.py`
- `h1_method_comparison.py`
- `h1_location_vs_scale.py`
- `h1_sign_microstructure_test.py`
- `dml_monte_carlo_stability.py`
- `rigor_h1_placebo.py`
- `rigor_h1_placebo_shanghai.py`

## H2 — cross-market magnitude (the paper's finding)

- `h2_eta_squared.py`
- `h2_eta_squared_n27.py`
- `h2_calibrated_kwh.py`
- `h2_cascade.py`
- `h2_cascade_n27_full.py`
- `h2_registered_composite.py`
- `h2_jt_n27.py`
- `h2_tier_based.py`
- `h2_tier_rank_sensitivity.py`
- `h2_rps_validation.py`
- `h2_rps_bounds.py`
- `h2_bayesian_uq.py`
- `h2_decomposition_sensitivity.py`
- `h2_sensitivity_spe_z.py`
- `cross_market_v2.py`

## H3 / H4 / H5 — composition, temporal structure, parameter transport

- `hysteresis_cross_market_v2.py`
- `hysteresis_robustness_v2.py`
- `h5_n27.py`
- `h5_per_market_grid_search.py`
- `shuffle_test.py`
- `regime_duration.py`

## Panel properties reported in the data section and limitations

- `dependence_aware_inference.py`
- `h_comovement_check.py`
- `series_length_diagnostic.py`
- `subperiod_stability.py`
- `causal_labeling_check.py`

## Negative controls and architecture comparisons

- `h2_simplevol_control.py`
- `hmm_baseline.py`
- `h6_chronos_8market.py`
- `entropy_vs_simple_8market.py`
- `tail_lift_8market.py`
- `harv_economic_value.py`

## Cross-market battery behind the interpretive reading (App B.5)

- `link_b_tests.py`
- `link_b_tests_n27.py`
- `link_b_raw_sampen_test.py`
- `link_b_volatility_test.py`
- `herding_coherence_mediator.py`
- `herding_vol_dynamics.py`
- `rigor_composition_clr_eiv.py`

## Out-of-sample campaigns and the forward test

- `oos_n27_common.py`
- `oos_n27_phase0_data.py`
- `oos_n27_phase1_repro.py`
- `oos_n27_phase2_h1.py`
- `oos_n27_phase345_h2mech.py`
- `oos_2026q2_extension.py`
- `oos_2026q2_extension_p2.py`
- `oos_2026q2_h2_alt_estimators.py`
- `forward_test_2026H2_eval.py`

## Diagnostics and figures

- `gmm_k_sensitivity.py`
- `structural_breaks.py`
- `regime_phase_space_compare.py`
- `garch_vnindex_v2.py`
