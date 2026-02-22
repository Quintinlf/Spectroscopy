"""
stellar_energy_model.py  [PHASE 2 — STUB]

Construct stellar energy vectors from spectral flux analysis.

This module is activated in Phase 2 after spectral throughlines are
discovered in Phase 1 analysis.

Physical basis
--------------
For each star, the spectral flux density F(λ) is integrated over
standard wavelength bands:

    E_band = ∫ F(λ) dλ       [erg s⁻¹ cm⁻²]

Stellar energy vector:

    S_i = (E_UV, E_VIS, E_IR, E_total)

Normalised relative to solar flux (Vega or solar spectrum as reference).

Units: SI (J m⁻² s⁻¹) or CGS (erg s⁻¹ cm⁻²) consistently throughout.

NOTE: This file intentionally does NOT import from Phase 1 modules at
      module level — it is activated by explicit import in Phase 2 notebook.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple

# Solar bolometric flux at Earth (W m⁻²) — IAU 2015
SOLAR_FLUX_W_M2 = 1361.0


class StellarEnergyVector:
    """
    Compute, store and normalise spectral energy content of one star.

    Parameters
    ----------
    object_name : str
    wavelength   : ndarray in Angstroms
    flux         : ndarray in erg s⁻¹ cm⁻² Å⁻¹
    """

    BAND_UV  = (1000.0,  4000.0)   # Å
    BAND_VIS = (4000.0,  7000.0)
    BAND_IR  = (7000.0, 25000.0)

    def __init__(
        self,
        object_name: str,
        wavelength: np.ndarray,
        flux: np.ndarray,
    ):
        self.object_name = object_name
        self.wl   = np.asarray(wavelength, dtype=float)
        self.flux = np.asarray(flux, dtype=float)
        self._vector: Optional[np.ndarray] = None
        self._solar_norm: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    def _band_integral(self, lo: float, hi: float) -> float:
        """Trapezoidal integration over a wavelength band."""
        from scipy.integrate import simpson
        mask = (self.wl >= lo) & (self.wl <= hi)
        if mask.sum() < 2:
            return 0.0
        return float(simpson(self.flux[mask], x=self.wl[mask]))

    def compute(self) -> np.ndarray:
        """
        Returns energy vector S = [E_UV, E_VIS, E_IR, E_total].
        Values are integrated flux in erg s⁻¹ cm⁻².
        """
        e_uv   = self._band_integral(*self.BAND_UV)
        e_vis  = self._band_integral(*self.BAND_VIS)
        e_ir   = self._band_integral(*self.BAND_IR)
        e_tot  = self._band_integral(self.wl[0], self.wl[-1])
        self._vector = np.array([e_uv, e_vis, e_ir, e_tot])
        return self._vector

    def normalise(self, solar_vector: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Normalise the energy vector relative to *solar_vector* (or unit norm).

        Returns the normalised vector.
        """
        if self._vector is None:
            self.compute()
        ref = solar_vector if solar_vector is not None else np.ones(4)
        # Avoid division by zero
        ref = np.where(ref == 0, 1.0, ref)
        self._solar_norm = self._vector / ref
        return self._solar_norm

    def to_dict(self) -> Dict[str, float]:
        v = self._vector if self._vector is not None else self.compute()
        return {
            "object_name": self.object_name,
            "e_uv":    v[0],
            "e_vis":   v[1],
            "e_ir":    v[2],
            "e_total": v[3],
        }

    def __repr__(self) -> str:
        v = self._vector
        if v is None:
            return f"StellarEnergyVector('{self.object_name}', not computed)"
        return (
            f"StellarEnergyVector('{self.object_name}' "
            f"UV={v[0]:.3e}  VIS={v[1]:.3e}  IR={v[2]:.3e}  total={v[3]:.3e})"
        )


class StellarEnergyDatabase:
    """
    Collection of StellarEnergyVectors for all analysed stars.

    Phase-2 activation
    ------------------
    Populate this from the Phase-1 SpectralDatabase:

        from stellar_spectrospy.spectral_database import SpectralDatabase
        from stellar_spectrospy.stellar_energy_model import StellarEnergyDatabase

        phase1_db = SpectralDatabase()
        energy_db = StellarEnergyDatabase.from_phase1(phase1_db)
    """

    def __init__(self):
        self._records: Dict[str, StellarEnergyVector] = {}
        self._solar_ref: Optional[np.ndarray] = None

    def add(self, ev: StellarEnergyVector) -> None:
        self._records[ev.object_name] = ev

    def set_solar_reference(self, solar_ev: StellarEnergyVector) -> None:
        """Set Vega or the Sun as the normalisation reference."""
        self._solar_ref = solar_ev.compute()

    def energy_matrix(self) -> Tuple[np.ndarray, List[str]]:
        """
        Return (matrix, names) where matrix shape = (N_stars, 4).
        Rows normalised if solar reference is set.
        """
        names = list(self._records.keys())
        rows  = []
        for name in names:
            ev = self._records[name]
            ev.compute()
            row = ev.normalise(self._solar_ref)
            rows.append(row)
        return np.array(rows), names

    @classmethod
    def from_phase1(cls, phase1_db) -> "StellarEnergyDatabase":
        """
        [STUB] Reconstruct energy vectors from Phase-1 SpectralDatabase.
        To be implemented when Phase-2 analysis begins.
        """
        raise NotImplementedError(
            "StellarEnergyDatabase.from_phase1() is a Phase-2 feature. "
            "Complete Phase-1 spectral analysis first."
        )
