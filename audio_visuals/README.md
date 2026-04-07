# Audio Visuals

WAV-first audio enhancement workspace for podcast-style signals.

## Purpose

This folder adds an interactive audio signal lab to the spectroscopy repository.
It reuses the same analysis mindset used in NMR and stellar workflows:

1. Time-domain inspection
2. Frequency-domain diagnostics
3. Deterministic enhancement pipeline
4. Before/after comparisons with tracked metrics

## Entry Point

- Notebook: `audio_enhancement_pipeline.ipynb`

## Supported Input (V1)

- WAV files (mono processing in the notebook)
- Default path: `audio_visuals/data/audio_enhancement_data.wav`

If no input file is available, the notebook can generate a synthetic speech-like WAV for baseline verification.

## Pipeline Stages

1. Load audio and print metadata
2. Plot waveform and FFT
3. Plot log-frequency spectrogram
4. Segment signal with overlap
5. Enhance each segment with classical DSP fallback
6. Optionally apply ML denoiser hook
7. Reconstruct with overlap-add
8. Produce diagnostics and threshold checks
9. Export enhanced WAV and metric tables

## Outputs

By default, artifacts are written to `audio_visuals/outputs/`:

- `enhanced_podcast.wav`
- `waveform_before_after.png`
- `spectrogram_before_after.png`
- `enhancement_metrics.csv`
- `validation_sweeps.csv`
- `band_energy_summary.csv`

## Verification Profile

The notebook includes deep validation with multiple segment settings and balanced thresholds.
Primary acceptance in V1 is successful DSP fallback execution even when no ML checkpoint is present.

## Notes on ML

The ML path is optional and attempts to follow the existing `DenoiseNetPhysics` checkpoint-loading pattern from `machine_learning/neural_net.py`.
If loading fails, the notebook automatically continues with classical DSP enhancement.

## Scope Boundaries (V1)

- Included: offline enhancement, diagnostics, spectral plots, export
- Excluded: real-time streaming, diarization, production service packaging
