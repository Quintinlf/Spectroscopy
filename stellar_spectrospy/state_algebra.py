"""
state_algebra.py

Quantum-inspired state-vector algebra for stellar spectra.

Mathematical framework
----------------------
A discrete spectrum  I(λ_i)  with N samples defines a vector in R^N (or C^N).
We embed it in a Hilbert space H by choosing an inner product.  Two conventions
are provided:

    1. **Discrete** (sequence space ℓ²):
           ⟨ψ|φ⟩  =  Σ_i  ψ*_i  φ_i

    2. **L²(λ)** (function space with quadrature weights):
           ⟨ψ|φ⟩  =  Σ_i  ψ*_i  φ_i  w_i
       where  w_i  are trapezoidal integration weights on the wavelength grid.

       This matters for non-uniform grids (e.g. SDSS log-λ sampling).

Normalisation
    ψ_i  =  I_i / ‖I‖_2

Density matrix
    ρ  =  |ψ⟩⟨ψ|     (pure state)
    ρ  =  Σ_k  w_k |ψ_k⟩⟨ψ_k|   (mixed / ensemble)

Basis projection
    c_k  =  ⟨φ_k|ψ⟩   where  {φ_k}  is an orthonormal basis

Operators
    O : H → H   (hermitian N×N matrix)
    ⟨O⟩_ψ  =  ⟨ψ|O|ψ⟩  =  Tr(ρ O)

    Position operator   X  =  diag(λ)           → expectation = mean wavelength
    Momentum operator   P  =  -i d/dλ  (FD)     → spectral gradient
    Effective H         H  =  T + V              → eigenmode structure

Integration with existing modules
---------------------------------
    unified_signal_engine.SpectralStateEstimator  →  SpectralState.from_estimator()
    stellar_energy_model.StellarEnergyVector      →  SpectralState (band-projected)
    tensor_analysis.EnergyTensor                  →  coefficient vectors from basis projection
    spectral_database.SpectralDatabase            →  purity / entropy as new metrics

Units
-----
    λ  :  Angstroms
    I  :  erg s⁻¹ cm⁻² Å⁻¹  (spectral flux density)  or arbitrary
    Operators carry the dimension of their diagonal entries.
"""

from __future__ import annotations

import warnings
from typing import (
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    TYPE_CHECKING,
)

import numpy as np
from numpy.linalg import eigh, svd, norm

try:
    import scipy.sparse as sp
    from scipy.sparse.linalg import eigsh as sparse_eigsh, expm_multiply
    _SPARSE_OK = True
except ImportError:
    _SPARSE_OK = False

try:
    from scipy.linalg import eigh_tridiagonal
    _TRIDIAG_OK = True
except ImportError:
    _TRIDIAG_OK = False

if TYPE_CHECKING:
    from stellar_spectrospy.unified_signal_engine import SpectralStateEstimator


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_EPS = np.finfo(np.float64).eps          # ≈ 2.2e-16
_NORM_RTOL = 1e-10                        # relative tolerance for norm checks
_SPARSE_THRESHOLD = 1024                  # use sparse ops above this dimension


# ═══════════════════════════════════════════════════════════════════════════
#  SpectralState
# ═══════════════════════════════════════════════════════════════════════════

class SpectralState:
    """
    Quantum-inspired state vector  |ψ⟩  derived from a discrete spectrum.

    Parameters
    ----------
    wavelength : (N,) array
        Wavelength grid in Angstroms.  Stored for quadrature and operator
        construction.  May be non-uniform (log-λ SDSS grids).
    intensity : (N,) array
        Raw spectral flux density (or any real-valued signal).
    label : str, optional
        Human-readable identifier (star name).
    l2_weights : bool
        If True,  the inner product uses trapezoidal quadrature weights on
        the wavelength grid (function-space L²).  If False (default), use
        the discrete sequence-space inner product.

    Attributes
    ----------
    psi : (N,) complex128 array
        Normalised state vector.
    dim : int
        Hilbert space dimension N.
    grid : (N,) float64 array
        Wavelength grid (Angstroms).
    """

    # ── construction ─────────────────────────────────────────────────────

    def __init__(
        self,
        wavelength: np.ndarray,
        intensity: np.ndarray,
        *,
        label: str = "",
        l2_weights: bool = False,
    ):
        wavelength = np.asarray(wavelength, dtype=np.float64)
        intensity = np.asarray(intensity, dtype=np.float64)

        if wavelength.ndim != 1 or intensity.ndim != 1:
            raise ValueError("wavelength and intensity must be 1-D arrays.")
        if len(wavelength) != len(intensity):
            raise ValueError(
                f"Length mismatch: wavelength({len(wavelength)}) "
                f"!= intensity({len(intensity)})"
            )
        if len(wavelength) < 2:
            raise ValueError("Need at least 2 spectral samples.")

        self.grid = wavelength
        self.dim = len(wavelength)
        self.label = label

        # Build quadrature weight vector  w_i  (trapezoidal rule)
        if l2_weights:
            self._weights = self._trapezoidal_weights(wavelength)
        else:
            self._weights = np.ones(self.dim, dtype=np.float64)
        self._sqrt_w = np.sqrt(self._weights)

        # Normalise into state vector
        self._raw_intensity = intensity.copy()
        self.psi = self._normalise(intensity)

    # ── alternative constructors ─────────────────────────────────────────

    @classmethod
    def from_estimator(
        cls,
        estimator: "SpectralStateEstimator",
        use_processed: bool = True,
        **kwargs,
    ) -> "SpectralState":
        """
        Construct a SpectralState from an already-loaded SpectralStateEstimator.

        Parameters
        ----------
        estimator : SpectralStateEstimator
            Must have been loaded with load_spectrum() (and optionally
            preprocessed / transformed).
        use_processed : bool
            If True and the estimator has a denoised signal, use that.
            Otherwise use raw flux.

        Example
        -------
        >>> est = SpectralStateEstimator(mode="stellar")
        >>> est.load_spectrum(wl, flux, name="Aldebaran")
        >>> est.preprocess(use_ml=False)
        >>> state = SpectralState.from_estimator(est)
        """
        if estimator._raw_x is None:
            raise RuntimeError("Estimator has no loaded spectrum.")

        wl = estimator._raw_x
        if use_processed and estimator._processed is not None:
            flux = np.real(estimator._processed)
        else:
            flux = np.real(estimator._raw_signal)

        label = estimator._object_name or ""
        return cls(wl, flux, label=label, **kwargs)

    @classmethod
    def from_arrays(
        cls,
        wavelength: np.ndarray,
        intensity: np.ndarray,
        **kwargs,
    ) -> "SpectralState":
        """Alias for the primary constructor — explicit factory name."""
        return cls(wavelength, intensity, **kwargs)

    @classmethod
    def zero(cls, wavelength: np.ndarray, **kwargs) -> "SpectralState":
        """
        Construct the zero vector (un-normalised).  Useful as an
        accumulator before calling mix().  Norm will be 0.
        """
        obj = cls.__new__(cls)
        wavelength = np.asarray(wavelength, dtype=np.float64)
        obj.grid = wavelength
        obj.dim = len(wavelength)
        obj.label = kwargs.get("label", "zero")
        obj._weights = np.ones(obj.dim, dtype=np.float64)
        obj._sqrt_w = np.ones(obj.dim, dtype=np.float64)
        obj._raw_intensity = np.zeros(obj.dim, dtype=np.float64)
        obj.psi = np.zeros(obj.dim, dtype=np.complex128)
        return obj

    # ── normalisation ────────────────────────────────────────────────────

    def _normalise(self, intensity: np.ndarray) -> np.ndarray:
        """
        ψ_i = I_i / ‖I‖_w

        where  ‖I‖_w² = Σ |I_i|² w_i   (weighted L² norm).

        Returns a *complex128* array (real part = normalised spectrum,
        imaginary part = 0).  Complex dtype keeps the algebra uniform
        for inner products, operators, and future extensions to complex
        amplitudes (e.g. Fourier-coefficient states).
        """
        psi = intensity.astype(np.complex128)
        nrm = self._weighted_norm(psi)

        if nrm < _EPS:
            warnings.warn(
                f"SpectralState '{self.label}': near-zero norm "
                f"({nrm:.2e}).  Returning un-normalised zero vector.",
                stacklevel=3,
            )
            return psi  # un-normalised zero vector

        psi /= nrm
        # Verify
        check = self._weighted_norm(psi)
        if abs(check - 1.0) > _NORM_RTOL:
            warnings.warn(
                f"Post-normalisation check: ‖ψ‖ = {check:.12e} (expected 1.0).",
                stacklevel=3,
            )
        return psi

    def renormalize(self) -> "SpectralState":
        """Re-normalise in-place (e.g. after arithmetic mutation)."""
        nrm = self._weighted_norm(self.psi)
        if nrm > _EPS:
            self.psi /= nrm
        return self

    def is_normalised(self, rtol: float = _NORM_RTOL) -> bool:
        return abs(self._weighted_norm(self.psi) - 1.0) < rtol

    # ── inner product machinery ──────────────────────────────────────────

    def _weighted_norm(self, v: np.ndarray) -> float:
        """‖v‖_w  =  sqrt( Σ |v_i|² w_i )"""
        return float(np.sqrt(np.sum(np.abs(v) ** 2 * self._weights)))

    def inner(self, other: "SpectralState") -> complex:
        """
        ⟨self | other⟩  =  Σ  ψ*_i  φ_i  w_i

        Both states must share the same grid dimension.
        Weights are taken from *self*.
        """
        self._check_compatible(other)
        return complex(np.sum(np.conj(self.psi) * other.psi * self._weights))

    def overlap(self, other: "SpectralState") -> float:
        """
        |⟨self|other⟩|²  — transition probability / fidelity.
        """
        return float(abs(self.inner(other)) ** 2)

    def distance(self, other: "SpectralState") -> float:
        """
        Hilbert-space distance  ‖|ψ⟩ - |φ⟩‖_w .
        """
        self._check_compatible(other)
        diff = self.psi - other.psi
        return float(np.sqrt(np.sum(np.abs(diff) ** 2 * self._weights)))

    # ── density matrix ───────────────────────────────────────────────────

    def to_density_matrix(self) -> "DensityMatrix":
        """
        Construct the pure-state density operator:

            ρ = |ψ⟩⟨ψ|

        implemented as the outer product  ψ ψ†.

        Returns a DensityMatrix wrapper with shape (N, N).
        """
        rho = np.outer(self.psi, np.conj(self.psi))
        # If using L² weights, incorporate them:  ρ_ij → √w_i  ρ_ij  √w_j
        # so that  Tr(ρ) = Σ ρ_ii w_i = 1  in the weighted inner product.
        if not np.allclose(self._weights, 1.0):
            W = np.outer(self._sqrt_w, self._sqrt_w)
            rho = rho * W
        return DensityMatrix(rho, labels=[self.label], grid=self.grid)

    # ── basis projection ─────────────────────────────────────────────────

    def project(self, basis: "SpectralBasis") -> np.ndarray:
        """
        Project |ψ⟩ onto the orthonormal basis  {|φ_k⟩}:

            c_k  =  ⟨φ_k | ψ⟩

        Parameters
        ----------
        basis : SpectralBasis
            Contains the (M, N) matrix of basis vectors.

        Returns
        -------
        coeffs : (M,) complex128 array
            Expansion coefficients.
        """
        if basis.n_dim != self.dim:
            raise ValueError(
                f"Basis dimension {basis.n_dim} != state dimension {self.dim}."
            )
        # coeffs[k] = Σ_i  φ*_ki  ψ_i  w_i
        coeffs = basis.vectors @ (self.psi * self._weights)
        return coeffs

    def reconstruct(self, coeffs: np.ndarray, basis: "SpectralBasis") -> np.ndarray:
        """
        Reconstruct the state from basis coefficients:

            |ψ_approx⟩  =  Σ_k  c_k |φ_k⟩
        """
        return coeffs @ basis.vectors   # (M,) @ (M, N) → (N,)

    def projection_fidelity(self, basis: "SpectralBasis") -> float:
        """
        Fraction of the state captured by the basis:

            F  =  Σ_k |c_k|²  /  ⟨ψ|ψ⟩

        F = 1 if the basis is complete, <1 if truncated.
        """
        c = self.project(basis)
        return float(np.sum(np.abs(c) ** 2))

    # ── operator expectations ────────────────────────────────────────────

    def expectation(self, operator: Union[np.ndarray, "SpectralOperator"]) -> complex:
        """
        ⟨ψ| O |ψ⟩  =  ψ†  O  ψ

        *operator* may be a raw (N, N) ndarray or a SpectralOperator instance.
        Supports sparse SpectralOperators for large-dimensional systems.
        """
        if isinstance(operator, SpectralOperator):
            if operator._sparse is not None:
                return complex(np.conj(self.psi) @ (operator._sparse @ self.psi))
            O = operator.matrix
        else:
            O = np.asarray(operator)
        if O.shape != (self.dim, self.dim):
            raise ValueError(f"Operator shape {O.shape} incompatible with dim={self.dim}.")
        return complex(np.conj(self.psi) @ O @ self.psi)

    def variance(self, operator: Union[np.ndarray, "SpectralOperator"]) -> float:
        """
        Var(O)_ψ  =  ⟨ψ|O²|ψ⟩ - ⟨ψ|O|ψ⟩²

        For sparse operators, avoids forming O² explicitly by computing
        O|ψ⟩ first, then ⟨Oψ|Oψ⟩.
        """
        if isinstance(operator, SpectralOperator) and operator._sparse is not None:
            O_psi = operator._sparse @ self.psi
            mean = complex(np.conj(self.psi) @ O_psi)
            mean_sq = complex(np.conj(O_psi) @ O_psi)
            return float(np.real(mean_sq - mean ** 2))
        O = operator.matrix if isinstance(operator, SpectralOperator) else np.asarray(operator)
        mean = self.expectation(O)
        mean_sq = self.expectation(O @ O)
        return float(np.real(mean_sq - mean ** 2))

    # ── statistical mechanics analogs ────────────────────────────────────

    def purity(self) -> float:
        """
        Tr(ρ²) for the pure state ρ = |ψ⟩⟨ψ|.
        Always 1.0 for a pure state (useful as sanity check, and as
        a comparison baseline for mixed-state ensembles).
        """
        return float(abs(self.inner(self)) ** 2)

    def participation_ratio(self) -> float:
        """
        Inverse participation ratio (IPR):

            IPR = 1 / Σ_i |ψ_i|⁴

        Measures the effective number of grid points over which the
        state is delocalised.  For a uniform distribution IPR = N;
        for a delta-function IPR = 1.
        """
        p = np.abs(self.psi) ** 2
        ipr_denom = np.sum(p ** 2)
        if ipr_denom < _EPS:
            return 0.0
        return float(1.0 / ipr_denom)

    def shannon_entropy(self) -> float:
        """
        Shannon entropy of the probability distribution  p_i = |ψ_i|² :

            S = - Σ_i  p_i ln(p_i)

        This is *not* the von Neumann entropy of ρ (which is 0 for pure
        states).  It quantifies the spectral complexity / spread.
        """
        p = np.abs(self.psi) ** 2
        p = p[p > _EPS]       # avoid log(0)
        return float(-np.sum(p * np.log(p)))

    # ── evolution under an operator ──────────────────────────────────────

    def evolve(
        self,
        hamiltonian: Union[np.ndarray, "SpectralOperator"],
        t: float = 1.0,
    ) -> "SpectralState":
        """
        Unitary evolution:

            |ψ(t)⟩  =  exp(-i H t)  |ψ(0)⟩

        For small systems (dim < SPARSE_THRESHOLD) uses dense eigendecomposition.
        For large systems uses scipy.sparse.linalg.expm_multiply (Krylov subspace
        method) which scales as O(N * k) instead of O(N³).

        Parameters
        ----------
        hamiltonian : (N, N) hermitian array or SpectralOperator
        t : float
            Evolution parameter (not physical time — there is no ℏ here
            unless you explicitly include it in H).

        Returns
        -------
        new SpectralState with evolved ψ (re-using the same grid).
        """
        is_sparse_op = isinstance(hamiltonian, SpectralOperator) and hamiltonian._sparse is not None
        H_mat = hamiltonian._sparse if is_sparse_op else (
            hamiltonian.matrix if isinstance(hamiltonian, SpectralOperator)
            else np.asarray(hamiltonian)
        )

        if is_sparse_op and _SPARSE_OK:
            # Krylov subspace method: expm_multiply(-i H t, psi)
            psi_new = expm_multiply(-1j * t * H_mat, self.psi)
        elif self.dim <= _SPARSE_THRESHOLD:
            H_dense = H_mat.toarray() if _SPARSE_OK and sp.issparse(H_mat) else np.asarray(H_mat)
            if H_dense.shape != (self.dim, self.dim):
                raise ValueError(f"H shape {H_dense.shape} incompatible with dim={self.dim}.")
            eigenvalues, U = eigh(H_dense)
            phase = np.exp(-1j * eigenvalues * t)
            psi_new = U @ (phase * (U.conj().T @ self.psi))
        elif _SPARSE_OK:
            if not sp.issparse(H_mat):
                H_mat = sp.csc_matrix(H_mat)
            psi_new = expm_multiply(-1j * t * H_mat, self.psi)
        else:
            raise RuntimeError(
                f"dim={self.dim} is too large for dense evolution and "
                f"scipy.sparse is not available."
            )

        new_state = SpectralState.__new__(SpectralState)
        new_state.grid = self.grid.copy()
        new_state.dim = self.dim
        new_state.label = f"{self.label}(t={t})"
        new_state._weights = self._weights.copy()
        new_state._sqrt_w = self._sqrt_w.copy()
        new_state._raw_intensity = np.real(psi_new)
        new_state.psi = psi_new
        new_state.renormalize()
        return new_state

    # ── serialisation / integration helpers ───────────────────────────────

    def to_dict(self) -> Dict:
        """Serialise core properties for storage / database insertion."""
        return {
            "label":              self.label,
            "dim":                self.dim,
            "purity":             self.purity(),
            "participation_ratio": self.participation_ratio(),
            "shannon_entropy":    self.shannon_entropy(),
            "norm_check":         float(self._weighted_norm(self.psi)),
            "wl_range":           (float(self.grid[0]), float(self.grid[-1])),
        }

    def probability_distribution(self) -> np.ndarray:
        """p_i = |ψ_i|²  — the Born-rule 'probability' distribution."""
        return np.abs(self.psi) ** 2

    # ── dunder helpers ───────────────────────────────────────────────────

    def _check_compatible(self, other: "SpectralState") -> None:
        if self.dim != other.dim:
            raise ValueError(
                f"Dimension mismatch: {self.dim} vs {other.dim}."
            )

    def __repr__(self) -> str:
        nrm = self._weighted_norm(self.psi)
        return (
            f"SpectralState('{self.label}', dim={self.dim}, "
            f"norm={nrm:.8f}, IPR={self.participation_ratio():.1f})"
        )

    def __matmul__(self, other: "SpectralState") -> complex:
        """Enable  state1 @ state2  syntax for inner product."""
        return self.inner(other)

    def __len__(self) -> int:
        return self.dim

    # ── static / private utilities ───────────────────────────────────────

    @staticmethod
    def _trapezoidal_weights(x: np.ndarray) -> np.ndarray:
        """
        Compute trapezoidal quadrature weights for a (possibly non-uniform) grid.

        w_0     = (x_1 - x_0) / 2
        w_i     = (x_{i+1} - x_{i-1}) / 2      (interior)
        w_{N-1} = (x_{N-1} - x_{N-2}) / 2
        """
        n = len(x)
        w = np.empty(n, dtype=np.float64)
        w[0] = (x[1] - x[0]) / 2.0
        w[-1] = (x[-1] - x[-2]) / 2.0
        if n > 2:
            w[1:-1] = (x[2:] - x[:-2]) / 2.0
        return np.abs(w)  # ensure positive weights


# ═══════════════════════════════════════════════════════════════════════════
#  DensityMatrix
# ═══════════════════════════════════════════════════════════════════════════

class DensityMatrix:
    """
    Density operator  ρ  for pure or mixed spectral states.

    Properties
    ----------
    ρ is a positive semi-definite Hermitian matrix with Tr(ρ) = 1.

    For a pure state  |ψ⟩:
        ρ  =  |ψ⟩⟨ψ|
        Tr(ρ²) = 1      (purity)
        S(ρ)   = 0      (von Neumann entropy)

    For a mixed ensemble  {wₖ, |ψₖ⟩}:
        ρ  =  Σ_k  wₖ |ψₖ⟩⟨ψₖ|
        Tr(ρ²) < 1
        S(ρ)   > 0

    Parameters
    ----------
    rho : (N, N) complex array
    labels : list of str, optional
    grid : (N,) array, optional
        Wavelength grid for operator construction later.
    """

    def __init__(
        self,
        rho: np.ndarray,
        labels: Optional[List[str]] = None,
        grid: Optional[np.ndarray] = None,
    ):
        rho = np.asarray(rho, dtype=np.complex128)
        if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
            raise ValueError(f"ρ must be square; got shape {rho.shape}.")
        self.rho = rho
        self.dim = rho.shape[0]
        self.labels = labels or []
        self.grid = grid

    # ── alternative constructors ─────────────────────────────────────────

    @classmethod
    def from_pure_state(cls, state: SpectralState) -> "DensityMatrix":
        """Construct ρ = |ψ⟩⟨ψ| from a SpectralState."""
        return state.to_density_matrix()

    @classmethod
    def from_ensemble(
        cls,
        states: Sequence[SpectralState],
        weights: Optional[np.ndarray] = None,
    ) -> "DensityMatrix":
        """
        Construct a mixed-state density matrix:

            ρ  =  Σ_k  w_k  |ψ_k⟩⟨ψ_k|

        Parameters
        ----------
        states : sequence of SpectralState
            All must share the same dimension.
        weights : (K,) array or None
            Convex combination weights (must sum to 1).
            If None, equal weights 1/K are used.
        """
        K = len(states)
        if K == 0:
            raise ValueError("Need at least one state.")

        dim = states[0].dim
        for s in states:
            if s.dim != dim:
                raise ValueError(
                    f"Dimension mismatch in ensemble: {s.dim} vs {dim}."
                )

        if weights is None:
            w = np.full(K, 1.0 / K)
        else:
            w = np.asarray(weights, dtype=np.float64)
            if len(w) != K:
                raise ValueError(f"weights length {len(w)} != number of states {K}.")
            if abs(w.sum() - 1.0) > 1e-8:
                warnings.warn(
                    f"Ensemble weights sum to {w.sum():.8f}, not 1.  Renormalising.",
                    stacklevel=2,
                )
                w = w / w.sum()

        rho = np.zeros((dim, dim), dtype=np.complex128)
        for wk, st in zip(w, states):
            rho += wk * np.outer(st.psi, np.conj(st.psi))

        labels = [s.label for s in states]
        grid = states[0].grid
        return cls(rho, labels=labels, grid=grid)

    @classmethod
    def maximally_mixed(cls, dim: int) -> "DensityMatrix":
        """ρ = I/N  — the maximally mixed state (maximum entropy)."""
        return cls(np.eye(dim, dtype=np.complex128) / dim)

    # ── core properties ──────────────────────────────────────────────────

    def trace(self) -> float:
        return float(np.real(np.trace(self.rho)))

    def purity(self) -> float:
        """
        Tr(ρ²).  Equals 1 for pure states, 1/N for maximally mixed.
        """
        return float(np.real(np.trace(self.rho @ self.rho)))

    def von_neumann_entropy(self) -> float:
        """
        S(ρ) = -Tr(ρ ln ρ)  computed via eigenvalues:

            S = - Σ_k  λ_k  ln(λ_k)

        where  λ_k  are the eigenvalues of ρ.
        """
        eigvals = np.linalg.eigvalsh(self.rho)
        eigvals = eigvals[eigvals > _EPS]   # discard zeros / numerical noise
        return float(-np.sum(eigvals * np.log(eigvals)))

    def fidelity(self, other: "DensityMatrix") -> float:
        """
        Fidelity  F(ρ, σ)  =  [ Tr( √(√ρ σ √ρ) ) ]²

        For two pure states this reduces to  |⟨ψ|φ⟩|².
        Uses the eigendecomposition-based formula for stability.
        """
        if self.dim != other.dim:
            raise ValueError("Dimension mismatch.")
        # sqrt(rho) via eigendecomposition
        eigvals, U = eigh(self.rho)
        eigvals = np.maximum(eigvals, 0.0)
        sqrt_rho = U @ np.diag(np.sqrt(eigvals)) @ U.conj().T
        # M = sqrt_rho @ sigma @ sqrt_rho
        M = sqrt_rho @ other.rho @ sqrt_rho
        eigM = np.linalg.eigvalsh(M)
        eigM = np.maximum(eigM, 0.0)
        return float(np.sum(np.sqrt(eigM)) ** 2)

    def eigendecompose(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Diagonalise ρ.

        Returns
        -------
        eigenvalues : (N,) sorted descending
        eigenvectors : (N, N)  columns are eigenvectors, ordered to match.
        """
        vals, vecs = eigh(self.rho)
        # Sort descending
        idx = np.argsort(vals)[::-1]
        return vals[idx], vecs[:, idx]

    def expectation(self, operator: Union[np.ndarray, "SpectralOperator"]) -> complex:
        """Tr(ρ O)"""
        O = operator.matrix if isinstance(operator, SpectralOperator) else np.asarray(operator)
        return complex(np.trace(self.rho @ O))

    # ── partial trace (bipartite) ────────────────────────────────────────

    def partial_trace(
        self,
        dims: Tuple[int, int],
        trace_out: int = 1,
    ) -> "DensityMatrix":
        """
        Partial trace for a bipartite Hilbert space  H_A ⊗ H_B.

        Parameters
        ----------
        dims : (d_A, d_B)
            Dimensions of the two subsystems.  Must satisfy d_A * d_B = N.
        trace_out : int
            0 → trace out subsystem A → return ρ_B of shape (d_B, d_B)
            1 → trace out subsystem B → return ρ_A of shape (d_A, d_A)
        """
        dA, dB = dims
        if dA * dB != self.dim:
            raise ValueError(f"d_A * d_B = {dA * dB} != dim = {self.dim}.")

        rho_reshaped = self.rho.reshape(dA, dB, dA, dB)

        if trace_out == 1:
            # Tr_B: sum over j=j' → ρ_A[i, i'] = Σ_j ρ[i,j,i',j]
            reduced = np.einsum("ijkj->ik", rho_reshaped)
        elif trace_out == 0:
            # Tr_A: sum over i=i' → ρ_B[j, j'] = Σ_i ρ[i,j,i,j']
            reduced = np.einsum("ijij'->jj'", rho_reshaped)
            # Alternative using explicit notation:
            reduced = np.trace(rho_reshaped, axis1=0, axis2=2)
        else:
            raise ValueError("trace_out must be 0 or 1.")

        return DensityMatrix(reduced)

    # ── display ──────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"DensityMatrix(dim={self.dim}, Tr={self.trace():.8f}, "
            f"purity={self.purity():.6f}, S={self.von_neumann_entropy():.6f})"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  SpectralBasis
# ═══════════════════════════════════════════════════════════════════════════

class SpectralBasis:
    """
    Orthonormal basis  {|φ_k⟩}  for projecting spectral states.

    Stores an (M, N) matrix where each row is a basis vector of dimension N.
    M ≤ N is the number of retained basis elements.

    The basis is always stored as complex128 for compatibility with
    SpectralState.project().

    Parameters
    ----------
    vectors : (M, N) array
        Rows are basis vectors.
    labels : list of str, optional
        Human-readable names for each basis element.
    kind : str
        Identifier for the construction method ("fourier", "pca", "gaussian", "custom").
    """

    def __init__(
        self,
        vectors: np.ndarray,
        labels: Optional[List[str]] = None,
        kind: str = "custom",
    ):
        vectors = np.asarray(vectors, dtype=np.complex128)
        if vectors.ndim == 1:
            vectors = vectors[np.newaxis, :]  # single vector → (1, N)
        if vectors.ndim != 2:
            raise ValueError(f"Expected 2-D matrix; got shape {vectors.shape}.")

        self.vectors = vectors
        self.n_modes = vectors.shape[0]
        self.n_dim = vectors.shape[1]
        self.labels = labels or [f"mode_{k}" for k in range(self.n_modes)]
        self.kind = kind

    # ── factory methods ──────────────────────────────────────────────────

    @classmethod
    def fourier(cls, n_dim: int, n_modes: int) -> "SpectralBasis":
        """
        Truncated discrete Fourier basis.

            φ_k(j) = (1/√N) exp(2πi k j / N)     k = 0, 1, …, M-1

        Parameters
        ----------
        n_dim : int
            Hilbert space dimension N (number of spectral samples).
        n_modes : int
            Number of Fourier modes to retain (M ≤ N).
        """
        n_modes = min(n_modes, n_dim)
        j = np.arange(n_dim)
        vectors = np.zeros((n_modes, n_dim), dtype=np.complex128)
        for k in range(n_modes):
            vectors[k] = np.exp(2j * np.pi * k * j / n_dim) / np.sqrt(n_dim)
        labels = [f"fourier_k={k}" for k in range(n_modes)]
        return cls(vectors, labels=labels, kind="fourier")

    @classmethod
    def pca(
        cls,
        spectra_matrix: np.ndarray,
        n_components: Optional[int] = None,
        explained_variance_target: float = 0.99,
    ) -> "SpectralBasis":
        """
        PCA basis from an ensemble of spectra.

        Parameters
        ----------
        spectra_matrix : (K, N) array
            K spectra, each of dimension N.  These need NOT be normalised —
            PCA operates on the covariance structure.
        n_components : int, optional
            Fixed number of principal components.  If None, retain enough
            to exceed *explained_variance_target*.
        explained_variance_target : float
            Cumulative variance fraction threshold (default 99%).
        """
        X = np.asarray(spectra_matrix, dtype=np.float64)
        if X.ndim != 2:
            raise ValueError(f"spectra_matrix must be 2-D; got shape {X.shape}.")

        # Centre the data
        mean = X.mean(axis=0)
        X_centred = X - mean

        # Economy SVD
        U, s, Vt = svd(X_centred, full_matrices=False)
        explained = s ** 2
        cumvar = np.cumsum(explained) / explained.sum()

        if n_components is None:
            n_components = int(np.searchsorted(cumvar, explained_variance_target) + 1)
            n_components = min(n_components, len(s))

        vectors = Vt[:n_components]   # (n_components, N)
        labels = [f"PC{k} ({cumvar[k]:.1%})" for k in range(n_components)]
        basis = cls(vectors, labels=labels, kind="pca")
        basis._pca_mean = mean
        basis._pca_singular_values = s[:n_components]
        basis._pca_explained_variance = cumvar[:n_components]
        return basis

    @classmethod
    def gaussian_features(
        cls,
        wavelength: np.ndarray,
        centres: Sequence[float],
        widths: Union[float, Sequence[float]] = 50.0,
        labels: Optional[List[str]] = None,
    ) -> "SpectralBasis":
        """
        Basis of Gaussian-windowed spectral features (e.g. absorption lines).

            φ_k(λ) ∝ exp( -(λ - λ_k)² / (2 σ_k²) )

        The resulting functions are orthogonalised via Gram-Schmidt
        to form a proper ONB.

        Parameters
        ----------
        wavelength : (N,) array
            The spectral grid (Angstroms).
        centres : sequence of float
            Central wavelengths for each feature (Angstroms).
        widths : float or sequence of float
            Gaussian σ for each feature (Angstroms).  Scalar → broadcast.
        labels : list of str, optional
        """
        wl = np.asarray(wavelength, dtype=np.float64)
        N = len(wl)
        M = len(centres)

        if isinstance(widths, (int, float)):
            widths = [float(widths)] * M
        widths = list(widths)
        if len(widths) != M:
            raise ValueError("Number of widths must match number of centres.")

        raw = np.zeros((M, N), dtype=np.float64)
        for k, (c, w) in enumerate(zip(centres, widths)):
            raw[k] = np.exp(-0.5 * ((wl - c) / w) ** 2)

        # Gram-Schmidt orthogonalisation
        vectors = cls._gram_schmidt(raw)

        if labels is None:
            labels = [f"gauss_{c:.0f}A" for c in centres]
        return cls(vectors, labels=labels, kind="gaussian")

    @classmethod
    def from_estimator_cwt(
        cls,
        estimator: "SpectralStateEstimator",
        n_modes: Optional[int] = None,
    ) -> "SpectralBasis":
        """
        Extract a PCA-like basis from the CWT scalogram of an estimator.

        Each CWT scale row is treated as a 'spectrum' in the wavelength
        domain.  SVD of the scalogram yields principal scale-patterns.

        Parameters
        ----------
        estimator : SpectralStateEstimator
            Must have transform_cwt() already called.
        n_modes : int, optional
            Number of modes to retain.  Default: all.
        """
        if estimator._cwt_matrix is None:
            raise RuntimeError("Call estimator.transform_cwt() before building a CWT basis.")

        mat = estimator._cwt_matrix.astype(np.float64)  # (n_scales, n_points)
        return cls.pca(mat, n_components=n_modes)

    # ── orthogonality checks ─────────────────────────────────────────────

    def is_orthonormal(self, atol: float = 1e-8) -> bool:
        """Check ⟨φ_k|φ_l⟩ ≈ δ_kl."""
        gram = self.vectors @ self.vectors.conj().T
        return bool(np.allclose(gram, np.eye(self.n_modes), atol=atol))

    def gram_matrix(self) -> np.ndarray:
        """Return the Gram matrix  G_kl = ⟨φ_k | φ_l⟩."""
        return self.vectors @ self.vectors.conj().T

    def orthogonalize(self) -> "SpectralBasis":
        """Return a new basis with Gram-Schmidt orthogonalised vectors."""
        new_vecs = self._gram_schmidt(np.real(self.vectors))
        return SpectralBasis(new_vecs, labels=self.labels, kind=self.kind)

    # ── utilities ────────────────────────────────────────────────────────

    @staticmethod
    def _gram_schmidt(raw: np.ndarray) -> np.ndarray:
        """
        Modified Gram-Schmidt orthonormalisation.

        Numerically more stable than classical GS.
        Drops linearly-dependent vectors (norm < ε after projection).
        """
        M, N = raw.shape
        Q = np.zeros((M, N), dtype=np.complex128)
        kept = 0
        for k in range(M):
            v = raw[k].astype(np.complex128)
            for j in range(kept):
                v -= np.vdot(Q[j], v) * Q[j]
            nrm = norm(v)
            if nrm < _EPS * N:
                warnings.warn(
                    f"Gram-Schmidt: vector {k} is linearly dependent; dropped.",
                    stacklevel=3,
                )
                continue
            Q[kept] = v / nrm
            kept += 1
        return Q[:kept]

    def __repr__(self) -> str:
        orth = "ONB" if self.is_orthonormal() else "non-orthogonal"
        return (
            f"SpectralBasis(kind='{self.kind}', modes={self.n_modes}, "
            f"dim={self.n_dim}, {orth})"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  SpectralOperator
# ═══════════════════════════════════════════════════════════════════════════

class SpectralOperator:
    """
    Linear operator on the spectral Hilbert space.

    Wraps an (N, N) matrix representing an observable or a Hamiltonian.
    Provides standard operator algebra: commutator, anti-commutator,
    expectation values, eigensystem.

    By convention all operators are stored as complex128 to support
    non-hermitian (e.g. annihilation / ladder) operators.

    Parameters
    ----------
    matrix : (N, N) array
    label : str
        Descriptive name for display.
    """

    def __init__(self, matrix: np.ndarray, label: str = "O"):
        matrix = np.asarray(matrix, dtype=np.complex128)
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise ValueError(f"Operator must be square; got {matrix.shape}.")
        self.matrix = matrix
        self.dim = matrix.shape[0]
        self.label = label
        self._sparse = None       # optional scipy.sparse representation
        self._tridiag = None      # optional (d, e) tuple for tridiagonal eigensolver

    # ── factory constructors ─────────────────────────────────────────────

    @classmethod
    def wavelength_operator(cls, wavelength: np.ndarray) -> "SpectralOperator":
        """
        Position operator  X  =  diag(λ).

        ⟨ψ|X|ψ⟩  gives the mean wavelength weighted by the state |ψ⟩².
        """
        wl = np.asarray(wavelength, dtype=np.float64)
        return cls(np.diag(wl.astype(np.complex128)), label="lambda")

    @classmethod
    def wavenumber_operator(cls, wavelength: np.ndarray) -> "SpectralOperator":
        """
        Wavenumber operator  K  =  diag(1/λ)   [1/Angstrom].

        Useful for frequency-domain expectations.
        """
        wl = np.asarray(wavelength, dtype=np.float64)
        k = 1.0 / np.where(wl == 0, 1e-30, wl)
        return cls(np.diag(k.astype(np.complex128)), label="wavenumber")

    @classmethod
    def energy_operator(cls, wavelength: np.ndarray) -> "SpectralOperator":
        """
        Photon energy operator  E  =  diag(hc/λ)   [Joules].

        ⟨ψ|E|ψ⟩  gives the mean photon energy weighted by the spectral state.
        """
        h = 6.626e-34     # J·s
        c = 2.998e8        # m/s
        wl_m = np.asarray(wavelength, dtype=np.float64) * 1e-10
        wl_m = np.where(wl_m == 0, 1e-30, wl_m)
        E = h * c / wl_m
        return cls(np.diag(E.astype(np.complex128)), label="E_photon")

    @classmethod
    def momentum_operator(
        cls,
        n_dim: int,
        d_lambda: float,
    ) -> "SpectralOperator":
        """
        Spectral momentum (gradient) operator using central finite differences:

            P_ij  =  -i  δ_{i,j+1} / (2 Δλ)  +  i  δ_{i,j-1} / (2 Δλ)

        This is the anti-hermitian part of the first-derivative matrix;
        multiply by -iℏ for physical momentum (if applicable).

        Parameters
        ----------
        n_dim : int
            Matrix size.
        d_lambda : float
            Grid spacing (Angstroms).
        """
        P = np.zeros((n_dim, n_dim), dtype=np.complex128)
        for i in range(1, n_dim - 1):
            P[i, i + 1] = -1j / (2 * d_lambda)
            P[i, i - 1] = 1j / (2 * d_lambda)
        # Boundary: forward / backward difference
        P[0, 1] = -1j / d_lambda
        P[-1, -2] = 1j / d_lambda
        return cls(P, label="P_lambda")

    @classmethod
    def kinetic_operator(
        cls,
        n_dim: int,
        d_lambda: float,
        mass: float = 1.0,
    ) -> "SpectralOperator":
        """
        Kinetic energy operator (second derivative):

            T  =  -(1 / 2m)  d²/dλ²

        Central finite-difference stencil:

            d²ψ/dλ²|_i  ≈  (ψ_{i-1} - 2ψ_i + ψ_{i+1}) / Δλ²

        Parameters
        ----------
        n_dim : int
        d_lambda : float
        mass : float
            Effective mass parameter (defaults to 1, making T a pure
            curvature operator).
        """
        coeff = -1.0 / (2.0 * mass * d_lambda ** 2)
        diag_main = np.full(n_dim, -2.0 * coeff, dtype=np.complex128)
        diag_off = np.full(n_dim - 1, 1.0 * coeff, dtype=np.complex128)
        T = np.diag(diag_main) + np.diag(diag_off, 1) + np.diag(diag_off, -1)
        return cls(T, label="T_kinetic")

    @classmethod
    def effective_hamiltonian(
        cls,
        wavelength: np.ndarray,
        potential: np.ndarray,
        mass: float = 1.0,
    ) -> "SpectralOperator":
        """
        Construct an effective Hamiltonian  H = T + V  on the wavelength grid.

            T  =  -(1/2m)  d²/dλ²      (kinetic / curvature)
            V  =  diag( V(λ) )          (potential = inverted spectrum)

        Physical interpretation
        -----------------------
        In stellar spectroscopy the "potential" is the inverted flux:

            V(λ)  =  -F(λ)  or  V(λ) = F_max - F(λ)

        so absorption lines appear as potential *wells*.  The eigenstates of
        H then correspond to modes that are localised in those wells —
        analogous to bound states of a quantum particle.

        The eigenvalues form a discrete "energy" spectrum whose spacing
        structure encodes the same physics as the RC score and harmonic
        families, but in a basis-independent way.

        Parameters
        ----------
        wavelength : (N,) array in Angstroms
        potential : (N,) array
            Potential energy function on the wavelength grid.
        mass : float
            Effective mass parameter (controls localisation scale).
        """
        wl = np.asarray(wavelength, dtype=np.float64)
        V = np.asarray(potential, dtype=np.float64)
        N = len(wl)
        if len(V) != N:
            raise ValueError("wavelength and potential must have the same length.")

        d_lambda = float(np.median(np.diff(wl)))  # approximate uniform spacing

        # For large systems build sparse H directly (tridiagonal T + diagonal V)
        if N >= _SPARSE_THRESHOLD and _SPARSE_OK:
            coeff = -1.0 / (2.0 * mass * d_lambda ** 2)
            diag_main = (-2.0 * coeff) * np.ones(N) + V
            diag_off = (1.0 * coeff) * np.ones(N - 1)
            H_sparse = sp.diags(
                [diag_off, diag_main.astype(np.complex128), diag_off],
                offsets=[-1, 0, 1],
                shape=(N, N),
                format="csc",
                dtype=np.complex128,
            )
            # Build a minimal dense placeholder (identity is wasteful —
            # store zeros and rely on _sparse for all computation)
            op = cls.__new__(cls)
            op.matrix = np.empty((0, 0))   # placeholder — use _sparse
            op.dim = N
            op.label = f"H_eff(m={mass:.2e})"
            op._sparse = H_sparse
            # Store tridiagonal data for O(N*k) eigensolves via eigh_tridiagonal
            op._tridiag = (diag_main.copy(), diag_off.copy())
            return op

        T = cls.kinetic_operator(N, d_lambda, mass=mass)
        H = T.matrix + np.diag(V.astype(np.complex128))
        return cls(H, label=f"H_eff(m={mass:.2e})")

    # ── operator algebra ─────────────────────────────────────────────────

    def apply(self, state: SpectralState) -> np.ndarray:
        """O|ψ⟩  →  (N,) array (NOT re-normalised)."""
        if state.dim != self.dim:
            raise ValueError(f"dim mismatch: operator {self.dim} vs state {state.dim}.")
        if self._sparse is not None:
            return self._sparse @ state.psi
        return self.matrix @ state.psi

    def expectation(self, state: SpectralState) -> complex:
        """⟨ψ|O|ψ⟩"""
        return state.expectation(self)

    def commutator(self, other: "SpectralOperator") -> "SpectralOperator":
        """[A, B] = AB - BA"""
        A = self._sparse if self._sparse is not None else self.matrix
        B = other._sparse if other._sparse is not None else other.matrix
        result = A @ B - B @ A
        if _SPARSE_OK and sp.issparse(result):
            op = SpectralOperator.__new__(SpectralOperator)
            op.matrix = np.empty((0, 0))
            op.dim = self.dim
            op.label = f"[{self.label},{other.label}]"
            op._sparse = result
            return op
        return SpectralOperator(
            np.asarray(result),
            label=f"[{self.label},{other.label}]",
        )

    def anticommutator(self, other: "SpectralOperator") -> "SpectralOperator":
        """{A, B} = AB + BA"""
        A = self._sparse if self._sparse is not None else self.matrix
        B = other._sparse if other._sparse is not None else other.matrix
        result = A @ B + B @ A
        if _SPARSE_OK and sp.issparse(result):
            op = SpectralOperator.__new__(SpectralOperator)
            op.matrix = np.empty((0, 0))
            op.dim = self.dim
            op.label = f"{{{self.label},{other.label}}}"
            op._sparse = result
            return op
        return SpectralOperator(
            np.asarray(result),
            label=f"{{{self.label},{other.label}}}",
        )

    def is_hermitian(self, atol: float = 1e-10) -> bool:
        if self._sparse is not None:
            # For sparse: check (A - A†) has small norm
            diff = self._sparse - self._sparse.conj().T
            return float(sp.linalg.norm(diff)) < atol * self.dim if _SPARSE_OK else True
        return bool(np.allclose(self.matrix, self.matrix.conj().T, atol=atol))

    def eigensystem(self, k: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Diagonalise the operator.

        Parameters
        ----------
        k : int, optional
            If given, compute only the *k* lowest eigenvalues/vectors.
            For tridiagonal operators this uses ``eigh_tridiagonal`` with
            index selection (O(N·k)).  For general sparse operators it
            falls back to ARPACK ``eigsh`` (O(N·k·iterations)).
            Defaults to full diagonalisation for small systems.

        Returns (eigenvalues, eigenvectors) sorted ascending.
        """
        # ── Fast path: tridiagonal (O(N·k) via LAPACK dstevr) ──────────
        if self._tridiag is not None and _TRIDIAG_OK:
            d, e = self._tridiag          # d: main diag (N,), e: off-diag (N-1,)
            if k is not None and k < self.dim:
                vals, vecs = eigh_tridiagonal(
                    d, e,
                    eigvals_only=False,
                    select="i",
                    select_range=(0, k - 1),
                )
            else:
                vals, vecs = eigh_tridiagonal(d, e, eigvals_only=False)
            return vals, vecs

        # ── Sparse ARPACK path ──────────────────────────────────────────
        use_sparse = (self._sparse is not None or
                      (k is not None and k < self.dim and _SPARSE_OK))

        if use_sparse and _SPARSE_OK:
            mat = self._sparse if self._sparse is not None else sp.csc_matrix(self.matrix)
            k_eff = k if k is not None else min(self.dim - 2, 50)
            # "SA" = smallest algebraic (fast for Hermitian);
            # "SM" = smallest magnitude (requires costly inversion).
            vals, vecs = sparse_eigsh(mat, k=k_eff, which="SA")
            idx = np.argsort(vals)
            return vals[idx], vecs[:, idx]

        if k is not None and k < self.dim and not _SPARSE_OK:
            warnings.warn(
                f"scipy.sparse not available; falling back to full O(N³) "
                f"eigendecomposition for dim={self.dim}.",
                stacklevel=2,
            )

        if self.is_hermitian():
            vals, vecs = eigh(self.matrix)
        else:
            vals, vecs = np.linalg.eig(self.matrix)
            idx = np.argsort(np.real(vals))
            vals, vecs = vals[idx], vecs[:, idx]
        return vals, vecs

    def matrix_exponential(self, t: float = 1.0) -> np.ndarray:
        """
        exp(-i O t)  via eigendecomposition.

        Useful for implementing time evolution U(t) = exp(-iHt).
        """
        vals, vecs = self.eigensystem()
        return vecs @ np.diag(np.exp(-1j * vals * t)) @ vecs.conj().T

    # ── arithmetic ───────────────────────────────────────────────────────

    def __add__(self, other: "SpectralOperator") -> "SpectralOperator":
        return SpectralOperator(self.matrix + other.matrix,
                                label=f"({self.label}+{other.label})")

    def __sub__(self, other: "SpectralOperator") -> "SpectralOperator":
        return SpectralOperator(self.matrix - other.matrix,
                                label=f"({self.label}-{other.label})")

    def __mul__(self, scalar: complex) -> "SpectralOperator":
        return SpectralOperator(scalar * self.matrix,
                                label=f"{scalar}*{self.label}")

    def __rmul__(self, scalar: complex) -> "SpectralOperator":
        return self.__mul__(scalar)

    def __matmul__(self, other: "SpectralOperator") -> "SpectralOperator":
        return SpectralOperator(self.matrix @ other.matrix,
                                label=f"{self.label}@{other.label}")

    def __repr__(self) -> str:
        herm = "Hermitian" if self.is_hermitian() else "non-Hermitian"
        return f"SpectralOperator('{self.label}', dim={self.dim}, {herm})"


# ═══════════════════════════════════════════════════════════════════════════
#  Convenience: pipeline integration
# ═══════════════════════════════════════════════════════════════════════════

def state_from_spectrum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    label: str = "",
    l2_weights: bool = False,
) -> SpectralState:
    """
    One-liner factory for the most common use case.

    >>> state = state_from_spectrum(wl, flux, label="Aldebaran")
    """
    return SpectralState(wavelength, flux, label=label, l2_weights=l2_weights)


def hamiltonian_from_spectrum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    mass: float = 1.0,
    invert: bool = True,
) -> SpectralOperator:
    """
    Build an effective Hamiltonian where absorption lines are potential wells.

    Parameters
    ----------
    wavelength, flux : arrays
    mass : float
        Effective mass (controls localisation length scale).
    invert : bool
        If True (default), V(λ) = max(F) - F(λ)  so absorption dips
        become wells.  If False, V(λ) = F(λ) directly.
    """
    flux = np.asarray(flux, dtype=np.float64)
    if invert:
        potential = flux.max() - flux
    else:
        potential = flux
    return SpectralOperator.effective_hamiltonian(wavelength, potential, mass=mass)


def analyse_state_properties(
    state: SpectralState,
    bases: Optional[Dict[str, SpectralBasis]] = None,
    operators: Optional[Dict[str, SpectralOperator]] = None,
) -> Dict[str, float]:
    """
    Compute a full set of quantum-inspired metrics for a spectral state.

    Returns a dictionary suitable for storage in SpectralDatabase.
    """
    metrics: Dict[str, float] = {
        "dim":                  state.dim,
        "shannon_entropy":      state.shannon_entropy(),
        "participation_ratio":  state.participation_ratio(),
        "purity":               state.purity(),
    }

    # Basis projections
    if bases:
        for name, basis in bases.items():
            fidelity = state.projection_fidelity(basis)
            metrics[f"fidelity_{name}"] = fidelity

    # Operator expectations
    if operators:
        for name, op in operators.items():
            exp_val = state.expectation(op)
            metrics[f"<{name}>"] = float(np.real(exp_val))
            metrics[f"var({name})"] = state.variance(op)

    return metrics
