"""
Purged K-Fold and Combinatorial Purged Cross-Validation splitters,
sklearn-compatible.

Reference: López de Prado (2018), "Advances in Financial Machine Learning",
Chapter 7. Designed for financial ML where:

  - Forward-looking targets create temporal overlap between consecutive
    observations (here: forward 20-day RV with 19-bar overlap)
  - Serial autocorrelation in residuals violates IID assumption
  - Standard random K-fold leaks future into past predictions
  - Pure forward-chaining (TimeSeriesSplit) wastes early data + fails
    when class distribution is non-stationary (rare classes only emerging
    late in the sample)

Two splitter classes provided:

(A) PurgedKFold — DISJOINT test folds (compatible with DML cross-fitting):
    K-fold over contiguous blocks; for each test fold k, purge training
    samples within `embargo` bars of test boundaries. Each observation is
    out-of-fold exactly ONCE => standard cross-fitting property preserved.
    THIS is the correct splitter for DML on time-series with overlapping
    targets (López de Prado §7.3).

(B) CombinatorialPurgedKFold — OVERLAPPING test sets across combinations
    (used for backtest path aggregation in trading strategy backtests, not
    DML cross-fitting). Each observation appears in multiple test sets
    across the C(K, K_test) combinations. Provided here for completeness
    but NOT compatible with econml DML cross-fitting which requires
    disjoint test folds.

Both are compatible with sklearn cross-validation API; PurgedKFold can be
passed as `cv=` argument to econml DML estimators.
"""
from __future__ import annotations

from itertools import combinations
from typing import Iterator, Optional

import numpy as np
from sklearn.model_selection import BaseCrossValidator


class PurgedKFold(BaseCrossValidator):
    """Purged K-Fold cross-validation per López de Prado (2018, Ch. 7.3).

    K-fold over CONTIGUOUS blocks (no shuffle), with embargo zone purged
    from training set around each test fold. Test folds are DISJOINT
    (each observation is out-of-fold exactly once), so this splitter is
    compatible with cross-fitting estimators (DML, etc.).

    Parameters
    ----------
    n_splits : int, default=5
        Number of contiguous folds K.
    embargo : int, default=20
        Number of bars to purge from training on each side of every test
        fold boundary. Should match or exceed the forward-overlap window
        of the target variable (e.g., 20 for forward 20-day RV).
    """

    def __init__(self, n_splits: int = 5, embargo: int = 20):
        if n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        if embargo < 0:
            raise ValueError("embargo must be >= 0")
        self.n_splits = n_splits
        self.embargo = embargo

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        return self.n_splits

    def _block_boundaries(self, n: int) -> list[tuple[int, int]]:
        block_size = n // self.n_splits
        return [
            (k * block_size, (k + 1) * block_size if k < self.n_splits - 1 else n)
            for k in range(self.n_splits)
        ]

    def split(self, X, y=None, groups=None) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        n = len(X) if hasattr(X, "__len__") else X.shape[0]
        blocks = self._block_boundaries(n)
        all_idx = np.arange(n)
        for k in range(self.n_splits):
            start, end = blocks[k]
            test_idx = np.arange(start, end)
            purge_start = max(0, start - self.embargo)
            purge_end = min(n, end + self.embargo)
            purge_mask = np.zeros(n, dtype=bool)
            purge_mask[purge_start:purge_end] = True
            train_idx = all_idx[~purge_mask]
            yield train_idx, test_idx


class CombinatorialPurgedKFold(BaseCrossValidator):
    """Combinatorial Purged Cross-Validation (CPCV) per López de Prado (2018).

    Parameters
    ----------
    n_splits : int, default=6
        Number of contiguous blocks K.
    n_test_splits : int, default=2
        Number of blocks per test set K_test. Total splits = C(K, K_test).
    embargo : int, default=20
        Number of bars to embargo (purge) on each side of every test block
        from the training set. Should match or exceed the forward-overlap
        window of the target variable.
    """

    def __init__(self, n_splits: int = 6, n_test_splits: int = 2, embargo: int = 20):
        if n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        if n_test_splits < 1 or n_test_splits >= n_splits:
            raise ValueError("n_test_splits must be in [1, n_splits-1]")
        if embargo < 0:
            raise ValueError("embargo must be >= 0")
        self.n_splits = n_splits
        self.n_test_splits = n_test_splits
        self.embargo = embargo

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        from math import comb
        return comb(self.n_splits, self.n_test_splits)

    def _block_boundaries(self, n: int) -> list[tuple[int, int]]:
        """Return (start, end_exclusive) for each of K contiguous blocks."""
        block_size = n // self.n_splits
        boundaries = []
        for k in range(self.n_splits):
            start = k * block_size
            end = (k + 1) * block_size if k < self.n_splits - 1 else n
            boundaries.append((start, end))
        return boundaries

    def split(self, X, y=None, groups=None) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        n = len(X) if hasattr(X, "__len__") else X.shape[0]
        blocks = self._block_boundaries(n)
        all_idx = np.arange(n)

        for test_block_combo in combinations(range(self.n_splits), self.n_test_splits):
            # Build test index set
            test_idx_list = []
            for k in test_block_combo:
                start, end = blocks[k]
                test_idx_list.append(np.arange(start, end))
            test_idx = np.sort(np.concatenate(test_idx_list))

            # Build purge zones around each test block
            purge_mask = np.zeros(n, dtype=bool)
            for k in test_block_combo:
                start, end = blocks[k]
                purge_start = max(0, start - self.embargo)
                purge_end = min(n, end + self.embargo)
                purge_mask[purge_start:purge_end] = True

            # Training index = all − purge zones (which already include test)
            train_idx = all_idx[~purge_mask]

            yield train_idx, test_idx
