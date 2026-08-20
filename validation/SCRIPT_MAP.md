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

- `validation/_features.py`
- `validation/_cpcv_splitter.py`
- `validation/_regression_guard.py`
- `validation/markets_n27.py`
- `validation/_smoke_dml.py`

## Scoring the pre-registration

- `validation/scoring/score_h1_h5_as_registered.py`
- `validation/scoring/compare_n8_vs_n27.py`

## H1 — per-market direction (causal forest DML)

- `validation/h1_direction/h1_dml.py`
- `validation/h1_direction/h1_dml_cpcv.py`
- `validation/h1_direction/h1_dml_cpcv_n27.py`
- `validation/h1_direction/h1_dml_filtered.py`
- `validation/h1_direction/h1_dml_no_lagrv.py`
- `validation/h1_direction/h1_dml_tsaware.py`
- `validation/h1_direction/h1_method_comparison.py`
- `validation/h1_direction/h1_location_vs_scale.py`
- `validation/h1_direction/h1_sign_microstructure_test.py`
- `validation/h1_direction/dml_monte_carlo_stability.py`
- `validation/h1_direction/rigor_h1_placebo.py`
- `validation/h1_direction/rigor_h1_placebo_shanghai.py`

## H2 — cross-market magnitude (the paper's finding)

- `validation/h2_magnitude/h2_eta_squared.py`
- `validation/h2_magnitude/h2_eta_squared_n27.py`
- `validation/h2_magnitude/h2_calibrated_kwh.py`
- `validation/h2_magnitude/h2_cascade.py`
- `validation/h2_magnitude/h2_cascade_n27_full.py`
- `validation/h2_magnitude/h2_registered_composite.py`
- `validation/h2_magnitude/h2_jt_n27.py`
- `validation/h2_magnitude/h2_tier_based.py`
- `validation/h2_magnitude/h2_tier_rank_sensitivity.py`
- `validation/h2_magnitude/h2_rps_validation.py`
- `validation/h2_magnitude/h2_rps_bounds.py`
- `validation/h2_magnitude/h2_bayesian_uq.py`
- `validation/h2_magnitude/h2_decomposition_sensitivity.py`
- `validation/h2_magnitude/h2_sensitivity_spe_z.py`
- `validation/h2_magnitude/cross_market_v2.py`

## H3 / H4 / H5 — composition, temporal structure, parameter transport

- `validation/h3_h4_h5/hysteresis_cross_market_v2.py`
- `validation/h3_h4_h5/hysteresis_robustness_v2.py`
- `validation/h3_h4_h5/h5_n27.py`
- `validation/h3_h4_h5/h5_per_market_grid_search.py`
- `validation/h3_h4_h5/shuffle_test.py`
- `validation/h3_h4_h5/regime_duration.py`

## Panel properties reported in the data section and limitations

- `validation/panel_properties/dependence_aware_inference.py`
- `validation/panel_properties/h_comovement_check.py`
- `validation/panel_properties/series_length_diagnostic.py`
- `validation/panel_properties/subperiod_stability.py`
- `validation/panel_properties/causal_labeling_check.py`

## Negative controls and architecture comparisons

- `validation/controls/h2_simplevol_control.py`
- `validation/controls/hmm_baseline.py`
- `validation/controls/h6_chronos_8market.py`
- `validation/controls/entropy_vs_simple_8market.py`
- `validation/controls/tail_lift_8market.py`
- `validation/controls/harv_economic_value.py`

## Cross-market battery behind the interpretive reading (App B.5)

- `validation/mechanism_battery/link_b_tests.py`
- `validation/mechanism_battery/link_b_tests_n27.py`
- `validation/mechanism_battery/link_b_raw_sampen_test.py`
- `validation/mechanism_battery/link_b_volatility_test.py`
- `validation/mechanism_battery/herding_coherence_mediator.py`
- `validation/mechanism_battery/herding_vol_dynamics.py`
- `validation/mechanism_battery/rigor_composition_clr_eiv.py`

## Out-of-sample campaigns and the forward test

- `validation/out_of_sample/oos_n27_common.py`
- `validation/out_of_sample/oos_n27_phase0_data.py`
- `validation/out_of_sample/oos_n27_phase1_repro.py`
- `validation/out_of_sample/oos_n27_phase2_h1.py`
- `validation/out_of_sample/oos_n27_phase345_h2mech.py`
- `validation/out_of_sample/oos_2026q2_extension.py`
- `validation/out_of_sample/oos_2026q2_extension_p2.py`
- `validation/out_of_sample/oos_2026q2_h2_alt_estimators.py`
- `forward_test_2026H2_eval.py`

## Diagnostics and figures

- `validation/diagnostics/gmm_k_sensitivity.py`
- `validation/diagnostics/structural_breaks.py`
- `validation/diagnostics/regime_phase_space_compare.py`
- `validation/diagnostics/garch_vnindex_v2.py`
