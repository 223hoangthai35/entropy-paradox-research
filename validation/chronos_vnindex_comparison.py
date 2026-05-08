"""Foundation-model head-to-head: Chronos zero-shot vs Entropy GMM regime classification on VNINDEX.

This script implements the §8.5 / §9 follow-up identified in the JFDS revision:
  comparing learned representations (Chronos zero-shot embeddings) against
  hand-engineered information-theoretic features (WPE + SPE_Z) on the same
  VNINDEX series, GMM K=3, identical Schmitt-trigger hysteresis filter,
  identical forward-vol evaluation horizon.

Status: SKELETON — requires `pip install chronos-forecasting` and one-time
Chronos model download (~250 MB for chronos-t5-small; larger for medium/large).

Run:
    pip install chronos-forecasting torch
    python validation/chronos_vnindex_comparison.py

Output:
    results_v2/chronos_vnindex_comparison.json
    results_v2/chronos_vnindex_phase_space.png

Methodology:
  1. Load VNINDEX OHLCV via existing `validation/_features.py` machinery
     (route through `run_full_pipeline()` for no-leakage controls).
  2. Compute log returns; normalize per-window for Chronos input range.
  3. For each rolling window of W bars, extract Chronos encoder hidden
     states (bottleneck embedding). Reduce dim via PCA to 2 components
     (matching the (WPE, SPE_Z) plane dimensionality).
  4. Fit GMM K=3 with same random_state=42, same n_init=10 as entropy pipeline.
  5. Apply identical Schmitt-trigger hysteresis (delta_hard=0.60, delta_soft=0.35,
     t_persist=8) to posterior probability sequences.
  6. Compute on the same labelable bars used by entropy pipeline:
     - KW H magnitude
     - Cliff's δ for forward 20-day realized vol Det vs Sto
     - Filtered flips/yr
     - Regime composition p(Det/Trans/Sto)
  7. Compare with the entropy-feature baseline values from
     `cross_market_summary_v2.csv` (VNINDEX row).

Expected outcomes (per §8.5 hypothesis):
  - Chronos likely achieves higher KW H magnitude (foundation models pick up
    variance dynamics analogously to SimpleVol features).
  - Chronos may NOT preserve the Cliff δ direction signal (entropy structural
    advantage at signal-rich frontier markets).
  - Filter flip rate and regime composition: open question.

If Chronos matches entropy on direction + composition while exceeding on
magnitude → §8.5 measurement-vs-structural framing requires substantial
revision.
If Chronos exceeds on magnitude but loses direction → §8.5 framing
strengthened.

NOTE: Implementation of the Chronos branch is left as committed follow-up.
The author has scheduled this work for the post-revision phase; the design
above is the pre-committed protocol.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results_v2"


def load_vnindex_log_returns():
    """Load VNINDEX log returns over the post-COVID window via existing pipeline."""
    raise NotImplementedError(
        "Route through validation/_features.py:run_full_pipeline() for no-leakage controls. "
        "Needs vnstock/yfinance data ingestion + the same SPE_Z 504-day labeling-floor convention."
    )


def chronos_zero_shot_embedding(returns: np.ndarray, window: int = 22, model_name: str = "amazon/chronos-t5-small"):
    """Extract Chronos encoder hidden states for each rolling window.

    Returns: array of shape (T - window + 1, d_embedding).
    """
    raise NotImplementedError(
        "Implementation: from chronos import ChronosPipeline; "
        "pipeline = ChronosPipeline.from_pretrained(model_name, torch_dtype=torch.float32); "
        "for each window [t-W+1 .. t] feed to pipeline.embed(); collect bottleneck states."
    )


def project_to_2d(embeddings: np.ndarray) -> np.ndarray:
    """PCA to 2 components matching (WPE, SPE_Z) plane dimensionality."""
    from sklearn.decomposition import PCA
    return PCA(n_components=2, random_state=42).fit_transform(embeddings)


def fit_gmm_and_hysteresis(features_2d: np.ndarray):
    """Re-uses skills/ds_skill.py:HysteresisGMMWrapper for label parity."""
    raise NotImplementedError(
        "Import HysteresisGMMWrapper from project skills/ds_skill.py to ensure identical "
        "GMM (K=3, full-cov, n_init=10, random_state=42) and Schmitt-trigger parameters "
        "(delta_hard=0.60, delta_soft=0.35, t_persist=8). Returns (raw_labels, filtered_labels, posteriors)."
    )


def evaluate_comparison_metrics(labels, fwd_vol_20d, posteriors):
    """KW H, Cliff δ Det-vs-Sto, regime composition, flips/yr."""
    raise NotImplementedError(
        "Re-use the metric functions from validation/cross_market_v2.py for parity "
        "with entropy-baseline numbers in cross_market_summary_v2.csv."
    )


def main():
    print("Chronos vs Entropy head-to-head — VNINDEX skeleton")
    print("=" * 60)
    print("Status: not yet implemented; protocol committed in this script.")
    print("Required:")
    print("  pip install chronos-forecasting torch scikit-learn")
    print("  ~250 MB Chronos-t5-small download (or larger variants)")
    print("Estimated runtime: 30-90 min depending on model size + data length")
    print()
    print("Pre-committed protocol:")
    print("  1. Load VNINDEX log returns post-COVID window via run_full_pipeline()")
    print("  2. Chronos zero-shot embeddings on rolling W=22 windows")
    print("  3. PCA to 2D (matching entropy plane dimensionality)")
    print("  4. GMM K=3 + Schmitt-trigger hysteresis (identical params)")
    print("  5. Compare KW H + Cliff δ + regime composition + flips/yr")
    print()
    print("Output JSON written to:", RESULTS_DIR / "chronos_vnindex_comparison.json")


if __name__ == "__main__":
    main()
