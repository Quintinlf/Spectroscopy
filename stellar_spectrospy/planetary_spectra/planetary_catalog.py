"""Planetary catalog with core metadata for planets, moons, and asteroids."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

BodyType = Literal["star", "planet", "moon", "asteroid"]


@dataclass(frozen=True)
class OrbitalElements:
    """Simplified orbital elements used for catalog-level analytics."""

    semi_major_axis_au: float
    eccentricity: float
    inclination_deg: float
    orbital_period_days: float


@dataclass(frozen=True)
class CelestialBody:
    """Metadata record for a solar-system object."""

    name: str
    body_type: BodyType
    parent_body: Optional[str]
    average_distance_au: float
    radius_km: float
    mass_kg: float
    orbital_elements: OrbitalElements
    atmosphere: Optional[str] = None
    discovery_year: Optional[int] = None
    notes: str = ""
    aliases: List[str] = field(default_factory=list)


PLANETS: Dict[str, CelestialBody] = {
    "Sun": CelestialBody(
        name="Sun",
        body_type="star",
        parent_body="Milky Way",
        average_distance_au=0.0,
        radius_km=696340.0,
        mass_kg=1.9885e30,
        orbital_elements=OrbitalElements(0.0, 0.0, 0.0, 0.0),
        atmosphere="Photosphere/Chromosphere/Corona",
        notes="Central star of the Solar System.",
        aliases=["Sol"],
    ),
    "Mercury": CelestialBody(
        name="Mercury",
        body_type="planet",
        parent_body="Sun",
        average_distance_au=0.387,
        radius_km=2439.7,
        mass_kg=3.3011e23,
        orbital_elements=OrbitalElements(0.387, 0.2056, 7.00, 87.969),
        atmosphere="Exosphere (O, Na, H, He, K)",
    ),
    "Venus": CelestialBody(
        name="Venus",
        body_type="planet",
        parent_body="Sun",
        average_distance_au=0.723,
        radius_km=6051.8,
        mass_kg=4.8675e24,
        orbital_elements=OrbitalElements(0.723, 0.0068, 3.39, 224.701),
        atmosphere="CO2, N2",
    ),
    "Earth": CelestialBody(
        name="Earth",
        body_type="planet",
        parent_body="Sun",
        average_distance_au=1.0,
        radius_km=6371.0,
        mass_kg=5.97237e24,
        orbital_elements=OrbitalElements(1.0, 0.0167, 0.0, 365.256),
        atmosphere="N2, O2",
    ),
    "Mars": CelestialBody(
        name="Mars",
        body_type="planet",
        parent_body="Sun",
        average_distance_au=1.524,
        radius_km=3389.5,
        mass_kg=6.4171e23,
        orbital_elements=OrbitalElements(1.524, 0.0934, 1.85, 686.980),
        atmosphere="CO2, N2, Ar",
    ),
    "Jupiter": CelestialBody(
        name="Jupiter",
        body_type="planet",
        parent_body="Sun",
        average_distance_au=5.203,
        radius_km=69911.0,
        mass_kg=1.8982e27,
        orbital_elements=OrbitalElements(5.203, 0.0489, 1.30, 4332.589),
        atmosphere="H2, He",
    ),
    "Saturn": CelestialBody(
        name="Saturn",
        body_type="planet",
        parent_body="Sun",
        average_distance_au=9.537,
        radius_km=58232.0,
        mass_kg=5.6834e26,
        orbital_elements=OrbitalElements(9.537, 0.0565, 2.49, 10759.22),
        atmosphere="H2, He",
    ),
    "Uranus": CelestialBody(
        name="Uranus",
        body_type="planet",
        parent_body="Sun",
        average_distance_au=19.191,
        radius_km=25362.0,
        mass_kg=8.6810e25,
        orbital_elements=OrbitalElements(19.191, 0.0464, 0.77, 30688.5),
        atmosphere="H2, He, CH4",
    ),
    "Neptune": CelestialBody(
        name="Neptune",
        body_type="planet",
        parent_body="Sun",
        average_distance_au=30.07,
        radius_km=24622.0,
        mass_kg=1.02413e26,
        orbital_elements=OrbitalElements(30.07, 0.0095, 1.77, 60182.0),
        atmosphere="H2, He, CH4",
    ),
    "Pluto": CelestialBody(
        name="Pluto",
        body_type="planet",
        parent_body="Sun",
        average_distance_au=39.48,
        radius_km=1188.3,
        mass_kg=1.303e22,
        orbital_elements=OrbitalElements(39.48, 0.2488, 17.16, 90560.0),
        atmosphere="N2, CH4, CO (tenuous)",
        discovery_year=1930,
        notes="Dwarf planet included for extended planetary studies.",
    ),
}


MAJOR_MOONS: Dict[str, CelestialBody] = {
    "Moon": CelestialBody(
        name="Moon",
        body_type="moon",
        parent_body="Earth",
        average_distance_au=1.0,
        radius_km=1737.4,
        mass_kg=7.342e22,
        orbital_elements=OrbitalElements(1.0, 0.0549, 5.145, 27.322),
        discovery_year=None,
        notes="Earth's natural satellite.",
    ),
    "Io": CelestialBody(
        name="Io",
        body_type="moon",
        parent_body="Jupiter",
        average_distance_au=5.203,
        radius_km=1821.6,
        mass_kg=8.9319e22,
        orbital_elements=OrbitalElements(5.203, 0.0041, 0.036, 1.769),
        discovery_year=1610,
    ),
    "Europa": CelestialBody(
        name="Europa",
        body_type="moon",
        parent_body="Jupiter",
        average_distance_au=5.203,
        radius_km=1560.8,
        mass_kg=4.7998e22,
        orbital_elements=OrbitalElements(5.203, 0.009, 0.466, 3.551),
        discovery_year=1610,
    ),
    "Ganymede": CelestialBody(
        name="Ganymede",
        body_type="moon",
        parent_body="Jupiter",
        average_distance_au=5.203,
        radius_km=2634.1,
        mass_kg=1.4819e23,
        orbital_elements=OrbitalElements(5.203, 0.0013, 0.177, 7.155),
        discovery_year=1610,
    ),
    "Callisto": CelestialBody(
        name="Callisto",
        body_type="moon",
        parent_body="Jupiter",
        average_distance_au=5.203,
        radius_km=2410.3,
        mass_kg=1.0759e23,
        orbital_elements=OrbitalElements(5.203, 0.0074, 0.192, 16.689),
        discovery_year=1610,
    ),
    "Titan": CelestialBody(
        name="Titan",
        body_type="moon",
        parent_body="Saturn",
        average_distance_au=9.537,
        radius_km=2574.7,
        mass_kg=1.3452e23,
        orbital_elements=OrbitalElements(9.537, 0.0288, 0.34854, 15.945),
        atmosphere="N2, CH4",
        discovery_year=1655,
    ),
    "Enceladus": CelestialBody(
        name="Enceladus",
        body_type="moon",
        parent_body="Saturn",
        average_distance_au=9.537,
        radius_km=252.1,
        mass_kg=1.08022e20,
        orbital_elements=OrbitalElements(9.537, 0.0047, 0.009, 1.37),
        discovery_year=1789,
    ),
    "Rhea": CelestialBody(
        name="Rhea",
        body_type="moon",
        parent_body="Saturn",
        average_distance_au=9.537,
        radius_km=763.8,
        mass_kg=2.3065e21,
        orbital_elements=OrbitalElements(9.537, 0.001, 0.345, 4.518),
        discovery_year=1672,
    ),
    "Dione": CelestialBody(
        name="Dione",
        body_type="moon",
        parent_body="Saturn",
        average_distance_au=9.537,
        radius_km=561.4,
        mass_kg=1.0955e21,
        orbital_elements=OrbitalElements(9.537, 0.0022, 0.019, 2.737),
        discovery_year=1684,
    ),
    "Tethys": CelestialBody(
        name="Tethys",
        body_type="moon",
        parent_body="Saturn",
        average_distance_au=9.537,
        radius_km=531.0,
        mass_kg=6.174e20,
        orbital_elements=OrbitalElements(9.537, 0.0001, 1.091, 1.888),
        discovery_year=1684,
    ),
    "Iapetus": CelestialBody(
        name="Iapetus",
        body_type="moon",
        parent_body="Saturn",
        average_distance_au=9.537,
        radius_km=734.5,
        mass_kg=1.8056e21,
        orbital_elements=OrbitalElements(9.537, 0.0283, 15.47, 79.321),
        discovery_year=1671,
    ),
    "Phobos": CelestialBody(
        name="Phobos",
        body_type="moon",
        parent_body="Mars",
        average_distance_au=1.524,
        radius_km=11.2667,
        mass_kg=1.0659e16,
        orbital_elements=OrbitalElements(1.524, 0.0151, 1.093, 0.319),
        discovery_year=1877,
    ),
    "Deimos": CelestialBody(
        name="Deimos",
        body_type="moon",
        parent_body="Mars",
        average_distance_au=1.524,
        radius_km=6.2,
        mass_kg=1.4762e15,
        orbital_elements=OrbitalElements(1.524, 0.0002, 0.93, 1.263),
        discovery_year=1877,
    ),
    "Triton": CelestialBody(
        name="Triton",
        body_type="moon",
        parent_body="Neptune",
        average_distance_au=30.07,
        radius_km=1353.4,
        mass_kg=2.139e22,
        orbital_elements=OrbitalElements(30.07, 0.0, 156.865, 5.877),
        discovery_year=1846,
    ),
    "Charon": CelestialBody(
        name="Charon",
        body_type="moon",
        parent_body="Pluto",
        average_distance_au=39.48,
        radius_km=606.0,
        mass_kg=1.586e21,
        orbital_elements=OrbitalElements(39.48, 0.0, 0.001, 6.387),
        discovery_year=1978,
    ),
}


NOTABLE_ASTEROIDS: Dict[str, CelestialBody] = {
    "Ceres": CelestialBody(
        name="Ceres",
        body_type="asteroid",
        parent_body="Sun",
        average_distance_au=2.77,
        radius_km=469.7,
        mass_kg=9.393e20,
        orbital_elements=OrbitalElements(2.77, 0.0758, 10.59, 1680.0),
        discovery_year=1801,
        notes="Dwarf planet in asteroid belt.",
    ),
    "Pallas": CelestialBody(
        name="Pallas",
        body_type="asteroid",
        parent_body="Sun",
        average_distance_au=2.77,
        radius_km=256.0,
        mass_kg=2.14e20,
        orbital_elements=OrbitalElements(2.77, 0.231, 34.84, 1686.0),
        discovery_year=1802,
    ),
    "Juno": CelestialBody(
        name="Juno",
        body_type="asteroid",
        parent_body="Sun",
        average_distance_au=2.67,
        radius_km=123.0,
        mass_kg=2.67e19,
        orbital_elements=OrbitalElements(2.67, 0.256, 12.99, 1594.0),
        discovery_year=1804,
    ),
    "Vesta": CelestialBody(
        name="Vesta",
        body_type="asteroid",
        parent_body="Sun",
        average_distance_au=2.36,
        radius_km=262.7,
        mass_kg=2.59e20,
        orbital_elements=OrbitalElements(2.36, 0.089, 7.14, 1325.0),
        discovery_year=1807,
    ),
    "Eros": CelestialBody(
        name="Eros",
        body_type="asteroid",
        parent_body="Sun",
        average_distance_au=1.46,
        radius_km=8.4,
        mass_kg=6.69e15,
        orbital_elements=OrbitalElements(1.46, 0.222, 10.83, 643.0),
        discovery_year=1898,
    ),
}


def _normalize_name(name: str) -> str:
    return name.strip().lower().replace("_", " ")


def list_bodies(body_type: Optional[BodyType] = None) -> List[CelestialBody]:
    """Return all catalog objects, optionally filtered by body type."""

    all_bodies = {**PLANETS, **MAJOR_MOONS, **NOTABLE_ASTEROIDS}
    values = list(all_bodies.values())
    if body_type is None:
        return sorted(values, key=lambda b: (b.body_type, b.name))
    return sorted([b for b in values if b.body_type == body_type], key=lambda b: b.name)


def get_body_by_name(name: str) -> Optional[CelestialBody]:
    """Find an object by canonical name or aliases (case-insensitive)."""

    token = _normalize_name(name)
    for body in list_bodies():
        if _normalize_name(body.name) == token:
            return body
        for alias in body.aliases:
            if _normalize_name(alias) == token:
                return body
    return None
