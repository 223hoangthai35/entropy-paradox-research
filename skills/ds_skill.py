"""
Data Science / ML Layer -- Financial Entropy Agent
Dual-Plane Unsupervised Regime Classification su dung Gaussian Mixture Model.
Plane 1 (Price): WPE/Complexity/MFI -> Stable/Fragile/Chaos.
Plane 2 (Volume): Shannon/SampEn -> Consensus/Dispersed/Erratic.
"""

import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler


# ==============================================================================
# REGIME LABELS
# ==============================================================================
REGIME_NAMES: dict[int, str] = {
    0: "Stable Growth",
    1: "Fragile Growth",
    2: "Chaos/Panic",
}


# ==============================================================================
# REGIME CLASSIFIER
# ==============================================================================
class RegimeClassifier:
    """
    Phan loai trang thai thi truong bang GMM unsupervised.
    Features dau vao: [WPE_Price, Complexity_Price, MFI_Price, ...].
    GMM tu dong phat hien clusters trong khong gian entropy da chieu.
    """

    def __init__(self, n_components: int = 3, random_state: int = 42) -> None:
        self.n_components = n_components
        self.scaler = StandardScaler()
        self.gmm = GaussianMixture(
            n_components=n_components,
            covariance_type="full",
            n_init=10,
            random_state=random_state,
        )
        self._cluster_to_regime: dict[int, str] = {}

    def fit(self, features: np.ndarray) -> "RegimeClassifier":
        """
        Fit GMM tren ma tran dac trung (N x F).
        Sau khi fit, tu dong map cluster -> regime name dua tren centroid MFI.
        """
        X = self.scaler.fit_transform(features)
        self.gmm.fit(X)
        self._map_clusters_to_regimes(features)
        return self

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict regime labels (0, 1, 2) cho tung dong."""
        X = self.scaler.transform(features)
        return self.gmm.predict(X)

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Soft classification: xac suat thuoc moi regime (N x n_components)."""
        X = self.scaler.transform(features)
        return self.gmm.predict_proba(X)

    def fit_predict(self, features: np.ndarray) -> np.ndarray:
        """Fit + predict trong 1 buoc. Returns regime labels."""
        self.fit(features)
        return self.predict(features)

    def get_regime_name(self, label: int) -> str:
        """Chuyen cluster index thanh ten regime."""
        return self._cluster_to_regime.get(label, f"Unknown_{label}")

    def _map_clusters_to_regimes(self, original_features: np.ndarray) -> None:
        """
        Tu dong gan nhan regime dua tren dac tinh centroid.
        Logic: sap xep cluster theo MFI centroid (cot index 2 neu co,
        hoac dung mean cua tat ca features).
        - MFI thap nhat  -> Stable Growth
        - MFI trung binh -> Fragile Growth
        - MFI cao nhat   -> Chaos/Panic
        """
        labels = self.gmm.predict(self.scaler.transform(original_features))
        centroids_original = np.array([
            original_features[labels == k].mean(axis=0)
            for k in range(self.n_components)
        ])

        # Su dung cot cuoi cung lam proxy MFI (hoac mean tat ca features)
        sort_key = centroids_original.mean(axis=1)
        sorted_indices = np.argsort(sort_key)

        regime_order = list(REGIME_NAMES.values())
        self._cluster_to_regime = {
            int(sorted_indices[i]): regime_order[min(i, len(regime_order) - 1)]
            for i in range(self.n_components)
        }


# ==============================================================================
# CONVENIENCE: FIT + PREDICT (FUNCTIONAL API) -- PRICE PLANE
# ==============================================================================
def fit_predict_regime(
    features: np.ndarray,
    n_components: int = 3,
) -> tuple[np.ndarray, RegimeClassifier]:
    """
    Ham tien ich: tao classifier, fit va predict trong 1 lenh.
    Input:  features (N x F array)
    Output: (labels, fitted_classifier)
    """
    clf = RegimeClassifier(n_components=n_components)
    labels = clf.fit_predict(features)
    return labels, clf


# ==============================================================================
# VOLUME REGIME LABELS (PLANE 2: LIQUIDITY STRUCTURE)
# ==============================================================================
VOLUME_REGIME_NAMES: dict[int, str] = {
    0: "Consensus Flow",
    1: "Dispersed Flow",
    2: "Erratic/Noisy Flow",
}


# ==============================================================================
# VOLUME REGIME CLASSIFIER
# ==============================================================================
class VolumeRegimeClassifier:
    """
    GMM Unsupervised cho Volume Entropy Plane.
    Features dau vao: [Vol_Shannon, Vol_SampEn].
    Mapping: sap xep cluster theo tong centroid (Shannon + SampEn).
    - Thap nhat  -> Consensus Flow (institutional, co cau truc)
    - Trung binh -> Dispersed Flow (phan tan vua phai)
    - Cao nhat   -> Erratic/Noisy Flow (retail erratic, bat quy luat)
    """

    def __init__(self, n_components: int = 3, random_state: int = 42) -> None:
        self.n_components = n_components
        self.scaler = StandardScaler()
        self.gmm = GaussianMixture(
            n_components=n_components,
            covariance_type="full",
            n_init=10,
            random_state=random_state,
        )
        self._cluster_to_regime: dict[int, str] = {}

    def fit(self, features: np.ndarray) -> "VolumeRegimeClassifier":
        """Fit GMM tren ma tran [Vol_Shannon, Vol_SampEn] (N x 2)."""
        X = self.scaler.fit_transform(features)
        self.gmm.fit(X)
        self._map_clusters(features)
        return self

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict volume regime labels."""
        X = self.scaler.transform(features)
        return self.gmm.predict(X)

    def fit_predict(self, features: np.ndarray) -> np.ndarray:
        """Fit + predict trong 1 buoc."""
        self.fit(features)
        return self.predict(features)

    def get_regime_name(self, label: int) -> str:
        """Chuyen cluster index thanh ten volume regime."""
        return self._cluster_to_regime.get(label, f"Unknown_{label}")

    def _map_clusters(self, original_features: np.ndarray) -> None:
        """
        Mapping dua tren tong centroid coordinates (Shannon + SampEn).
        Thap = Consensus (thanh khoan tap trung, on dinh).
        Cao  = Erratic (thanh khoan phan tan, bat quy luat).
        """
        labels = self.gmm.predict(self.scaler.transform(original_features))
        centroids = np.array([
            original_features[labels == k].mean(axis=0)
            for k in range(self.n_components)
        ])
        # Sort theo tong Shannon + SampEn
        sort_key = centroids.sum(axis=1)
        sorted_indices = np.argsort(sort_key)

        regime_order = list(VOLUME_REGIME_NAMES.values())
        self._cluster_to_regime = {
            int(sorted_indices[i]): regime_order[min(i, len(regime_order) - 1)]
            for i in range(self.n_components)
        }


# ==============================================================================
# CONVENIENCE: FIT + PREDICT (FUNCTIONAL API) -- VOLUME PLANE
# ==============================================================================
def fit_predict_volume_regime(
    features: np.ndarray,
    n_components: int = 3,
) -> tuple[np.ndarray, VolumeRegimeClassifier]:
    """
    Ham tien ich: tao VolumeRegimeClassifier, fit va predict.
    Input:  features (N x 2 array: [Vol_Shannon, Vol_SampEn])
    Output: (labels, fitted_classifier)
    """
    clf = VolumeRegimeClassifier(n_components=n_components)
    labels = clf.fit_predict(features)
    return labels, clf


# ==============================================================================
# TESTING BLOCK
# ==============================================================================
if __name__ == "__main__":
    np.random.seed(42)

    print("=" * 60)
    print("TEST 1: Price Plane -- GMM Regime Classification")
    print("=" * 60)

    # Tao 3 cum gia lap tuong ung 3 regime
    stable = np.random.randn(50, 3) * 0.3 + np.array([0.4, 0.25, 0.3])
    fragile = np.random.randn(50, 3) * 0.3 + np.array([0.7, 0.10, 0.6])
    chaos = np.random.randn(50, 3) * 0.3 + np.array([0.95, 0.03, 0.9])

    fake_features = np.vstack([stable, fragile, chaos])
    print(f"  Feature matrix shape : {fake_features.shape}")
    print(f"  Columns semantics    : [WPE, Complexity, MFI]")

    labels, clf = fit_predict_regime(fake_features, n_components=3)

    print(f"\n  Predicted labels     : {np.unique(labels)}")
    print(f"  Label distribution   :")
    for lbl in np.unique(labels):
        name = clf.get_regime_name(lbl)
        count = (labels == lbl).sum()
        print(f"    {lbl} -> {name:25s} (n={count})")

    print(f"\n  Sample predictions:")
    for idx in [0, 75, 140]:
        regime_label = labels[idx]
        regime_name = clf.get_regime_name(regime_label)
        print(f"    Index {idx:3d} -> Label={regime_label}, Regime='{regime_name}'")

    print()
    print("=" * 60)
    print("TEST 2: Volume Plane -- GMM Volume Regime Classification")
    print("=" * 60)

    # Tao 3 cum: Consensus (thap), Dispersed (trung binh), Erratic (cao)
    consensus = np.random.randn(50, 2) * 0.05 + np.array([0.65, 0.8])
    dispersed = np.random.randn(50, 2) * 0.05 + np.array([0.85, 1.2])
    erratic = np.random.randn(50, 2) * 0.05 + np.array([0.95, 2.5])

    vol_features = np.vstack([consensus, dispersed, erratic])
    print(f"  Feature matrix shape : {vol_features.shape}")
    print(f"  Columns semantics    : [Vol_Shannon, Vol_SampEn]")

    vol_labels, vol_clf = fit_predict_volume_regime(vol_features, n_components=3)

    print(f"\n  Predicted labels     : {np.unique(vol_labels)}")
    print(f"  Label distribution   :")
    for lbl in np.unique(vol_labels):
        name = vol_clf.get_regime_name(lbl)
        count = (vol_labels == lbl).sum()
        print(f"    {lbl} -> {name:25s} (n={count})")

    print(f"\n  Sample predictions:")
    for idx in [0, 75, 140]:
        vl = vol_labels[idx]
        vn = vol_clf.get_regime_name(vl)
        print(f"    Index {idx:3d} -> Label={vl}, Regime='{vn}'")
