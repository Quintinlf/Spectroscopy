"""
planetary_model.py  [PHASE 2 — STUB]

Classical Hamiltonian orbital mechanics for Solar System planets.

Physical basis
--------------
For a planet of mass m in orbit around the Sun (mass M):

    Hamiltonian:  H = p² / (2m) - G M m / r

    E_orbital  = -G M m / (2a)                   (vis-viva, SI, Joules)
    f_orbital  = 1 / T  where T = 2π (a³ / GM)^0.5   (Hz)
    L          = m v_perp r  = m √(GM a (1-e²))   (kg m² s⁻¹)

Planetary state vector (per planet k):

    P_k = (E_orb, f_orb, L)

All quantities in SI units.

Data source: NASA Planetary Fact Sheet values (2024).
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# SI constants
G_SI  = 6.674e-11    # m³ kg⁻¹ s⁻²
M_SUN = 1.989e30     # kg
AU    = 1.496e11     # m  (1 Astronomical Unit)
YEAR  = 3.156e7      # s


@dataclass
class OrbitalElements:
    """Keplerian orbital elements + mass for one planet."""
    name:         str
    a_au:         float         # semi-major axis (AU)
    e:            float         # eccentricity
    mass_kg:      float         # planet mass (kg)
    # Derived — filled after compute()
    e_orbital_J:  Optional[float] = field(default=None, repr=False)
    f_orbital_hz: Optional[float] = field(default=None, repr=False)
    L_kg_m2_s:    Optional[float] = field(default=None, repr=False)
    state_vector: Optional[np.ndarray] = field(default=None, repr=False)


class PlanetaryOrbitalState:
    """
    Compute and store the dynamical state vector for a planet.

    Parameters
    ----------
    elements : OrbitalElements
    """

    def __init__(self, elements: OrbitalElements):
        self.el = elements

    def compute(self) -> np.ndarray:
        """
        Derive P_k = (E_orb, f_orb, L) in SI units.

        Returns ndarray of shape (3,).
        """
        a = self.el.a_au * AU                # m
        m = self.el.mass_kg                  # kg
        e = self.el.e

        # Orbital energy (negative = bound)
        E_orb = -(G_SI * M_SUN * m) / (2.0 * a)

        # Orbital period (Kepler's 3rd law)
        T = 2.0 * np.pi * np.sqrt(a**3 / (G_SI * M_SUN))
        f_orb = 1.0 / T

        # Angular momentum (circular approximation corrected for eccentricity)
        L = m * np.sqrt(G_SI * M_SUN * a * (1.0 - e**2))

        self.el.e_orbital_J   = E_orb
        self.el.f_orbital_hz  = f_orb
        self.el.L_kg_m2_s     = L
        self.el.state_vector  = np.array([E_orb, f_orb, L])

        return self.el.state_vector

    def to_dict(self) -> Dict:
        if self.el.state_vector is None:
            self.compute()
        return {
            "name":        self.el.name,
            "a_au":        self.el.a_au,
            "e":           self.el.e,
            "mass_kg":     self.el.mass_kg,
            "e_orbital_J": self.el.e_orbital_J,
            "f_orbital_hz":self.el.f_orbital_hz,
            "L_kg_m2_s":   self.el.L_kg_m2_s,
        }


# ---------------------------------------------------------------------------
# Solar System data  (NASA Planetary Fact Sheet, 2024)
# ---------------------------------------------------------------------------

SOLAR_SYSTEM_PLANETS: List[OrbitalElements] = [
    OrbitalElements("Mercury", a_au=0.387,  e=0.206, mass_kg=3.301e23),
    OrbitalElements("Venus",   a_au=0.723,  e=0.007, mass_kg=4.867e24),
    OrbitalElements("Earth",   a_au=1.000,  e=0.017, mass_kg=5.972e24),
    OrbitalElements("Mars",    a_au=1.524,  e=0.093, mass_kg=6.417e23),
    OrbitalElements("Jupiter", a_au=5.203,  e=0.049, mass_kg=1.898e27),
    OrbitalElements("Saturn",  a_au=9.537,  e=0.057, mass_kg=5.683e26),
    OrbitalElements("Uranus",  a_au=19.191, e=0.046, mass_kg=8.681e25),
    OrbitalElements("Neptune", a_au=30.069, e=0.010, mass_kg=1.024e26),
]


class SolarSystemModel:
    """
    Compute and return state vectors for all 8 planets.

    Returns
    -------
    state_matrix : ndarray  shape=(8, 3)
        Rows = planets, cols = [E_orb, f_orb, L]
    planet_names : list[str]
    """

    def __init__(self):
        self._states: Dict[str, PlanetaryOrbitalState] = {}
        for el in SOLAR_SYSTEM_PLANETS:
            self._states[el.name] = PlanetaryOrbitalState(el)

    def compute_all(self) -> Tuple[np.ndarray, List[str]]:
        """Compute state vectors for all planets. Returns (matrix, names)."""
        names   = []
        vectors = []
        for name, pos in self._states.items():
            v = pos.compute()
            names.append(name)
            vectors.append(v)
        return np.array(vectors), names

    def normalised_matrix(self) -> Tuple[np.ndarray, List[str]]:
        """
        Return state matrix column-normalised to [0, 1] for tensor construction.
        """
        matrix, names = self.compute_all()
        col_max = np.abs(matrix).max(axis=0)
        col_max = np.where(col_max == 0, 1.0, col_max)
        return matrix / col_max, names

    def summary(self) -> str:
        matrix, names = self.compute_all()
        lines = [
            f"{'Planet':<10} {'E_orb (J)':>16} {'f_orb (Hz)':>16} {'L (kg m²/s)':>16}",
            "─" * 62,
        ]
        for name, row in zip(names, matrix):
            lines.append(
                f"{name:<10} {row[0]:>16.4e} {row[1]:>16.4e} {row[2]:>16.4e}"
            )
        return "\n".join(lines)


if __name__ == "__main__":
    sm = SolarSystemModel()
    print(sm.summary())
