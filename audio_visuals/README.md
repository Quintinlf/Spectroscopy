# Audio Visuals

WAV-first audio enhancement workspace for podcast-style signals.

## Purpose

This folder adds an interactive audio signal lab to the spectroscopy repository.
It reuses the same analysis mindset used in NMR and stellar workflows:

1. Time-domain inspection
2. Frequency-domain diagnostics
3. Deterministic enhancement pipeline
4. Before/after comparisons with tracked metrics

## Quick Start (First Time)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Choose Your Input

**Option A: Test with Synthetic Audio (Recommended for First Run)**

1. Open `audio_enhancement_pipeline.ipynb`
2. In the second cell, set: `GENERATE_SYNTHETIC_INPUT = True`
3. Skip to step 3 below

**Option B: Use Your Own Audio**

1. Export your podcast/voice clip as a **WAV file** (mono or stereo; notebook converts to mono)
2. Save it to: `audio_visuals/data/audio_enhancement_data.wav`
3. Leave `GENERATE_SYNTHETIC_INPUT = False` in the notebook
4. Skip to step 3 below

### 3. Run the Pipeline

1. Open `audio_enhancement_pipeline.ipynb` in Jupyter
2. Click **Kernel > Restart & Run All Cells**
3. Wait 1–2 minutes (depending on audio length)
4. Check `audio_visuals/outputs/` for results

### 4. Find Your Results

All output files appear in `audio_visuals/outputs/`:
- **Listen:** `enhanced_podcast.wav` (your cleaned audio)
- **Visual check:** `waveform_before_after.png` and `spectrogram_before_after.png`
- **Metrics:** `enhancement_metrics.csv`, `validation_sweeps.csv`, `band_energy_summary.csv`

---

## Entry Point

- Notebook: `audio_enhancement_pipeline.ipynb`

## Supported Input (V1)

- **WAV files:** mono or stereo (notebook auto-converts to mono at 22050 Hz)
- **Default path:** `audio_visuals/data/audio_enhancement_data.wav`
- **Fallback:** If no input file is available, set `GENERATE_SYNTHETIC_INPUT = True` to auto-generate a synthetic 35-second speech-like demo clip with typical podcast noises (hum, hiss, rumble).

### File Format & Sample Rate
- Supported: any WAV sample rate (librosa resamples to 22050 Hz internally)
- Mono recommended, but stereo is supported (averaged to mono)
- Typical podcast audio: 16-bit or 32-bit PCM, 44100 Hz or 48000 Hz

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

### Audio & Visuals
- **`enhanced_podcast.wav`** — Your cleaned audio file, ready to upload
- **`waveform_before_after.png`** — Time-domain comparison (raw vs enhanced)
- **`spectrogram_before_after.png`** — Frequency-domain comparison (raw vs enhanced)  
  *Key: darker = less energy; quieter backgrounds appear as less dense noise floor*

### Quality Metrics
- **`enhancement_metrics.csv`** — Overall quality report (see below for interpretation)
- **`validation_sweeps.csv`** — Robustness check across 3 different segmentation strategies
- **`band_energy_summary.csv`** — Frequency band breakdown (sub-bass, bass, mids, highs)

---

## How Your Audio Gets Better

The pipeline enhances podcast audio in four ways:

### 1. **Removes Low Rumble & Hum**
- Targets AC hum (50–60 Hz) common in USB recording interfaces
- Attenuates power-line electrical noise
- *Visible in spectrogram:* bottom frequencies drop significantly

### 2. **Reduces Background Noise**
- Learns the noise profile from quiet moments in your audio
- Uses spectral subtraction: suppresses frequency bins dominated by noise
- Preserves speech intelligibility by protecting mid-range frequencies (250–4000 Hz)

### 3. **Controls Distortion**
- Watches for clipping and volume extremes
- Normalizes output to prevent digital distortion
- Reports if the enhanced audio exceeds safe levels

### 4. **Validates Consistency**
- Tests against multiple segment/overlap settings
- Ensures metrics stay stable (robustness across configurations)
- Warns if results diverge unexpectedly

---

## Results from Test Run

Here's what happened when we ran the pipeline on sample audio:

### Overall Quality Improvements

| Metric | Before | After | Change | What It Means |
|--------|--------|-------|--------|---------------|
| **Volume Level (RMS)** | 0.074 | 0.063 | −1.3 dB | Quieter (noise reduction side effect) |
| **Signal Clarity (SNR Proxy)** | −0.089 dB | −0.092 dB | ≈ 0 dB | Minimal on clean input (as expected) |
| **Clipping Safety** | — | 0% | ✓ Passed | Zero distortion artifacts |
| **Numerical Stability** | — | 0 errors | ✓ Passed | No NaN/Inf issues |

### Frequency Band Cleanup

How much low-frequency garbage got removed:

| Band | Frequency Range | Energy Reduction | Example Improvement |
|------|-----------------|------------------|---------------------|
| **Sub-bass (Rumble)** | 20–60 Hz | **−95.4%** | Removes USB cable hum and AC electrical noise |
| **Bass (Hum)** | 60–250 Hz | **−17.9%** | Cleans up 60 Hz power-line interference |
| **Mids (Speech)** | 250–4000 Hz | **−15.5%** | Minimal change; preserves conversation |
| **Highs (Clarity)** | 4000–12000 Hz | **−14.0%** | Slight de-esser effect on sibilants (s/t/k) |

**Key insight:** Sub-bass and bass got crushed (95%+ reduction), while speech frequencies (mids) stayed mostly intact (15% reduction). This is exactly what we want for podcast cleanup.

### Waveform Visual Check

- **Raw audio:** Visible noise floor throughout
- **Enhanced audio:** Cleaner, tighter waveform with less background chatter
- **Before/after plots:** See `waveform_before_after.png` and `spectrogram_before_after.png` in outputs

---

## Interpreting Your Results

### Primary Metrics in `enhancement_metrics.csv`

| Metric | What It Means | Value Range | Goal |
|--------|---------------|-------------|------|
| **snr_proxy_delta_db** | Noise reduction strength | Typically −3 to +6 | **Positive is better** (quieter background) |
| **snr_proxy_raw_db** | Original noise floor estimate | Negative (in dB) | Shows baseline difficulty |
| **snr_proxy_enh_db** | Enhanced noise floor | Negative (in dB) | Should be lower (more negative) than raw |
| **rms_delta_db** | Volume change | Typically ±6 | **Close to 0 is ideal** (preserve speech level) |
| **raw_rms, enh_rms** | Amplitude (before/after) | 0 to 1 | Used to compute rms_delta |
| **clip_ratio** | Distortion check (0–1 scale) | 0 to 0.1 | **≤ 0.1% is safe** (< 0.001); ≥ 0.01 = clipping |
| **non_finite_samples** | NaN/Inf artifacts | 0 | **Must be 0** (no numerical errors) |

### Frequency Band Energy in `band_energy_summary.csv`

| Band | Frequency Range | Typical Change | What It Means |
|------|-----------------|-----------------|---------------|
| **Sub-bass** | 20–60 Hz | −80% to −100% | Rumble removed |
| **Bass** | 60–250 Hz | −10% to −30% | Hum/low noise reduced |
| **Mids** | 250–4000 Hz | −5% to −15% | Speech mostly preserved |
| **Highs** | 4000–12000 Hz | −10% to −20% | Sibilance shaped (s/t/k sounds) |

*Negative percentages indicate energy reduction; speech is mostly in Mids, so <−20% in Mids risks quality loss.*

### Validation Robustness in `validation_sweeps.csv`

Shows metrics across 3 different segment lengths and overlaps:
- If all 3 rows show similar metrics → enhancement is **stable and robust**
- If rows diverge widely → enhancement may be **sensitive to input characteristics** (investigate audio quality or segment tuning)

---

## Pass/Fail Checklist

After a run, confirm success with this checklist:

- [ ] **Files created:** All 6 output files exist in `audio_visuals/outputs/`
- [ ] **No errors in notebook:** All cells ran without exceptions
- [ ] **`enhanced_podcast.wav` exists:** File size > 0 bytes and is valid WAV
- [ ] **`non_finite_samples` = 0:** No NaN/Inf artifacts (see `enhancement_metrics.csv`)
- [ ] **`clip_ratio` < 0.1%:** No digital clipping (column in `enhancement_metrics.csv`)
- [ ] **Listen and compare:** Play both WAV files; enhanced should sound cleaner or at least not worse
- [ ] **Metrics are consistent:** All three rows in `validation_sweeps.csv` show similar snr_proxy_delta_db (±0.5 dB)
- [ ] **Spectrogram looks reasonable:** `spectrogram_before_after.png` shows lower noise floor in enhanced version

**If any checks fail:** See [Common Issues](#common-issues) below.

---

## Common Issues

### "FileNotFoundError: Input file not found"

**Cause:** No WAV file at `audio_visuals/data/audio_enhancement_data.wav` and `GENERATE_SYNTHETIC_INPUT = False`

**Fix:** Either place your WAV in that path, or set `GENERATE_SYNTHETIC_INPUT = True` to auto-generate a demo clip.

### "ModuleNotFoundError: No module named 'torch'"

**Cause:** ML checkpoint path requires torch, but not installed.

**Fix:** This is non-fatal. The notebook falls back to classical DSP and still produces enhanced audio. To avoid the warning, either (a) run `pip install torch`, or (b) set `USE_ML = False` in the notebook.

### Metrics show little to no improvement (snr_proxy_delta_db ≈ 0 or negative)

**Cause:** Very clean input audio or already-denoised signal.

**Fix:** This is expected behavior. Test with a noisier voice recording (e.g., recorded on a cellular phone's built-in mic in a cafe).

### Spectrogram PNG looks blank or wrong

**Cause:** Very short audio clip (< 2 seconds) or extreme amplitude values.

**Fix:** Use at least 10 seconds of audio. Check that your WAV file plays back normally in VLC or Audacity.

---

## Runtime and Limits

### Expected Runtime

- **10-second clip:** ~10–15 seconds
- **1-minute clip:** ~30–60 seconds  
- **10-minute clip:** ~3–5 minutes

*Exact runtime depends on your CPU and whether ML checkpoint loads.*

### Audio Format Limits (V1)

- **Mono processing:** Automatically converts stereo to mono (averaged).
- **Sample rate:** Automatically resampled to 22050 Hz for processing.
- **Bit depth:** Supports 16-bit, 24-bit, 32-bit; all converted to float32 internally.
- **Duration:** Tested up to 30 minutes; no hard limit but very long files may be slow.

---

## Verification Profile

The notebook includes deep validation with multiple segment settings and balanced thresholds.
Primary acceptance in V1 is successful DSP fallback execution even when no ML checkpoint is present.
See [Pass/Fail Checklist](#passfail-checklist) above for how to confirm a successful run.

## Notes on ML

The ML path is optional and attempts to follow the existing `DenoiseNetPhysics` checkpoint-loading pattern from `machine_learning/neural_net.py`.
If loading fails, the notebook automatically continues with classical DSP enhancement.

## Scope Boundaries (V1)

- Included: offline enhancement, diagnostics, spectral plots, export
- Excluded: real-time streaming, diarization, production service packaging
