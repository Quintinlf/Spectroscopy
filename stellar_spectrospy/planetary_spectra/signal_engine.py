"""Planetary wrapper around the unified spectral signal engine."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np

from stellar_spectrospy.unified_signal_engine import SpectralStateEstimator

DateLike = Union[str, date, datetime]


def _normalize_date(value: Optional[DateLike]) -> str:
    if value is None:
        return datetime.utcnow().date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return datetime.fromisoformat(str(value)).date().isoformat()


class PlanetarySignalEngine(SpectralStateEstimator):
    """Specialized adapter for timed planetary wavelength-flux processing."""

    def __init__(
        self,
        checkpoint_dir: Optional[Union[str, Path]] = None,
        device: str = "cpu",
    ):
        super().__init__(mode="stellar", checkpoint_dir=checkpoint_dir, device=device)

    def analyze_planetary_spectrum(
        self,
        wavelength: np.ndarray,
        flux: np.ndarray,
        target_name: str,
        observation_date: Optional[DateLike] = None,
        use_ml_denoise: bool = False,
    ) -> Dict[str, Any]:
        """Run full spectral analysis and annotate metrics with planetary metadata."""

        self.load_spectrum(wavelength, flux, name=target_name)
        metrics = self.analyse(use_ml_denoise=use_ml_denoise)
        metrics["harmonic_families"] = self.find_harmonic_families()
        metrics["target_name"] = target_name
        metrics["observation_date"] = _normalize_date(observation_date)
        metrics["mode"] = "planetary"
        return metrics
