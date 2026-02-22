"""
analysis_runner.py

Orchestrates the full zodiac-star spectral analysis pipeline.

Workflow per star
-----------------
1)  Query SDSS/SIMBAD for spectrum  (with local CSV cache)
2)  Feed spectrum to SpectralStateEstimator
3)  Run analyse() → metrics
4)  Persist results in SpectralDatabase
5)  Return summary table

Usage (notebook)
----------------
    from stellar_spectrospy.analysis_runner import ZodiacRunner

    runner = ZodiacRunner(cache_dir="spectral_cache", db_path="spectral_results.db")

    # Analyse one constellation
    df = runner.run_constellation("Taurus")

    # Analyse all 12 constellations (slow — makes real archive calls)
    runner.run_all(max_stars_per_const=3)

    # Load already-cached results
    df = runner.summary_dataframe()
"""

from __future__ import annotations

import os
import sys
import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# ---------------------------------------------------------------------------
# Repo-relative imports
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from stellar_spectrospy.zodiac_targets import (
    ZODIAC_STARS,
    StarRecord,
    get_all_stars,
    get_stars_by_constellation,
)
from stellar_spectrospy.unified_signal_engine import SpectralStateEstimator
from stellar_spectrospy.spectral_database import SpectralDatabase

# Optional dependencies
try:
    import pandas as pd
    _PANDAS_OK = True
except ImportError:
    _PANDAS_OK = False
    warnings.warn("pandas not available — summary_dataframe() will return a list of dicts.",
                  stacklevel=2)

try:
    from astropy import units as u
    from astropy.coordinates import SkyCoord
    _ASTROPY_OK = True
except ImportError:
    _ASTROPY_OK = False

try:
    from astroquery.sdss import SDSS
    from astroquery.simbad import Simbad
    _ASTROQUERY_OK = True
except ImportError:
    _ASTROQUERY_OK = False
    warnings.warn("astroquery not available — SDSS queries disabled; use cached CSV only.",
                  stacklevel=2)


# ---------------------------------------------------------------------------
# Helper: spectrum fetching
# ---------------------------------------------------------------------------

class SpectrumFetcher:
    """
    Wraps SDSS + SIMBAD queries with local CSV caching.

    Cache format
    ------------
    One CSV per star:  <cache_dir>/<object_name>.csv
    Columns: wavelength_angstrom, flux_erg_s_cm2_angstrom
    """

    def __init__(self, cache_dir: Union[str, Path] = "spectral_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def cache_path(self, name: str) -> Path:
        safe = name.replace(" ", "_").replace("/", "_")
        return self.cache_dir / f"{safe}.csv"

    def load_from_cache(self, name: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Return (wavelength, flux) arrays from cache, or None if absent."""
        p = self.cache_path(name)
        if not p.exists():
            return None
        try:
            data = np.genfromtxt(p, delimiter=",", skip_header=1)
            if data.ndim < 2 or data.shape[1] < 2:
                return None
            wl   = data[:, 0]
            flux = data[:, 1]
            valid = np.isfinite(wl) & np.isfinite(flux)
            return wl[valid], flux[valid]
        except Exception as exc:
            warnings.warn(f"Cache read failed for {name}: {exc}", stacklevel=2)
            return None

    def save_to_cache(self, name: str, wl: np.ndarray, flux: np.ndarray) -> None:
        p = self.cache_path(name)
        try:
            header = "wavelength_angstrom,flux_erg_s_cm2_angstrom"
            np.savetxt(p, np.column_stack([wl, flux]), delimiter=",",
                       header=header, comments="")
        except Exception as exc:
            warnings.warn(f"Cache write failed for {name}: {exc}", stacklevel=2)

    def fetch(
        self,
        star: StarRecord,
        radius_arcsec: float = 3.0,
        retry_delay: float = 2.0,
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Attempt to fetch a spectrum for *star*.

        Priority:
          1. Local cache
          2. SDSS spectroscopic query (via astroquery)
          3. Synthetic fallback (blackbody estimate — for testing)
        """
        # 1. Cache
        cached = self.load_from_cache(star.name)
        if cached is not None:
            print(f"  [Cache] {star.name}")
            return cached

        # 2. SDSS
        if _ASTROQUERY_OK and _ASTROPY_OK:
            result = self._query_sdss(star, radius_arcsec, retry_delay)
            if result is not None:
                self.save_to_cache(star.name, result[0], result[1])
                return result

        # 3. Synthetic blackbody fallback (educational / offline mode)
        print(f"  [Synthetic fallback] {star.name}")
        result = self._synthetic_spectrum(star)
        self.save_to_cache(star.name, result[0], result[1])
        return result

    def _query_sdss(
        self,
        star: StarRecord,
        radius_arcsec: float,
        retry_delay: float,
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Query SDSS for a spectrum within *radius_arcsec* of the star."""
        try:
            coord = SkyCoord(
                ra=star.ra_deg, dec=star.dec_deg,
                unit=(u.deg, u.deg), frame="icrs"
            )
            print(f"  [SDSS query] {star.name}  RA={star.ra_deg:.3f} Dec={star.dec_deg:.3f}")
            spec_data = SDSS.query_region(
                coord,
                radius=radius_arcsec * u.arcsec,
                spectro=True,
            )
            if spec_data is None or len(spec_data) == 0:
                print(f"  [SDSS] No spectra found for {star.name}")
                return None

            spectra = SDSS.get_spectra(matches=spec_data[0:1])
            if not spectra:
                return None

            hdu  = spectra[0][1]
            wl   = 10 ** hdu.data["loglam"]           # Angstroms
            flux = hdu.data["flux"] * 1e-17           # erg/s/cm²/Å
            valid = np.isfinite(wl) & np.isfinite(flux)
            print(f"  [SDSS] {star.name}: {valid.sum()} valid points")
            return wl[valid], flux[valid]

        except Exception as exc:
            warnings.warn(
                f"SDSS query failed for {star.name}: {exc}", stacklevel=3
            )
            time.sleep(retry_delay)
            return None

    @staticmethod
    def _synthetic_spectrum(star: StarRecord) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a simple Planck blackbody spectrum as offline fallback.

        Temperature is estimated from the spectral type code.
        """
        STYPE_TEMP = {
            "O": 40000, "B": 20000, "A": 9000,
            "F": 7000,  "G": 5800,  "K": 4500, "M": 3500,
        }
        stype_char = star.spectral_type[0].upper() if star.spectral_type else "G"
        T = STYPE_TEMP.get(stype_char, 5800)

        wl_ang = np.linspace(3500, 10000, 4096)        # Å
        wl_m   = wl_ang * 1e-10
        h, c, k = 6.626e-34, 2.998e8, 1.381e-23
        exponent = np.clip((h * c) / (wl_m * k * T), 0, 709)
        B_nu = (2 * h * c**2) / (wl_m**5 * (np.exp(exponent) - 1))
        # Scale to plausible erg/s/cm²/Å units
        B_nu_scaled = B_nu / (B_nu.max() + 1e-300) * 1e-14

        # Add a few absorption-line dips (Hα, Hβ, Ca H&K)
        for wl_line in [3933.7, 3968.5, 4861.3, 6562.8]:
            sigma = 10.0  # Å
            dip_depth = 0.15 * B_nu_scaled.max()
            B_nu_scaled -= dip_depth * np.exp(-0.5 * ((wl_ang - wl_line) / sigma) ** 2)

        B_nu_scaled = np.maximum(B_nu_scaled, 0)
        return wl_ang, B_nu_scaled


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

class ZodiacRunner:
    """
    Full pipeline orchestrator for zodiac-star spectral analysis.

    Parameters
    ----------
    cache_dir : str or Path
        Where to store cached spectra (CSV per star).
    db_path : str or Path
        SpectralDatabase file path.
    checkpoint_dir : str or Path, optional
        DenoiseNetPhysics checkpoint directory.
    device : str
        PyTorch device.
    """

    def __init__(
        self,
        cache_dir: Union[str, Path] = "spectral_cache",
        db_path: Union[str, Path] = "spectral_results.db",
        checkpoint_dir: Optional[Union[str, Path]] = None,
        device: str = "cpu",
    ):
        self.fetcher = SpectrumFetcher(cache_dir)
        self.db      = SpectralDatabase(db_path)
        self.checkpoint_dir = checkpoint_dir
        self.device  = device
        self._results: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Per-star analysis
    # ------------------------------------------------------------------

    def analyse_star(
        self,
        star: StarRecord,
        use_ml_denoise: bool = False,
        verbose: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch spectrum + run full analysis pipeline for one star.

        Returns the metrics dict, or None if spectrum unavailable.
        """
        if verbose:
            print(f"\n{'─'*60}")
            print(f"  {star.constellation} / {star.name}  [{star.spectral_type}]")

        # Fetch spectrum
        spectrum = self.fetcher.fetch(star)
        if spectrum is None:
            print(f"  SKIPPED — no spectrum available for {star.name}")
            return None

        wl, flux = spectrum

        # Build and run estimator
        estimator = SpectralStateEstimator(
            mode="stellar",
            checkpoint_dir=self.checkpoint_dir,
            device=self.device,
        )
        try:
            estimator.load_spectrum(wl, flux, name=star.name)
            metrics = estimator.analyse(use_ml_denoise=use_ml_denoise)
            estimator.find_harmonic_families()
        except Exception as exc:
            warnings.warn(f"Analysis failed for {star.name}: {exc}", stacklevel=2)
            return None

        # Persist
        self.db.store_star(star)
        self.db.store_metrics(star.name, metrics, notes=star.notes)

        # Update StarRecord in-place
        star.peak_frequencies = metrics.get("peak_frequencies", [])
        star.coherence_score  = metrics.get("coherence_score")
        star.energy_vector    = {
            "e_uv":   metrics.get("e_uv"),
            "e_vis":  metrics.get("e_vis"),
            "e_ir":   metrics.get("e_ir"),
            "e_total":metrics.get("e_total"),
        }

        row = {
            "object_name":    star.name,
            "constellation":  star.constellation,
            "spectral_type":  star.spectral_type,
            "vmag":           star.vmag,
            "n_peaks":        metrics.get("n_peaks", 0),
            "coherence_score":metrics.get("coherence_score"),
            "e_uv":           metrics.get("e_uv"),
            "e_vis":          metrics.get("e_vis"),
            "e_ir":           metrics.get("e_ir"),
            "e_total":        metrics.get("e_total"),
            "n_harmonic_families": len(metrics.get("harmonic_families", [])),
        }
        self._results.append(row)

        if verbose:
            print(estimator.summary())

        return metrics

    # ------------------------------------------------------------------
    # Constellation / batch analysis
    # ------------------------------------------------------------------

    def run_constellation(
        self,
        constellation: str,
        max_stars: Optional[int] = None,
        use_ml_denoise: bool = False,
        verbose: bool = True,
    ) -> "pd.DataFrame | List[Dict]":
        """
        Analyse all (or *max_stars*) stars in a given constellation.
        """
        stars = get_stars_by_constellation(constellation)
        if max_stars is not None:
            stars = stars[:max_stars]

        print(f"\n{'='*60}")
        print(f"  Constellation: {constellation}  ({len(stars)} stars)")
        print(f"{'='*60}")

        for star in stars:
            self.analyse_star(star, use_ml_denoise=use_ml_denoise, verbose=verbose)

        return self.summary_dataframe(constellation=constellation)

    def run_all(
        self,
        max_stars_per_const: Optional[int] = None,
        use_ml_denoise: bool = False,
        verbose: bool = True,
    ) -> "pd.DataFrame | List[Dict]":
        """
        Iterate through all 12 zodiac constellations.
        """
        for const_name in ZODIAC_STARS:
            self.run_constellation(
                const_name,
                max_stars=max_stars_per_const,
                use_ml_denoise=use_ml_denoise,
                verbose=verbose,
            )
        print(f"\n✅ Completed all constellations  ({len(self._results)} results)")
        return self.summary_dataframe()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary_dataframe(
        self,
        constellation: Optional[str] = None,
    ) -> "pd.DataFrame | List[Dict]":
        """
        Return a pandas DataFrame (or list of dicts) of all results.
        If *constellation* is given, filter to that constellation only.
        """
        if constellation:
            data = self.db.query_by_constellation(constellation)
        else:
            data = self.db.query_all()

        if _PANDAS_OK:
            import pandas as pd
            return pd.DataFrame(data)
        return data

    def export_csv(self, path: Union[str, Path] = "spectral_results.csv") -> Path:
        """Export all results to CSV."""
        return self.db.export_csv(path)

    def print_status(self) -> None:
        print(self.db.status())

    # ------------------------------------------------------------------
    # Quick single-star API for notebooks
    # ------------------------------------------------------------------

    def analyse_single(
        self,
        object_name: str,
        constellation: str = "Taurus",
        plot: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Convenience wrapper: look up a named star, run analysis, optionally plot.
        """
        from stellar_spectrospy.zodiac_targets import get_star_by_name
        try:
            star = get_star_by_name(object_name)
        except KeyError as e:
            print(e)
            return None

        metrics = self.analyse_star(star, verbose=True)
        if metrics and plot:
            spectrum = self.fetcher.load_from_cache(star.name)
            if spectrum is not None:
                est = SpectralStateEstimator(mode="stellar")
                est.load_spectrum(spectrum[0], spectrum[1], name=star.name)
                est.preprocess(use_ml=False)
                est.transform()
                est.detect_peaks()
                est.resonance_coherence()
                est._metrics = metrics
                est._peaks   = np.where(
                    np.isin(est._fft_freqs,
                            np.array(metrics.get("peak_frequencies", [])))
                )[0] or est._peaks
                try:
                    est.plot_pipeline(show=True)
                    est.plot_stellar_wavelength_spectrum(show=True)
                except Exception as exc:
                    warnings.warn(f"Plot error: {exc}", stacklevel=2)
        return metrics
