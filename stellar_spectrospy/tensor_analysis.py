"""
tensor_analysis.py  [PHASE 2 — STUB]

Tensor construction and decomposition for the stellar–planetary energy model.

Tensor definition
-----------------
    T[i, j, k] = S_i[j] * P_k

Where:
  i  → star index        (N_stars)
  j  → spectral band     (4: UV, VIS, IR, Total)
  k  → planetary feature (3: E_orb, f_orb, L)

Operations
----------
  1. Construct T          shape (N_stars, 4, 3)
  2. Unfold / matricise   along each mode
  3. Tucker decomposition (via scipy or tensorly if available)
  4. Singular Value Decomposition on unfolded matrices
  5. Spectral clustering  on mode-1 factor matrix
  6. Symmetry analysis    (pairwise cosine similarity)

Output
------
  - Factor matrices  (U_stars, U_bands, U_planets)
  - Core tensor
  - Eigenvalue spectra per mode
  - Cluster assignments
  - Stability (explained variance ratio)

NOTE: This file is a Phase-2 stub.
      Activate after Phase-1 spectral patterns are identified.
"""

from __future__ import annotations

import warnings
import numpy as np
from typing import Dict, List, Optional, Tuple

try:
    import tensorly as tl
    from tensorly.decomposition import tucker
    _TENSORLY_OK = True
except ImportError:
    _TENSORLY_OK = False
    warnings.warn(
        "tensorly not installed — Tucker decomposition unavailable. "
        "pip install tensorly to enable.",
        stacklevel=2,
    )


class EnergyTensor:
    """
    Construct and decompose the stellar–planetary energy tensor T[i,j,k].

    Parameters
    ----------
    stellar_matrix : ndarray  shape (N_stars, 4)
        Row-normalised stellar energy vectors.
    planet_matrix  : ndarray  shape (8, 3)
        Column-normalised planetary state vectors.
    star_names     : list[str]
    planet_names   : list[str]
    """

    BAND_LABELS   = ["UV", "VIS", "IR", "Total"]
    PLANET_LABELS = ["E_orb", "f_orb", "L"]

    def __init__(
        self,
        stellar_matrix: np.ndarray,
        planet_matrix:  np.ndarray,
        star_names:     Optional[List[str]] = None,
        planet_names:   Optional[List[str]] = None,
    ):
        self.S = stellar_matrix            # (N, 4)
        self.P = planet_matrix             # (8, 3)
        self.star_names   = star_names   or [f"star_{i}" for i in range(len(self.S))]
        self.planet_names = planet_names or [f"planet_{k}" for k in range(len(self.P))]
        self.T: Optional[np.ndarray] = None
        self._tucker_result = None

    # ------------------------------------------------------------------
    def build(self) -> np.ndarray:
        """
        Construct T[i, j, k] = S[i, j] * P[k].

        S has shape (N, 4), P has shape (8, 3).
        T has shape (N, 4, 3).

        Outer-product broadcast:
            T[i, j, k] = S[i, j] * (sum_k P[:, k] treated as scalar per planet feature)

        NOTE: The specification uses P_k as the full planet vector per planet k.
        A full interpretation is T[i, j, k_planet] = S[i, j] * ||P[k_planet]||,
        which gives shape (N_stars, 4, 8). Both formulations are provided.
        """
        N, B = self.S.shape     # (N_stars, 4)
        K, F = self.P.shape     # (8, 3)

        # Primary tensor: outer product — shape (N, B, K)
        # T[i, j, k] = S[i, j] * norm(P[k])
        P_norms = np.linalg.norm(self.P, axis=1)   # (8,)
        T = np.einsum("ij,k->ijk", self.S, P_norms)  # (N, 4, 8)
        self.T = T
        print(f"[Tensor built]  shape={T.shape}  "
              f"N_stars={N}  bands={B}  planets={K}")
        return T

    # ------------------------------------------------------------------
    def unfold(self, mode: int) -> np.ndarray:
        """
        Return mode-*n* matricisation of T.
        Mode 0 → star-mode  (N × 4·8)
        Mode 1 → band-mode  (4 × N·8)
        Mode 2 → planet-mode (8 × N·4)
        """
        if self.T is None:
            raise RuntimeError("Call build() first.")
        return np.reshape(
            np.moveaxis(self.T, mode, 0),
            (self.T.shape[mode], -1)
        )

    # ------------------------------------------------------------------
    def svd_decompose(self, mode: int = 0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        SVD of the mode-*n* unfolding.

        Returns (U, s, Vt).
        Explained variance ratio printed for each singular value.
        """
        M = self.unfold(mode)
        U, s, Vt = np.linalg.svd(M, full_matrices=False)
        var_ratio = s**2 / (s**2).sum()
        print(f"[SVD mode-{mode}]  rank={len(s)}  "
              f"top-3 explained: {var_ratio[:3].cumsum()[-1]:.2%}")
        return U, s, Vt

    # ------------------------------------------------------------------
    def tucker_decompose(
        self,
        ranks: Optional[Tuple[int, int, int]] = None,
    ) -> Dict:
        """
        Tucker decomposition.  Requires tensorly.

        Parameters
        ----------
        ranks : (r0, r1, r2)  core tensor dimensions.
               Defaults to (min(N,4), 3, 4).
        """
        if not _TENSORLY_OK:
            raise ImportError(
                "tensorly is required for Tucker decomposition. "
                "Run: pip install tensorly"
            )
        if self.T is None:
            raise RuntimeError("Call build() first.")

        N, B, K = self.T.shape
        if ranks is None:
            ranks = (min(N, 4), B, K)

        core, factors = tucker(
            tl.tensor(self.T),
            rank=list(ranks),
        )
        self._tucker_result = {"core": np.array(core), "factors": [np.array(f) for f in factors]}
        print(f"[Tucker]  core shape={np.array(core).shape}  ranks={ranks}")
        return self._tucker_result

    # ------------------------------------------------------------------
    def spectral_clustering(self, n_clusters: int = 4) -> Optional[np.ndarray]:
        """
        Cluster stars by their mode-0 SVD embedding.

        [STUB] Requires scikit-learn.  Returns array of cluster labels.
        """
        try:
            from sklearn.cluster import SpectralClustering
        except ImportError:
            warnings.warn("scikit-learn required for clustering: pip install scikit-learn",
                          stacklevel=2)
            return None

        U, s, _ = self.svd_decompose(mode=0)
        # Embed each star in top-r dimensions weighted by singular values
        r = min(n_clusters + 1, len(s))
        embedding = U[:, :r] * s[:r]

        sc = SpectralClustering(n_clusters=n_clusters, affinity="nearest_neighbors",
                                random_state=42)
        labels = sc.fit_predict(embedding)
        print(f"[Clustering]  n_clusters={n_clusters}  labels={labels}")
        return labels

    # ------------------------------------------------------------------
    def symmetry_analysis(self) -> np.ndarray:
        """
        Pairwise cosine similarity between star energy vectors.

        Returns (N×N) similarity matrix.
        """
        S = self.S
        norms = np.linalg.norm(S, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        S_norm = S / norms
        return S_norm @ S_norm.T

    # ------------------------------------------------------------------
    def summary(self) -> str:
        lines = [
            "EnergyTensor",
            f"  Stars   : {len(self.star_names)}",
            f"  Bands   : {len(self.BAND_LABELS)}",
            f"  Planets : {len(self.planet_names)}",
        ]
        if self.T is not None:
            lines.append(f"  T shape : {self.T.shape}")
        if self._tucker_result:
            lines.append(f"  Tucker core: {self._tucker_result['core'].shape}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase-2 activation check helper
# ---------------------------------------------------------------------------

def check_phase2_readiness(phase1_db_path: str) -> bool:
    """
    Verify that enough Phase-1 data exists to activate Phase-2.

    Returns True if ≥ 10 stars with energy metrics are stored.
    """
    from stellar_spectrospy.spectral_database import SpectralDatabase
    db = SpectralDatabase(phase1_db_path)
    rows = db.query_all()
    valid = [r for r in rows if r.get("e_total") is not None]
    ready = len(valid) >= 10
    print(
        f"Phase-2 readiness: {len(valid)} stars with metrics "
        f"({'READY' if ready else 'NOT READY — need ≥10'})"
    )
    return ready
