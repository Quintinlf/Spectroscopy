# Planetary Spectra Module

This package extends the stellar spectroscopy pipeline with timed planetary spectra.

## Structure

- `planetary_catalog.py`: Catalog metadata for planets, moons, and asteroids.
- `planetary_targets.py`: Target registry and dated observation records.
- `spectrum_fetcher.py`: Source fallback fetcher (`cache -> local_csv -> nasa_pds -> hitran -> synthetic`).
- `spectrum_cache.py`: Normalization, CSV cache, and BLOB serialization.
- `signal_engine.py`: Planetary wrapper over `unified_signal_engine.SpectralStateEstimator`.
- `temporal_analysis.py`: Pair and series temporal difference metrics.
- `planetary_database.py`: SQLite schema for dated spectra and metrics.
- `planetary_runner.py`: End-to-end orchestration API.
- `notebooks/example_fetch_and_plot.ipynb`: Example workflow.

## Integration Points

1. `unified_signal_engine.py`
   - Used via `PlanetarySignalEngine` (`signal_engine.py`).
2. `analysis_runner.py`
   - Similar API shape in `PlanetaryRunner` (`fetch_analyze_store`, summary rows).
   - Unified summary support via `ZodiacRunner.summary_dataframe_unified()`.
3. `spectral_database.py`
   - Bridge method: `PlanetaryRunner.sync_latest_to_legacy_db()`.
   - Unified tables (`objects`, `object_spectra`, `object_metrics`) with `object_type`.

## Temporal Labeling

- If no `observation_date` is provided, UTC "today" is used.
- `query_timestamp` is always captured at fetch/store time.
- Date override is supported via `observation_date` argument.

## Data Sources

- Real-source-first fetch API:
   - `fetch_spectrum(object_name, observation_date=None, source="auto")`
   - `source="auto"` uses: NASA PDS -> HITRAN -> synthetic fallback.
- Configure remote endpoints with env vars:
   - `NASA_PDS_SPECTRUM_URL_TEMPLATE`
   - `HITRAN_SPECTRUM_URL_TEMPLATE`
- Optional future placeholders exist for JWST/HST (MAST wiring comments in code).

## Cache Layout

- `spectral_cache/raw/` stores fetched arrays before interpolation.
- `spectral_cache/processed/` stores ML-ready arrays on uniform wavelength grid.
- CSV schema: `wavelength,intensity,uncertainty` (`uncertainty=NaN` if unknown).

## Quick Start

```python
from stellar_spectrospy.planetary_spectra.planetary_runner import PlanetaryRunner

runner = PlanetaryRunner()
df = runner.fetch_spectrum("Mars", "2026-03-10", source="auto")
res = runner.compare_two_dates("Mars", "2026-03-01", "2026-03-10")
print(res["temporal"])
```
