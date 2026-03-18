"""Utilities for caching, normalizing, and serializing planetary spectra."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import numpy as np

DateLike = Union[str, date, datetime]


class SpectrumCache:
    """Manages raw/processed CSV cache and binary serialization of spectra.

    Standard spectral columns used across this module:
    - wavelength  : Angstrom
    - intensity   : normalized or raw flux units
    - uncertainty : optional per-point uncertainty (NaN if unknown)
    """

    def __init__(self, cache_dir: Union[str, Path]):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = self.cache_dir / "raw"
        self.processed_dir = self.cache_dir / "processed"
        self.metadata_dir = self.cache_dir / "metadata"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_date(observation_date: Optional[DateLike]) -> str:
        """Normalize date input to YYYY-MM-DD."""

        if observation_date is None:
            return datetime.utcnow().date().isoformat()
        if isinstance(observation_date, datetime):
            return observation_date.date().isoformat()
        if isinstance(observation_date, date):
            return observation_date.isoformat()
        parsed = datetime.fromisoformat(str(observation_date))
        return parsed.date().isoformat()

    def cache_path(
        self,
        target_name: str,
        observation_date: Optional[DateLike],
        source: str = "cache",
        tier: str = "raw",
    ) -> Path:
        """Build deterministic cache path using target, date, and source."""

        safe_name = target_name.strip().replace(" ", "_").replace("/", "_")
        safe_source = source.strip().replace(" ", "_").lower()
        day = self.normalize_date(observation_date)
        tier_dir = self.raw_dir if tier == "raw" else self.processed_dir
        return tier_dir / f"{safe_name}_{day}_{safe_source}.csv"

    def metadata_path(
        self,
        target_name: str,
        observation_date: Optional[DateLike],
        source: str = "cache",
        tier: str = "raw",
    ) -> Path:
        safe_name = target_name.strip().replace(" ", "_").replace("/", "_")
        safe_source = source.strip().replace(" ", "_").lower()
        day = self.normalize_date(observation_date)
        return self.metadata_dir / f"{safe_name}_{day}_{safe_source}_{tier}.json"

    def save_spectrum(
        self,
        target_name: str,
        wavelength: np.ndarray,
        intensity: np.ndarray,
        observation_date: Optional[DateLike],
        source: str = "cache",
        tier: str = "raw",
        uncertainty: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Union[str, float, int, bool]]] = None,
    ) -> Path:
        """Persist one spectrum to CSV with optional uncertainty column."""

        wl = np.asarray(wavelength, dtype=float)
        it = np.asarray(intensity, dtype=float)
        if uncertainty is None:
            unc = np.full_like(it, np.nan, dtype=float)
        else:
            unc = np.asarray(uncertainty, dtype=float)

        path = self.cache_path(target_name, observation_date, source=source, tier=tier)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["wavelength", "intensity", "uncertainty"])
            for w, i, u in zip(wl, it, unc):
                writer.writerow([float(w), float(i), float(u)])

        if metadata:
            meta_path = self.metadata_path(target_name, observation_date, source=source, tier=tier)
            with meta_path.open("w", encoding="utf-8") as handle:
                json.dump(metadata, handle, indent=2)

        return path

    def load_spectrum(
        self,
        target_name: str,
        observation_date: Optional[DateLike],
        source: str = "cache",
        tier: str = "raw",
    ) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """Load spectrum arrays (wavelength, intensity, uncertainty)."""

        path = self.cache_path(target_name, observation_date, source=source, tier=tier)
        if not path.exists():
            return None

        data = np.genfromtxt(path, delimiter=",", skip_header=1)
        if data.ndim < 2 or data.shape[1] < 2:
            return None

        wavelength = np.asarray(data[:, 0], dtype=float)
        intensity = np.asarray(data[:, 1], dtype=float)
        if data.shape[1] >= 3:
            uncertainty = np.asarray(data[:, 2], dtype=float)
        else:
            uncertainty = np.full_like(intensity, np.nan, dtype=float)

        valid = np.isfinite(wavelength) & np.isfinite(intensity)
        return wavelength[valid], intensity[valid], uncertainty[valid]

    def save_to_csv(
        self,
        target_name: str,
        wavelength: np.ndarray,
        flux: np.ndarray,
        observation_date: Optional[DateLike],
        source: str = "cache",
    ) -> Path:
        """Backward-compatible wrapper for writing raw spectrum CSV."""

        return self.save_spectrum(
            target_name=target_name,
            wavelength=wavelength,
            intensity=flux,
            uncertainty=None,
            observation_date=observation_date,
            source=source,
            tier="raw",
        )

    def load_from_csv(
        self,
        target_name: str,
        observation_date: Optional[DateLike],
        source: str = "cache",
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Backward-compatible wrapper for loading raw cached spectra."""

        loaded = self.load_spectrum(
            target_name=target_name,
            observation_date=observation_date,
            source=source,
            tier="raw",
        )
        if loaded is None:
            return None
        wavelength, intensity, _ = loaded
        return wavelength, intensity

    @staticmethod
    def normalize_spectrum(
        wavelength: np.ndarray,
        intensity: np.ndarray,
        uncertainty: Optional[np.ndarray] = None,
        target_resolution_angstrom: float = 1.0,
        normalize_intensity: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Resample spectrum to regular grid and optionally normalize intensity."""

        wl = np.asarray(wavelength, dtype=float)
        fy = np.asarray(intensity, dtype=float)
        if uncertainty is None:
            unc = np.full_like(fy, np.nan, dtype=float)
        else:
            unc = np.asarray(uncertainty, dtype=float)

        order = np.argsort(wl)
        wl = wl[order]
        fy = fy[order]
        unc = unc[order]

        if len(wl) < 2:
            return wl, fy, unc

        start = float(wl[0])
        stop = float(wl[-1])
        grid = np.arange(start, stop + target_resolution_angstrom, target_resolution_angstrom)
        interp = np.interp(grid, wl, fy)
        valid_unc = np.isfinite(unc)
        if valid_unc.sum() >= 2:
            unc_interp = np.interp(grid, wl[valid_unc], unc[valid_unc])
        else:
            unc_interp = np.full_like(interp, np.nan, dtype=float)

        # Scale with robust percentile to avoid one outlier dominating.
        if normalize_intensity:
            scale = np.percentile(np.abs(interp), 95)
            if scale > 0:
                interp = interp / scale
                if np.isfinite(unc_interp).any():
                    unc_interp = unc_interp / scale
        return grid, interp, unc_interp

    @staticmethod
    def serialize_spectrum(
        wavelength: np.ndarray,
        intensity: np.ndarray,
        uncertainty: Optional[np.ndarray] = None,
    ) -> bytes:
        """Serialize arrays into compressed NPZ bytes for SQLite BLOB storage."""

        buffer = io.BytesIO()
        if uncertainty is None:
            uncertainty = np.full_like(np.asarray(intensity, dtype=float), np.nan)
        np.savez_compressed(
            buffer,
            wavelength=np.asarray(wavelength),
            intensity=np.asarray(intensity),
            uncertainty=np.asarray(uncertainty),
        )
        return buffer.getvalue()

    @staticmethod
    def deserialize_spectrum(blob: bytes) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Deserialize NPZ bytes back to wavelength/flux arrays."""

        with np.load(io.BytesIO(blob), allow_pickle=False) as data:
            wavelength = np.asarray(data["wavelength"], dtype=float)
            if "intensity" in data:
                intensity = np.asarray(data["intensity"], dtype=float)
            else:
                intensity = np.asarray(data["flux"], dtype=float)
            if "uncertainty" in data:
                uncertainty = np.asarray(data["uncertainty"], dtype=float)
            else:
                uncertainty = np.full_like(intensity, np.nan, dtype=float)
            return wavelength, intensity, uncertainty
