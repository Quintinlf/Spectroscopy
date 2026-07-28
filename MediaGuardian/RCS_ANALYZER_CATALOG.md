# Reusable signal-processing tooling for an RCS Transmission Analyzer

Scope: catalog only — no new code written. This session has no adb/phone access, so capturing `adb logcat` output or running `ffprobe` on the failed video has to happen on your machine; this file is about what's already in the repo that a future analyzer could build on.

## 1. Genuinely reusable (domain-agnostic algorithm/pattern)

| File | Purpose | Inputs | Outputs | Applicable to packet timing / throughput / retries / latency? |
|---|---|---|---|---|
| `nuclear_magnetic_resonance_spectrospy/nmr_function.py:232` `compute_fft_spectrum()` | FFT of a 1-D time series with optional windowing (hamming/hann/exponential) and zero-fill | 2-column array (time, value), window name, zero-fill length | dict: signed + positive frequencies, magnitude | Yes — feed it a resampled "bytes-acked per tick" or "retry-interval" series to look for periodicity in stalls |
| `stellar_spectrospy/planetary_spectra/temporal_analysis.py` `TemporalSpectralAnalyzer` | Compare two 1-D signals sampled on different x-grids: interpolates to shared support, RMS/median delta, cross-correlation lag (shift), FFT-harmonic L2 distance. `compare_series()` walks consecutive pairs in a list | two or more `(label, x, y)` series | `TemporalComparisonResult` (rms, median delta, shift, harmonic delta) or list of dicts for a series | Yes — closest existing fit for "how different was this send attempt from the last N attempts" |
| `stellar_spectrospy/unified_signal_engine.py` `SpectralStateEstimator` | Pipeline shape: smooth (`scipy.signal.savgol_filter`) → FFT → peak detection (`find_peaks`) → composite score | 1-D signal array | smoothed signal, detected peaks, coherence/score metrics | Pipeline shape transfers (smooth → transform → detect events → score); the physics framing does not |
| `stellar_spectrospy/planetary_spectra/spectrum_cache.py` `SpectrumCache` | Cache-by-name+date utility: deterministic path building, CSV + compressed-NPZ serialization, raw/processed/metadata tiers | any 2-3 column numeric series + a name/date key | cached `.csv`/`.npz` files, round-trip load | Yes, unmodified — the column names (`wavelength/intensity/uncertainty`) are just labels; works for `time/throughput/retry_count` as-is |
| `audio_visuals/audio_enhancement_pipeline.ipynb` (see its README) | Full 1-D signal diagnostics pipeline: waveform/FFT/spectrogram plots, band-energy breakdown, high-pass filter, spectral-subtraction denoise with overlap-add, and a metrics/validation harness | WAV-shaped 1-D signal at a fixed sample rate | before/after plots, `enhancement_metrics.csv` (SNR-proxy, RMS delta, clip ratio, non-finite check), `band_energy_summary.csv`, `validation_sweeps.csv` (robustness across segmentations) | Shape matches "ingest a signal → diagnostics + quality metrics + before/after" closely, but requires resampling a transmission timeline into a synthetic fixed-rate "waveform" first — it won't run on raw log lines directly |
| `machine_learning/neural_net.py:253-274` `_complex_fft()` / `_rfft_mag()` | Generic FFT + magnitude-spectrum helpers (PyTorch) | `(B,2,L)` real/imag tensor | complex spectrum / magnitude spectrum | Yes, as standalone utility functions — independent of the trained model below |
| `stellar_spectrospy/planetary_spectra/planetary_runner.py` `PlanetaryRunner` | **Orchestration pattern**: fetch → cache → store → analyze → compare-over-time → export CSV → summarize, wiring together `SpectrumCache`, `SpectralStateEstimator`, `TemporalSpectralAnalyzer`, and a SQLite results DB | target name + date range | stored spectra/metrics in SQLite, `compare_two_dates()`, `export_temporal_analysis()` CSV, `summary_dataframe()` | **This is the template to copy for the analyzer's top-level `Runner` class** — same shape works with "ingest attempt" instead of "fetch spectrum" |

## 2. Present but not meaningfully reusable without a full rewrite

| File | Why it doesn't transfer |
|---|---|
| `stellar_spectrospy/tensor_analysis.py` `EnergyTensor` | Tucker/SVD decomposition of a hand-built star × spectral-band × planet-feature tensor. There's no natural 3-axis structure in RCS diagnostics data — the outer-product-tensor code could apply to *any* 3-factor tensor in principle, but would need a genuinely new tensor design, not adaptation |
| `machine_learning/neural_net.py` `DenoiseNetPhysics` (trained model + 43 checkpoints) | Trained exclusively on `synth_batch_phys()` synthetic NMR-FID exponential-decay signals. The architecture could be retrained on network-timing data, but the existing checkpoints are useless for this — reuse means retraining from scratch |
| `nuclear_magnetic_resonance_spectrospy/peak_assignment.py` `ChemicalShiftDatabase` / `PeakAssignmentAnalyzer` | Matches detected peaks against a hardcoded chemical-shift lookup table. The *pattern* (match features against known signatures) is conceptually similar to matching failure timing signatures to known causes, but none of the lookup data or matching logic itself transfers |
| `stellar_spectrospy/state_algebra.py`, `planetary_model.py`, `zodiac_targets.py`, `planetary_spectra/planetary_catalog.py` | Quantum-state / orbital-mechanics / star-catalog domain models — no transferable generic logic |
| `solar_project/solar_spec.ipynb` | External API polling (NREL/EcoFlow) with timestamped CSV output. Only the general "poll on an interval, log timestamped samples" pattern is reusable, not the solar-specific content |

## 3. Suggested architecture for an "RCS Transmission Analyzer"

Modeled directly on `PlanetaryRunner` (§1, last row), swapping "spectrum" for "transmission attempt":

```
Capture (on your machine, out of scope here)
  adb logcat  ->  rcs_log.txt
  ffprobe     ->  video metadata (codec, bitrate, resolution, size)
        |
        v
Ingest / normalize  ->  parse log lines into a (timestamp, event, value) series
        |
        v
Cache            ->  SpectrumCache-style: store raw + processed series per attempt, keyed by attempt timestamp
        |
        v
Per-attempt analysis  ->  SpectralStateEstimator-shaped: smooth -> FFT (compute_fft_spectrum) -> detect retry/stall events -> score
        |
        v
Cross-attempt comparison  ->  TemporalSpectralAnalyzer.compare_series() across recent attempts:
                              RMS/median delta in timing, cross-correlation shift, harmonic delta
        |
        v
Report  ->  CSV export + summary (PlanetaryRunner.export_temporal_analysis / summary_dataframe pattern)
```

This is a design sketch only — nothing above has been implemented. If you want it built, the natural first step is capturing one real `rcs_log.txt` (via the adb steps) and the video's `ffprobe` output so the ingest/parsing step can be designed against real log line shapes instead of guessed ones.
