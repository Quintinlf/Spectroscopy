"""Energy-mode transforms for planetary and unified spectral workflows.

This module converts fetched spectra into a simplified approximation of
top-of-atmosphere spectral irradiance at Earth.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

pd = None
try:
    import pandas as pd

    _PANDAS_OK = True
except ImportError:
    _PANDAS_OK = False

from .planetary_catalog import get_body_by_name

ENERGY_MODEL_VERSION = "toa_v1"


def _require_pandas() -> None:
    if not _PANDAS_OK:
        raise ImportError("pandas is required for compute_energy_spectrum()")


def _resolved_object_type(object_name: str) -> Optional[str]:
    body = get_body_by_name(object_name)
    if body is None:
        return None
    if body.name.strip().lower() == "sun":
        return "star"
    return body.body_type


def compute_energy_spectrum(
    df,
    object_name: str,
    observation_date: Optional[str] = None,
):
    """Compute a simplified TOA energy-mode spectrum.

    Parameters
    ----------
    df : pandas.DataFrame
        Input frame with at least wavelength/intensity/uncertainty columns.
    object_name : str
        Target object name used for object-type behavior.
    observation_date : Optional[str]
        Reserved for future temporal/ephemeris-aware energy corrections.

    Returns
    -------
    pandas.DataFrame
        DataFrame with updated intensity for TOA energy mode.
    """

    _require_pandas()
    required = {"wavelength", "intensity", "uncertainty"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"compute_energy_spectrum() missing required columns: {sorted(missing)}")

    out = df.copy()
    object_type = _resolved_object_type(object_name)
    if object_type is None and "object_type" in out.columns:
        object_type = str(out["object_type"].iloc[0]).strip().lower()

    # Stars and Sun are emission sources in this model, so they are currently
    # passed through unchanged in energy mode.
    if object_type in {"star", None}:
        out["mode"] = "energy"
        out["energy_model"] = ENERGY_MODEL_VERSION
        return out

    if object_type in {"planet", "moon", "asteroid"}:
        intensity = np.asarray(out["intensity"], dtype=float)

        # Placeholder terms for physically grounded upgrades.
        # Future upgrade points:
        # 1) solar_scaling: insert true I_sun(lambda) weighting.
        # 2) distance_scaling: apply inverse-square law from ephemeris distances.
        # 3) phase correction: apply phase-angle reflectance correction.
        # 4) emitted_component: replace with blackbody(T_object, lambda).
        # 5) atmosphere: add optional surface-level atmospheric filtering stage.
        solar_scaling = 1.0
        distance_scaling = 1.0
        epsilon = 0.10

        reflected_component = intensity * solar_scaling * distance_scaling
        emitted_component = epsilon * intensity
        total_irradiance = reflected_component + emitted_component

        # Keep energy mode numerically non-collapsing for downstream ML stages.
        total_irradiance = np.maximum(total_irradiance, 1e-12)

        out["intensity"] = total_irradiance

    out["mode"] = "energy"
    out["energy_model"] = ENERGY_MODEL_VERSION
    return out
