"""Pipeline orchestrator for timed planetary spectra workflows."""

from __future__ import annotations

import warnings
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

pd = None
try:
    import pandas as pd
    _PANDAS_OK = True
except ImportError:
    _PANDAS_OK = False

from stellar_spectrospy.spectral_database import SpectralDatabase

from .planetary_database import PlanetarySpectralDatabase
from .signal_engine import PlanetarySignalEngine
from .spectrum_cache import SpectrumCache
from .spectrum_fetcher import PlanetarySpectrumFetcher
from .temporal_analysis import TemporalSpectralAnalyzer

DateLike = Union[str, date, datetime]


class PlanetaryRunner:
    """Fetch, cache, analyze, and compare planetary spectra over time.

    Integration points:
    - Uses `unified_signal_engine.SpectralStateEstimator` through PlanetarySignalEngine.
    - Uses planetary SQLite schema and can bridge to `spectral_database.SpectralDatabase`.
    - Provides summary row format similar to `analysis_runner.ZodiacRunner`.
    """

    def __init__(
        self,
        cache_dir: Union[str, Path] = Path(__file__).parent / "spectral_cache",
        db_path: Union[str, Path] = Path(__file__).parent / "planetary_results.db",
        checkpoint_dir: Optional[Union[str, Path]] = None,
        device: str = "cpu",
    ):
        self.fetcher = PlanetarySpectrumFetcher(cache_dir=cache_dir)
        self.cache = SpectrumCache(cache_dir)
        self.db = PlanetarySpectralDatabase(db_path=db_path)
        self.signal_engine = PlanetarySignalEngine(checkpoint_dir=checkpoint_dir, device=device)
        self.temporal = TemporalSpectralAnalyzer()
        self._results: List[Dict[str, Any]] = []

    def fetch_and_store_spectrum(
        self,
        target_name: str,
        observation_date: Optional[DateLike] = None,
        mode: str = "reflectance",
        source_priority: Optional[List[str]] = None,
        local_csv_path: Optional[Union[str, Path]] = None,
        normalize: bool = True,
    ) -> Dict[str, Any]:
        """Fetch one spectrum and persist it in planetary database."""

        selected_source = "auto"
        if source_priority and len(source_priority) == 1:
            selected_source = source_priority[0]
        fetched_df = self.fetcher.fetch_spectrum(
            object_name=target_name,
            observation_date=observation_date,
            mode=mode,
            source=selected_source,
            local_csv_path=local_csv_path,
            target_resolution_angstrom=1.0,
            normalize_intensity=normalize,
        )

        wl = fetched_df["wavelength"].to_numpy(dtype=float)
        flux = fetched_df["intensity"].to_numpy(dtype=float)
        unc = fetched_df["uncertainty"].to_numpy(dtype=float)
        source_name = str(fetched_df["source"].iloc[0])
        object_type = str(fetched_df["object_type"].iloc[0])
        resolved_day = str(fetched_df["observation_date"].iloc[0])

        spectrum_id = self.db.store_spectrum(
            target_name=target_name,
            wavelength=wl,
            flux=flux,
            uncertainty=unc,
            observation_date=resolved_day,
            source=source_name,
            metadata={
                "object_type": object_type,
                "mode": str(fetched_df["mode"].iloc[0]) if "mode" in fetched_df.columns else mode,
                "energy_model": (
                    str(fetched_df["energy_model"].iloc[0])
                    if "energy_model" in fetched_df.columns
                    else "toa_v1"
                ),
                "query_timestamp": str(fetched_df["query_timestamp"].iloc[0]),
            },
            query_timestamp=datetime.utcnow().isoformat(),
        )

        return {
            "spectrum_id": spectrum_id,
            "target_name": target_name,
            "object_type": object_type,
            "observation_date": resolved_day,
            "source": source_name,
            "mode": str(fetched_df["mode"].iloc[0]) if "mode" in fetched_df.columns else mode,
            "points": len(wl),
        }

    def fetch_spectrum(
        self,
        object_name: str,
        observation_date: Optional[DateLike] = None,
        mode: str = "reflectance",
        source: str = "auto",
        local_csv_path: Optional[Union[str, Path]] = None,
    ) -> Any:
        """Public lightweight fetch API returning ML-ready DataFrame."""

        return self.fetcher.fetch_spectrum(
            object_name=object_name,
            observation_date=observation_date,
            mode=mode,
            source=source,
            local_csv_path=local_csv_path,
        )

    def analyze_spectrum(
        self,
        spectrum_id: int,
        use_ml_denoise: bool = False,
        analysis_notes: str = "",
    ) -> Dict[str, Any]:
        """Run spectral analysis for one stored spectrum and persist metrics."""

        stored = self.db.get_spectrum(spectrum_id)
        metrics = self.signal_engine.analyze_planetary_spectrum(
            wavelength=stored["wavelength"],
            flux=stored["flux"],
            target_name=stored["object_name"],
            observation_date=stored["observation_date"],
            use_ml_denoise=use_ml_denoise,
        )
        metrics_id = self.db.store_metrics(spectrum_id=spectrum_id, metrics=metrics, analysis_notes=analysis_notes)

        row = {
            "object_name": stored["object_name"],
            "object_type": stored["object_type"],
            "constellation": "SolarSystem",
            "spectral_type": f"{stored['object_type'].title()} Spectrum",
            "observation_date": stored["observation_date"],
            "n_peaks": metrics.get("n_peaks", 0),
            "coherence_score": metrics.get("coherence_score"),
            "e_uv": metrics.get("e_uv"),
            "e_vis": metrics.get("e_vis"),
            "e_ir": metrics.get("e_ir"),
            "e_total": metrics.get("e_total"),
            "n_harmonic_families": len(metrics.get("harmonic_families", [])),
            "metrics_id": metrics_id,
        }
        self._results.append(row)

        metrics["metrics_id"] = metrics_id
        metrics["spectrum_id"] = spectrum_id
        return metrics

    def fetch_analyze_store(
        self,
        target_name: str,
        observation_date: Optional[DateLike] = None,
        mode: str = "reflectance",
        source_priority: Optional[List[str]] = None,
        local_csv_path: Optional[Union[str, Path]] = None,
        use_ml_denoise: bool = False,
        analysis_notes: str = "",
    ) -> Dict[str, Any]:
        """Convenience API for single target/date processing."""

        fetched = self.fetch_and_store_spectrum(
            target_name=target_name,
            observation_date=observation_date,
            mode=mode,
            source_priority=source_priority,
            local_csv_path=local_csv_path,
            normalize=True,
        )
        metrics = self.analyze_spectrum(
            spectrum_id=fetched["spectrum_id"],
            use_ml_denoise=use_ml_denoise,
            analysis_notes=analysis_notes,
        )
        return {**fetched, **metrics}

    def compare_two_dates(
        self,
        target_name: str,
        date_a: DateLike,
        date_b: DateLike,
        mode: str = "reflectance",
        source_priority: Optional[List[str]] = None,
        use_ml_denoise: bool = False,
    ) -> Dict[str, Any]:
        """Fetch/analyze two observations and compute temporal differences."""

        first = self.fetch_and_store_spectrum(
            target_name=target_name,
            observation_date=date_a,
            mode=mode,
            source_priority=source_priority,
            normalize=True,
        )
        second = self.fetch_and_store_spectrum(
            target_name=target_name,
            observation_date=date_b,
            mode=mode,
            source_priority=source_priority,
            normalize=True,
        )

        metrics_a = self.analyze_spectrum(first["spectrum_id"], use_ml_denoise=use_ml_denoise)
        metrics_b = self.analyze_spectrum(second["spectrum_id"], use_ml_denoise=use_ml_denoise)

        spec_a = self.db.get_spectrum(first["spectrum_id"])
        spec_b = self.db.get_spectrum(second["spectrum_id"])
        cmp_result = self.temporal.compare_pair(
            wl_a=spec_a["wavelength"],
            flux_a=spec_a["flux"],
            wl_b=spec_b["wavelength"],
            flux_b=spec_b["flux"],
        )

        temporal_metrics = {
            "spectral_difference_rms": cmp_result.spectral_difference_rms,
            "detected_shift_angstrom": cmp_result.detected_shift_angstrom,
            "harmonic_delta_l2": cmp_result.harmonic_delta_l2,
            "median_flux_delta": cmp_result.median_flux_delta,
        }

        self.db.store_metrics(
            spectrum_id=second["spectrum_id"],
            metrics={**metrics_b, **temporal_metrics},
            comparison_spectrum_id=first["spectrum_id"],
            analysis_notes="Temporal pair comparison",
        )

        return {
            "target_name": target_name,
            "object_type": second.get("object_type"),
            "date_a": first["observation_date"],
            "date_b": second["observation_date"],
            "spectrum_id_a": first["spectrum_id"],
            "spectrum_id_b": second["spectrum_id"],
            "metrics_a": metrics_a,
            "metrics_b": metrics_b,
            "temporal": temporal_metrics,
        }

    def get_target_history(
        self,
        target_name: str,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> List[Dict[str, Any]]:
        """Return stored observations for a target in date order."""

        return self.db.query_spectra_by_object(target_name, start_date=start_date, end_date=end_date)

    def export_temporal_analysis(
        self,
        target_name: str,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        output_csv: Union[str, Path] = Path(__file__).parent / "planetary_temporal_results.csv",
    ) -> Path:
        """Export pairwise temporal comparisons for consecutive observations."""

        history = self.get_target_history(target_name, start_date=start_date, end_date=end_date)
        if len(history) < 2:
            warnings.warn("Need at least two observations to export temporal analysis.", stacklevel=2)
            return Path(output_csv)

        series = []
        for row in history:
            spec = self.db.get_spectrum(row["id"])
            series.append((row["observation_date"], spec["wavelength"], spec["flux"]))

        comparisons = self.temporal.compare_series(series)
        if not comparisons:
            return Path(output_csv)

        import csv

        output_path = Path(output_csv)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(comparisons[0].keys()))
            writer.writeheader()
            writer.writerows(comparisons)
        return output_path

    def summary_dataframe(self) -> Any:
        """Return runner-side summary rows similar to ZodiacRunner output."""

        if _PANDAS_OK:
            import pandas as pd_local

            return pd_local.DataFrame(self._results)
        return list(self._results)

    def to_analysis_runner_rows(self) -> List[Dict[str, Any]]:
        """Return rows in shape expected by analysis_runner/ZodiacRunner summaries."""

        out: List[Dict[str, Any]] = []
        for row in self._results:
            out.append(
                {
                    "object_name": row.get("object_name"),
                    "object_type": row.get("object_type", "planet"),
                    "constellation": row.get("constellation", "SolarSystem"),
                    "spectral_type": row.get("spectral_type"),
                    "n_peaks": row.get("n_peaks"),
                    "coherence_score": row.get("coherence_score"),
                    "e_uv": row.get("e_uv"),
                    "e_vis": row.get("e_vis"),
                    "e_ir": row.get("e_ir"),
                    "e_total": row.get("e_total"),
                    "n_harmonic_families": row.get("n_harmonic_families"),
                    "observation_date": row.get("observation_date"),
                }
            )
        return out

    def sync_latest_to_legacy_db(
        self,
        target_name: str,
        legacy_db: Optional[SpectralDatabase] = None,
    ) -> bool:
        """Compatibility bridge to spectral_database.py for mixed dashboards."""

        return self.db.sync_latest_to_spectral_database(target_name, spectral_db=legacy_db)

    def plot_temporal_comparison(
        self,
        spectrum_id_a: int,
        spectrum_id_b: int,
        show: bool = True,
    ) -> Dict[str, Any]:
        """Render overlay, delta, and harmonic comparison plots for two spectra."""

        spec_a = self.db.get_spectrum(spectrum_id_a)
        spec_b = self.db.get_spectrum(spectrum_id_b)

        ax_overlay = self.temporal.plot_overlay(
            wl_a=spec_a["wavelength"],
            flux_a=spec_a["intensity"],
            wl_b=spec_b["wavelength"],
            flux_b=spec_b["intensity"],
            label_a=f"{spec_a['object_name']} {spec_a['observation_date']}",
            label_b=f"{spec_b['object_name']} {spec_b['observation_date']}",
        )
        ax_delta = self.temporal.plot_delta(
            wl_a=spec_a["wavelength"],
            flux_a=spec_a["intensity"],
            wl_b=spec_b["wavelength"],
            flux_b=spec_b["intensity"],
        )
        ax_harm = self.temporal.plot_harmonic_delta(
            flux_a=spec_a["intensity"],
            flux_b=spec_b["intensity"],
            label_a=str(spec_a["observation_date"]),
            label_b=str(spec_b["observation_date"]),
        )

        if show and _PANDAS_OK:
            import matplotlib.pyplot as plt

            plt.show()

        return {
            "overlay_axis": ax_overlay,
            "delta_axis": ax_delta,
            "harmonic_axis": ax_harm,
        }

    def close(self) -> None:
        self.db.close()
