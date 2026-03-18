"""Planetary spectra toolkit for timed planetary spectroscopy workflows."""

from .planetary_catalog import (
    CelestialBody,
    OrbitalElements,
    PLANETS,
    MAJOR_MOONS,
    NOTABLE_ASTEROIDS,
    get_body_by_name,
    list_bodies,
)
from .planetary_targets import (
    PlanetaryObservation,
    PlanetaryTarget,
    register_observation,
    list_targets,
)
from .planetary_runner import PlanetaryRunner
from .energy_model import compute_energy_spectrum
from .spectrum_fetcher import PlanetarySpectrumFetcher, fetch_spectrum
from .temporal_analysis import TemporalSpectralAnalyzer

__all__ = [
    "CelestialBody",
    "OrbitalElements",
    "PLANETS",
    "MAJOR_MOONS",
    "NOTABLE_ASTEROIDS",
    "get_body_by_name",
    "list_bodies",
    "PlanetaryObservation",
    "PlanetaryTarget",
    "register_observation",
    "list_targets",
    "PlanetaryRunner",
    "compute_energy_spectrum",
    "PlanetarySpectrumFetcher",
    "TemporalSpectralAnalyzer",
    "fetch_spectrum",
]
