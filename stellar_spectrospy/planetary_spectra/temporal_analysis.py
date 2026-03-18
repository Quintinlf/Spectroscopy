"""Temporal comparison utilities for planetary spectral series."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import matplotlib.pyplot as plt
    _MATPLOTLIB_OK = True
except ImportError:
    _MATPLOTLIB_OK = False


@dataclass
class TemporalComparisonResult:
    """Result object for pairwise temporal spectral comparison."""

    spectral_difference_rms: float
    median_flux_delta: float
    detected_shift_angstrom: float
    harmonic_delta_l2: float


class TemporalSpectralAnalyzer:
    """Computes pairwise and series-level temporal spectral metrics."""

    @staticmethod
    def _require_matplotlib() -> None:
        if not _MATPLOTLIB_OK:
            raise ImportError("matplotlib is required for plotting functions")

    @staticmethod
    def _align(
        wl_a: np.ndarray,
        flux_a: np.ndarray,
        wl_b: np.ndarray,
        flux_b: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Interpolate two spectra to a shared wavelength support."""

        lo = max(float(np.min(wl_a)), float(np.min(wl_b)))
        hi = min(float(np.max(wl_a)), float(np.max(wl_b)))
        if hi <= lo:
            raise ValueError("No overlapping wavelength range between spectra")

        n = min(len(wl_a), len(wl_b))
        common = np.linspace(lo, hi, num=max(n, 64))
        a_i = np.interp(common, wl_a, flux_a)
        b_i = np.interp(common, wl_b, flux_b)
        return common, a_i, b_i

    @staticmethod
    def _harmonic_signature(flux: np.ndarray) -> np.ndarray:
        """Return normalized FFT magnitude signature for harmonic comparison."""

        centered = np.asarray(flux, dtype=float) - float(np.mean(flux))
        mag = np.abs(np.fft.rfft(centered))
        if np.max(mag) > 0:
            mag = mag / np.max(mag)
        return mag

    def spectral_difference(
        self,
        wl_a: np.ndarray,
        flux_a: np.ndarray,
        wl_b: np.ndarray,
        flux_b: np.ndarray,
    ) -> Tuple[np.ndarray, float, float]:
        """Return flux delta array with RMS and median delta summary metrics."""

        _, a_i, b_i = self._align(wl_a, flux_a, wl_b, flux_b)
        delta = b_i - a_i
        rms = float(np.sqrt(np.mean(delta**2)))
        median = float(np.median(delta))
        return delta, rms, median

    def estimate_shift_angstrom(
        self,
        wl_a: np.ndarray,
        flux_a: np.ndarray,
        wl_b: np.ndarray,
        flux_b: np.ndarray,
    ) -> float:
        """Estimate wavelength shift using cross-correlation lag."""

        common, a_i, b_i = self._align(wl_a, flux_a, wl_b, flux_b)
        a0 = a_i - np.mean(a_i)
        b0 = b_i - np.mean(b_i)
        corr = np.correlate(a0, b0, mode="full")
        lag = int(np.argmax(corr) - (len(a0) - 1))
        d_wl = float(common[1] - common[0]) if len(common) > 1 else 0.0
        return lag * d_wl

    def compare_pair(
        self,
        wl_a: np.ndarray,
        flux_a: np.ndarray,
        wl_b: np.ndarray,
        flux_b: np.ndarray,
    ) -> TemporalComparisonResult:
        """Compute primary pairwise temporal metrics."""

        _, rms, median = self.spectral_difference(wl_a, flux_a, wl_b, flux_b)
        shift = self.estimate_shift_angstrom(wl_a, flux_a, wl_b, flux_b)

        h_a = self._harmonic_signature(flux_a)
        h_b = self._harmonic_signature(flux_b)
        m = min(len(h_a), len(h_b))
        harmonic_delta = float(np.linalg.norm(h_a[:m] - h_b[:m]))

        return TemporalComparisonResult(
            spectral_difference_rms=rms,
            median_flux_delta=median,
            detected_shift_angstrom=shift,
            harmonic_delta_l2=harmonic_delta,
        )

    def compare_series(
        self,
        series: List[Tuple[str, np.ndarray, np.ndarray]],
    ) -> List[Dict[str, Union[str, float]]]:
        """Compare consecutive observations in a temporal series."""

        if len(series) < 2:
            return []

        out: List[Dict[str, Union[str, float]]] = []
        for idx in range(1, len(series)):
            day_prev, wl_prev, flux_prev = series[idx - 1]
            day_curr, wl_curr, flux_curr = series[idx]
            cmp = self.compare_pair(wl_prev, flux_prev, wl_curr, flux_curr)
            out.append(
                {
                    "date_a": day_prev,
                    "date_b": day_curr,
                    "spectral_difference_rms": cmp.spectral_difference_rms,
                    "median_flux_delta": cmp.median_flux_delta,
                    "detected_shift_angstrom": cmp.detected_shift_angstrom,
                    "harmonic_delta_l2": cmp.harmonic_delta_l2,
                }
            )
        return out

    def plot_overlay(
        self,
        wl_a: np.ndarray,
        flux_a: np.ndarray,
        wl_b: np.ndarray,
        flux_b: np.ndarray,
        label_a: str = "Spectrum A",
        label_b: str = "Spectrum B",
        ax: Optional[Any] = None,
    ) -> Any:
        """Plot overlay of two spectra for visual temporal comparison."""

        self._require_matplotlib()
        import matplotlib.pyplot as plt_local

        if ax is None:
            _, ax = plt_local.subplots(figsize=(10, 5))
        ax.plot(wl_a, flux_a, label=label_a)
        ax.plot(wl_b, flux_b, label=label_b, alpha=0.8)
        ax.set_xlabel("Wavelength (Angstrom)")
        ax.set_ylabel("Intensity")
        ax.set_title("Temporal Spectrum Overlay")
        ax.legend()
        return ax

    def plot_delta(
        self,
        wl_a: np.ndarray,
        flux_a: np.ndarray,
        wl_b: np.ndarray,
        flux_b: np.ndarray,
        ax: Optional[Any] = None,
    ) -> Any:
        """Plot per-wavelength delta with RMS annotation."""

        self._require_matplotlib()
        import matplotlib.pyplot as plt_local

        common, a_i, b_i = self._align(wl_a, flux_a, wl_b, flux_b)
        delta = b_i - a_i
        rms = float(np.sqrt(np.mean(delta**2)))

        if ax is None:
            _, ax = plt_local.subplots(figsize=(10, 4))
        ax.plot(common, delta, color="tab:red", label=f"Delta (RMS={rms:.4f})")
        ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.6)
        ax.set_xlabel("Wavelength (Angstrom)")
        ax.set_ylabel("Delta Intensity")
        ax.set_title("Temporal Delta Spectrum")
        ax.legend()
        return ax

    def plot_harmonic_delta(
        self,
        flux_a: np.ndarray,
        flux_b: np.ndarray,
        label_a: str = "A",
        label_b: str = "B",
        ax: Optional[Any] = None,
    ) -> Any:
        """Plot FFT harmonic signatures and their L2 difference."""

        self._require_matplotlib()
        import matplotlib.pyplot as plt_local

        h_a = self._harmonic_signature(flux_a)
        h_b = self._harmonic_signature(flux_b)
        m = min(len(h_a), len(h_b))
        l2 = float(np.linalg.norm(h_a[:m] - h_b[:m]))

        if ax is None:
            _, ax = plt_local.subplots(figsize=(10, 4))
        x = np.arange(m)
        ax.plot(x, h_a[:m], label=f"{label_a} harmonic")
        ax.plot(x, h_b[:m], label=f"{label_b} harmonic", alpha=0.85)
        ax.set_xlabel("Harmonic Bin")
        ax.set_ylabel("Normalized Magnitude")
        ax.set_title(f"Harmonic Signatures (L2 Delta={l2:.4f})")
        ax.legend()
        return ax
