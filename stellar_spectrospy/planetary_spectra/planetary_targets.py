"""Planetary observation targets with temporal metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .planetary_catalog import CelestialBody, get_body_by_name


@dataclass
class PlanetaryObservation:
    """Represents a single timed observation for one target."""

    target_name: str
    observation_date: str
    source: str
    source_url: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    query_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class PlanetaryTarget:
    """Container for one catalog body and all known observations."""

    body: CelestialBody
    observations: List[PlanetaryObservation] = field(default_factory=list)


SOLAR_SYSTEM_TARGETS: Dict[str, PlanetaryTarget] = {
    body.name: PlanetaryTarget(body=body)
    for body in (
        list(get_body_by_name(name) for name in [
            "Sun",
            "Mercury",
            "Venus",
            "Earth",
            "Mars",
            "Jupiter",
            "Saturn",
            "Uranus",
            "Neptune",
            "Pluto",
            "Moon",
            "Titan",
            "Io",
            "Europa",
            "Ganymede",
            "Callisto",
            "Rhea",
            "Dione",
            "Tethys",
            "Iapetus",
            "Phobos",
            "Deimos",
            "Triton",
            "Ceres",
            "Vesta",
            "Pallas",
            "Juno",
        ])
    )
    if body is not None
}


def register_observation(
    target_name: str,
    source: str,
    observation_date: Optional[str] = None,
    source_url: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> PlanetaryObservation:
    """Create and attach a dated observation record to a planetary target."""

    body = get_body_by_name(target_name)
    if body is None:
        raise KeyError(f"Unknown planetary target: {target_name}")

    key = body.name
    if key not in SOLAR_SYSTEM_TARGETS:
        SOLAR_SYSTEM_TARGETS[key] = PlanetaryTarget(body=body)

    obs_date = observation_date or datetime.now(timezone.utc).date().isoformat()
    observation = PlanetaryObservation(
        target_name=key,
        observation_date=obs_date,
        source=source,
        source_url=source_url,
        metadata=metadata or {},
    )
    SOLAR_SYSTEM_TARGETS[key].observations.append(observation)
    return observation


def list_targets() -> List[PlanetaryTarget]:
    """Return all currently registered targets."""

    return sorted(SOLAR_SYSTEM_TARGETS.values(), key=lambda t: t.body.name)
