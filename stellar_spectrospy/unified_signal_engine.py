"""
unified_signal_engine.py

Physics-informed spectral state estimator for:
  1. NMR FID quantum spin signals        (JEOL ASCII 3-column format)
  2. Stellar photometric spectra         (Spectrum1D / wavelength-flux arrays)
  3. Oscillation eigenmode extraction   (harmonic ratio analysis)

Architecture
------------
    Input  →  Preprocess  →  FFT  →  Peak Detection  →  RC Score  →  Output

Integration with existing modules (no modifications made to originals):
  - nuclear_magnetic_resonance_spectrospy.nmr_function   → FFT helpers, plots
  - nuclear_magnetic_resonance_spectrospy.peak_assignment → ChemicalShiftDatabase
  - machine_learning.neural_net                          → DenoiseNetPhysics

Physical constants (SI)
-----------------------
  h = 6.626e-34  J·s      (Planck)
  c = 2.998e8    m/s
"""

from __future__ import annotations

import sys
import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from scipy.fft import fft, fftfreq, fftshift
from scipy.signal import savgol_filter, find_peaks
from scipy.integrate import simpson

import matplotlib
matplotlib.use("Agg")          # safe default; notebooks will override
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Optional dependencies — degrade gracefully
# ---------------------------------------------------------------------------
try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    warnings.warn("PyTorch not available — ML denoising disabled.", stacklevel=2)

try:
    from astropy import units as u
    _ASTROPY_AVAILABLE = True
except ImportError:
    _ASTROPY_AVAILABLE = False

# ---------------------------------------------------------------------------
# Repo-relative imports  (add repo root to path if running from subfolders)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from nuclear_magnetic_resonance_spectrospy.nmr_function import (
        compute_fft_spectrum,
        plot_fid,
        plot_full_and_zoom_with_peaks,
    )
    _NMR_FUNC_AVAILABLE = True
except ImportError:
    _NMR_FUNC_AVAILABLE = False
    warnings.warn(
        "nmr_function.py not importable — standalone FFT used instead.",
        stacklevel=2,
    )

try:
    from nuclear_magnetic_resonance_spectrospy.peak_assignment import (
        ChemicalShiftDatabase,
    )
    _PEAK_ASSIGN_AVAILABLE = True
except ImportError:
    _PEAK_ASSIGN_AVAILABLE = False
    warnings.warn(
        "peak_assignment.py not importable — wavelength identification disabled.",
        stacklevel=2,
    )

try:
    from machine_learning.neural_net import (
        DenoiseNetPhysics,
        build_model_from_latest,
        load_checkpoint,
    )
    _DENOISE_AVAILABLE = _TORCH_AVAILABLE
except ImportError:
    _DENOISE_AVAILABLE = False

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
PLANCK_H       = 6.626e-34    # J·s
SPEED_OF_LIGHT = 2.998e8      # m/s
EV_TO_J        = 1.602e-19    # eV → J

# Stellar wavelength band boundaries (Angstroms)
BAND_UV_RANGE  = (1000.0,  4000.0)
BAND_VIS_RANGE = (4000.0,  7000.0)
BAND_IR_RANGE  = (7000.0, 25000.0)


# ===========================================================================
# Core class
# ===========================================================================

class SpectralStateEstimator:
    """
    Unified signal analysis engine.

    Parameters
    ----------
    mode : str
        'nmr'     — FID time-domain complex signal
        'stellar' — wavelength-flux spectrum (angstroms / erg/s/cm²/Å)
        'auto'    — attempt to detect from input shape (default)
    checkpoint_dir : str or Path, optional
        Directory that contains DenoiseNetPhysics .pth checkpoints.
        Falls back to classical denoising when absent.
    device : str
        PyTorch device ('cpu' or 'cuda').
    """

    def __init__(
        self,
        mode: str = "auto",
        checkpoint_dir: Optional[Union[str, Path]] = None,
        device: str = "cpu",
    ):
        self.mode = mode
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        self.device = device

        # State populated by load_* and analyse()
        self._raw_x: Optional[np.ndarray] = None   # time (s) or wavelength (Å)
        self._raw_signal: Optional[np.ndarray] = None   # real or complex amplitude / flux
        self._processed: Optional[np.ndarray] = None
        self._fft_freqs: Optional[np.ndarray] = None
        self._fft_mag: Optional[np.ndarray] = None
        self._peaks: Optional[np.ndarray] = None
        self._peak_props: Dict[str, np.ndarray] = {}
        self._metrics: Dict[str, Any] = {}
        self._ml_model = None
        self._mode_resolved: Optional[str] = None   # 'nmr' or 'stellar'
        self._object_name: Optional[str] = None
        # CWT results (populated by transform_cwt)
        self._cwt_matrix: Optional[np.ndarray] = None   # shape (n_scales, n_points)
        self._cwt_scales: Optional[np.ndarray] = None
        self._cwt_freqs_aa: Optional[np.ndarray] = None  # 1/Å pseudo-frequencies
        # Periodogram peaks (stellar mode – used for RC / harmonic analysis)
        self._pgram_peaks: Optional[np.ndarray] = None
        self._pgram_peak_freqs: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # 1. Input layer
    # ------------------------------------------------------------------

    def load_fid(
        self,
        source: Union[str, Path, np.ndarray],
        delimiter: str = "\t",
        skip_header: int = 1,
        name: Optional[str] = None,
    ) -> "SpectralStateEstimator":
        """
        Load a JEOL ASCII FID file (3-column: X | Real | Imaginary)
        or a pre-loaded ndarray of the same shape.

        Uses nmr_function.load_fid_and_preview when available.
        """
        self._mode_resolved = "nmr"
        self._object_name = name or "NMR FID"

        if isinstance(source, np.ndarray):
            data = source
        else:
            if _NMR_FUNC_AVAILABLE:
                from nuclear_magnetic_resonance_spectrospy.nmr_function import (
                    load_fid_and_preview,
                )
                df, detected_name = load_fid_and_preview(
                    source, delimiter=delimiter, skip_header=skip_header
                )
                data = df.to_numpy()
                self._object_name = name or detected_name
            else:
                data = np.genfromtxt(
                    source, delimiter=delimiter, skip_header=skip_header
                )

        self._raw_x = data[:, 0]                   # time (s)
        # Build complex FID from Real + Imaginary columns
        self._raw_signal = data[:, 1].astype(float)
        if data.shape[1] >= 3:
            self._raw_signal = self._raw_signal + 1j * data[:, 2].astype(float)

        print(f"[FID loaded]  points={len(self._raw_x)}  name='{self._object_name}'")
        return self

    def load_spectrum(
        self,
        wavelength: np.ndarray,
        flux: np.ndarray,
        name: Optional[str] = None,
        wavelength_unit: str = "angstrom",
    ) -> "SpectralStateEstimator":
        """
        Load a stellar spectrum as (wavelength, flux) arrays.
        Accepts astropy Quantity arrays as well as plain ndarrays.
        """
        self._mode_resolved = "stellar"
        self._object_name = name or "Stellar Spectrum"

        # Strip astropy units if present
        if _ASTROPY_AVAILABLE:
            if hasattr(wavelength, "value"):
                wavelength = wavelength.value
            if hasattr(flux, "value"):
                flux = flux.value

        self._raw_x = np.asarray(wavelength, dtype=float)
        self._raw_signal = np.asarray(flux, dtype=float)

        # Sort by ascending wavelength
        order = np.argsort(self._raw_x)
        self._raw_x = self._raw_x[order]
        self._raw_signal = self._raw_signal[order]

        # Sanitise: remove NaN/Inf
        valid = np.isfinite(self._raw_signal)
        if not np.all(valid):
            bad = (~valid).sum()
            warnings.warn(f"Removed {bad} non-finite flux values.", stacklevel=2)
            self._raw_x = self._raw_x[valid]
            self._raw_signal = self._raw_signal[valid]

        print(
            f"[Spectrum loaded]  points={len(self._raw_x)}"
            f"  λ=[{self._raw_x[0]:.1f}, {self._raw_x[-1]:.1f}] Å"
            f"  name='{self._object_name}'"
        )
        return self

    # ------------------------------------------------------------------
    # 2. Preprocessing layer
    # ------------------------------------------------------------------

    def preprocess(
        self,
        use_ml: bool = True,
        sg_window: int = 51,
        sg_poly: int = 3,
        checkpoint_name: str = "DenoiseNetPhysics_final_best.pth",
    ) -> "SpectralStateEstimator":
        """
        Physics-aware denoising.

        Priority:
          1. DenoiseNetPhysics checkpoint (if use_ml=True and available)
          2. Savitzky-Golay + complex magnitude

        For stellar spectra the ML model is applied to the flux as a
        single-channel real signal (in_ch=1 flag via a wrapper).
        """
        if self._raw_signal is None:
            raise RuntimeError("No signal loaded. Call load_fid() or load_spectrum() first.")

        sig = self._raw_signal.copy()
        applied_ml = False

        # ---- attempt ML denoising ----
        if use_ml and _DENOISE_AVAILABLE and self.checkpoint_dir is not None:
            ckpt_path = Path(self.checkpoint_dir) / checkpoint_name
            if not ckpt_path.exists():
                # fallback: pick the latest timestamped checkpoint
                candidates = sorted(
                    Path(self.checkpoint_dir).glob("DenoiseNetPhysics_*.pth")
                )
                if candidates:
                    ckpt_path = candidates[-1]

            if ckpt_path.exists():
                applied_ml = self._apply_ml_denoiser(sig, ckpt_path)

        if not applied_ml:
            # ---- classical fallback ----
            if self._mode_resolved == "nmr":
                # magnitude of complex FID, then SG smooth
                real_part = np.real(sig)
                imag_part = np.imag(sig) if np.iscomplexobj(sig) else np.zeros_like(sig)
                wl = max(sg_window, 5)
                if wl % 2 == 0:
                    wl += 1
                wl = min(wl, len(real_part) - 1 if (len(real_part) - 1) % 2 != 0 else len(real_part) - 2)
                real_smooth = savgol_filter(real_part, wl, sg_poly)
                imag_smooth = savgol_filter(imag_part, wl, sg_poly)
                sig = real_smooth + 1j * imag_smooth
            else:
                # stellar — smooth flux with Savitzky-Golay
                wl = min(sg_window, len(sig) - (1 if (len(sig) - 1) % 2 != 0 else 2))
                wl = max(wl, sg_poly + 1)
                if wl % 2 == 0:
                    wl += 1
                sig = savgol_filter(sig.astype(float), wl, sg_poly)

            method = "Savitzky-Golay"
        else:
            method = "DenoiseNetPhysics"

        self._processed = sig
        print(f"[Preprocess]  method={method}")
        return self

    def _apply_ml_denoiser(self, sig: np.ndarray, ckpt_path: Path) -> bool:
        """
        Apply DenoiseNetPhysics to the loaded signal.
        Returns True if successful, False if fallback needed.
        """
        try:
            import torch

            model = DenoiseNetPhysics(in_ch=2).to(self.device)
            ok, msg = load_checkpoint(model, str(ckpt_path))
            if not ok:
                print(f"[ML]  {msg}  → falling back to classical filter")
                return False
            print(f"[ML]  {msg}")
            model.eval()

            # Prepare tensor [1, 2, L]
            if self._mode_resolved == "nmr" and np.iscomplexobj(sig):
                real = sig.real.astype(np.float32)
                imag = sig.imag.astype(np.float32)
            else:
                real = sig.real.astype(np.float32)
                imag = np.zeros_like(real)

            L = len(real)
            t = torch.tensor(
                np.stack([real, imag])[None], dtype=torch.float32, device=self.device
            )  # [1, 2, L]

            with torch.no_grad():
                out = model(t)  # [1, 2, L]

            out_np = out.squeeze(0).cpu().numpy()
            self._processed = out_np[0] + 1j * out_np[1]
            return True

        except Exception as exc:
            warnings.warn(f"ML denoiser error: {exc} → classical fallback", stacklevel=3)
            return False

    # ------------------------------------------------------------------
    # 3. Spectral transformation
    # ------------------------------------------------------------------

    def transform(self) -> "SpectralStateEstimator":
        """
        Compute FFT (NMR) or frequency-domain representation (stellar).

        For NMR:
          Uses nmr_function.compute_fft_spectrum if available, else scipy.fft.
        For stellar:
          Treats evenly-resampled flux as a signal and computes its periodogram
          to detect oscillation pattern spacings (quasi-Fourier domain).
        """
        sig = self._processed if self._processed is not None else self._raw_signal
        if sig is None:
            raise RuntimeError("No signal to transform. Run preprocess() first.")

        if self._mode_resolved == "nmr":
            self._transform_nmr(sig)
        else:
            self._transform_stellar(sig)

        print(
            f"[Transform]  mode={self._mode_resolved}"
            f"  freq_bins={len(self._fft_freqs)}"
        )
        return self

    def _transform_nmr(self, sig: np.ndarray) -> None:
        if _NMR_FUNC_AVAILABLE and not np.iscomplexobj(sig):
            # Build array compatible with compute_fft_spectrum
            arr = np.column_stack([self._raw_x, np.real(sig), np.imag(sig)])
            result = compute_fft_spectrum(arr, time_col=0, real_col=1)
            self._fft_freqs = result["frequencies"]
            self._fft_mag   = result["magnitude"]
        else:
            # Direct scipy FFT on complex FID
            n = len(sig)
            dt = (self._raw_x[-1] - self._raw_x[0]) / max(n - 1, 1)
            spectrum = fft(sig, n=n)
            self._fft_freqs = fftshift(fftfreq(n, dt))
            self._fft_mag   = fftshift(np.abs(spectrum))

    def _transform_stellar(self, sig: np.ndarray) -> None:
        """
        For a stellar wavelength spectrum the 'frequency' axis is
        optical frequency  ν = c / λ (Hz).  We compute spectral flux
        density as function of ν and also the Lomb-Scargle-style
        periodogram over the wavelength axis to detect oscillation spacings.
        """
        wl_angstrom = self._raw_x                      # Å
        flux = np.asarray(sig, dtype=float)

        # Optical frequency axis (Hz)
        wl_m = wl_angstrom * 1e-10
        nu = np.sort(SPEED_OF_LIGHT / wl_m)
        # Sort flux to match ascending ν
        nu_sort_idx = np.argsort(SPEED_OF_LIGHT / wl_m)
        flux_nu = flux[nu_sort_idx]

        self._fft_freqs = nu                # Hz (optical frequency)
        self._fft_mag   = flux_nu           # flux as fn of ν

        # Also store wavelength oscillation periodogram
        # (uniform resample then FFT → detect periodic absorption spacing)
        wl_uniform = np.linspace(wl_angstrom[0], wl_angstrom[-1], len(flux))
        flux_uniform = np.interp(wl_uniform, wl_angstrom, flux)
        flux_detrended = flux_uniform - np.polyval(
            np.polyfit(wl_uniform, flux_uniform, 3), wl_uniform
        )
        period_fft  = np.abs(fft(flux_detrended))
        period_freq = fftfreq(len(flux_detrended),
                              d=(wl_uniform[1] - wl_uniform[0]))  # 1/Å
        # Positive half only
        pos = period_freq > 0
        self._periodogram_freqs = period_freq[pos]
        self._periodogram_power = period_fft[pos]

        # Detect periodogram peaks (used for RC / harmonic families in stellar mode)
        self._detect_periodogram_peaks()

    # ------------------------------------------------------------------
    # 3b. Continuous Wavelet Transform (CWT) — stellar mode
    # ------------------------------------------------------------------

    def transform_cwt(
        self,
        n_scales: int = 64,
        min_scale: float = 2.0,
        max_scale: float = 300.0,
        wavelet_w: float = 6.0,
    ) -> "SpectralStateEstimator":
        """
        Compute a Continuous Wavelet Transform (CWT) using the Morlet wavelet.

        Unlike the FFT which decomposes a signal into pure sinusoids of global
        frequency, CWT produces a 2-D time-frequency (here wavelength-scale)
        map.  This reveals *where* in the spectrum a given feature width
        (scale) is concentrated — useful for localising broad molecular bands
        vs narrow atomic lines.

        Parameters
        ----------
        n_scales : int
            Number of scale steps (frequency resolution).
        min_scale / max_scale : float
            Scale range in Angstroms (feature width range to examine).
        wavelet_w : float
            Morlet central frequency parameter (higher w = more frequency
            resolution, less time localisation).

        Stores
        ------
        _cwt_matrix       : 2-D power array  (n_scales × n_points)
        _cwt_scales       : scale values (Å)
        _cwt_freqs_aa     : pseudo-frequencies (1/Å) for each scale
        """
        sig = self._processed if self._processed is not None else self._raw_signal
        if sig is None:
            raise RuntimeError("Load and preprocess a spectrum before CWT.")

        flux = np.asarray(sig, dtype=float)

        # Uniformly resample onto even λ grid (required for meaningful scales)
        wl_uniform = np.linspace(self._raw_x[0], self._raw_x[-1], len(flux))
        flux_uniform = np.interp(wl_uniform, self._raw_x, flux)
        d_lambda = wl_uniform[1] - wl_uniform[0]  # Å per sample

        # Detrend: remove 3rd-order polynomial baseline
        flux_detrended = flux_uniform - np.polyval(
            np.polyfit(wl_uniform, flux_uniform, 3), wl_uniform
        )

        # Scales in sample units (convert Å → samples)
        scales_aa = np.geomspace(min_scale, max_scale, n_scales)
        scales_samp = scales_aa / d_lambda

        # Pure-numpy Morlet CWT via FFT convolution
        # (replaces scipy.signal.cwt which was removed in scipy >=1.12)
        coef = self._morlet_cwt_fft(flux_detrended, scales_samp, w=wavelet_w)
        power = np.abs(coef) ** 2  # (n_scales, n_points)

        self._cwt_matrix   = power
        self._cwt_scales   = scales_aa
        self._cwt_freqs_aa = 1.0 / scales_aa  # pseudo-frequency (1/Å)

        # Store x-axis for plotting
        self._cwt_wl_uniform = wl_uniform

        print(f"[CWT]  scales={n_scales}  lam-range=[{min_scale:.0f}, {max_scale:.0f}] Ang  "
              f"pseudo-freq=[{1/max_scale:.4f}, {1/min_scale:.4f}] 1/Ang")
        return self

    @staticmethod
    def _morlet_cwt_fft(
        signal: np.ndarray,
        scales: np.ndarray,
        w: float = 6.0,
    ) -> np.ndarray:
        """
        Compute a CWT with the real Morlet wavelet using FFT convolution.

        This is a pure-numpy implementation that works with any scipy version.

        Parameters
        ----------
        signal : 1-D float array
        scales : array of scale values (in sample units)
        w      : Morlet central frequency parameter

        Returns
        -------
        coef : complex array of shape (len(scales), len(signal))
        """
        from numpy.fft import fft, ifft, fftfreq
        n = len(signal)
        sig_fft = fft(signal, n=n)
        freqs   = fftfreq(n)                     # cycles/sample, range [-0.5, 0.5)

        coef = np.zeros((len(scales), n), dtype=complex)
        norm = np.pi ** (-0.25)                  # Morlet normalisation

        for i, s in enumerate(scales):
            # Frequency-domain Morlet: hat{psi}(f*s) = norm * sqrt(2pi*s)
            #   * exp(-0.5*(2*pi*s*f - w)^2)
            arg = 2.0 * np.pi * s * freqs - w
            psi_hat = norm * np.sqrt(2 * np.pi * s) * np.exp(-0.5 * arg ** 2)
            coef[i] = ifft(sig_fft * psi_hat, n=n)

        return coef

    def _detect_periodogram_peaks(
        self,
        height_frac: float = 0.05,
        prominence_frac: float = 0.02,
    ) -> None:
        """
        Find peaks in the wavelength-oscillation periodogram.

        These represent recurring absorption-line spacings in the spectrum
        and are the physically correct domain for RC scoring in stellar mode.
        Called automatically at the end of _transform_stellar().
        """
        if not hasattr(self, '_periodogram_power') or self._periodogram_power is None:
            return
        power = self._periodogram_power
        max_p = power.max()
        if max_p == 0:
            self._pgram_peaks = np.array([], dtype=int)
            self._pgram_peak_freqs = np.array([])
            return
        peaks, _ = find_peaks(
            power,
            height=height_frac * max_p,
            prominence=prominence_frac * max_p,
            distance=3,
        )
        self._pgram_peaks = peaks
        self._pgram_peak_freqs = self._periodogram_freqs[peaks] if len(peaks) else np.array([])

    # ------------------------------------------------------------------
    # 4. Peak / eigenmode detection
    # ------------------------------------------------------------------

    def detect_peaks(
        self,
        height_frac: float = 0.05,
        prominence_frac: float = 0.03,
        min_distance_pts: int = 5,
    ) -> "SpectralStateEstimator":
        """
        Locate peaks in the magnitude/flux spectrum.

        Adapts peak_assignment.PeakAssignmentAnalyzer logic to both NMR ppm
        domain and stellar wavelength / optical-frequency domain.
        """
        if self._fft_mag is None:
            raise RuntimeError("Run transform() before detect_peaks().")

        mag = self._fft_mag
        max_val = mag.max()
        if max_val == 0:
            self._peaks = np.array([], dtype=int)
            return self

        peaks, props = find_peaks(
            mag,
            height=height_frac * max_val,
            prominence=prominence_frac * max_val,
            distance=min_distance_pts,
        )
        self._peaks = peaks
        self._peak_props = props

        print(f"[Peaks]  detected={len(peaks)}")
        return self

    def identify_features(self) -> List[Dict[str, Any]]:
        """
        Annotate detected peaks with physical/chemical identity.

        NMR mode: delegates to ChemicalShiftDatabase (ppm assignment).
        Stellar mode: matches against canonical stellar absorption lines
                      (Hα, Hβ, Ca H&K, Mg I, Na D, TiO bands, etc.).
        """
        if self._peaks is None or len(self._peaks) == 0:
            return []

        features = []
        peak_idx = self._peaks

        if self._mode_resolved == "nmr" and _PEAK_ASSIGN_AVAILABLE:
            # Convert Hz to ppm (399.78 MHz assumed unless we know better)
            spectrometer_hz = 399.78e6
            ppm_vals = self._fft_freqs[peak_idx] / (spectrometer_hz / 1e6)
            for i, (idx, ppm) in enumerate(zip(peak_idx, ppm_vals)):
                groups = ChemicalShiftDatabase.identify_functional_group(ppm)
                features.append({
                    "index": idx,
                    "frequency": self._fft_freqs[idx],
                    "amplitude": self._fft_mag[idx],
                    "ppm": ppm,
                    "assignments": groups[:3],
                })

        else:
            # Stellar — use optical frequency / wavelength annotation
            STELLAR_LINES = {
                "Hα":     6562.8,  "Hβ":     4861.3,  "Hγ":     4340.5,
                "Hδ":     4101.7,  "Ca K":   3933.7,  "Ca H":   3968.5,
                "Mg I":   5175.0,  "Na D":   5892.5,  "He I":   5876.0,
                "Fe I":   5270.0,  "TiO-a":  7054.0,  "TiO-b":  7589.0,
                "Ca IRT": 8542.0,
            }
            # Convert optical frequency (Hz) back to wavelength for lookup
            peak_nu  = self._fft_freqs[peak_idx]
            peak_wl  = (SPEED_OF_LIGHT / peak_nu) * 1e10  # → Angstroms

            for i, (idx, wl_peak, nu_peak) in enumerate(
                zip(peak_idx, peak_wl, peak_nu)
            ):
                closest = min(STELLAR_LINES.items(), key=lambda kv: abs(kv[1] - wl_peak))
                features.append({
                    "index":     idx,
                    "frequency": nu_peak,
                    "wavelength_angstrom": wl_peak,
                    "amplitude": self._fft_mag[idx],
                    "nearest_line": closest[0],
                    "line_wavelength": closest[1],
                    "delta_angstrom": abs(closest[1] - wl_peak),
                })

        self._features = features
        return features

    # ------------------------------------------------------------------
    # 5. Resonance Coherence Score  (astro-seismology extension)
    # ------------------------------------------------------------------

    def resonance_coherence(
        self,
        max_p: int = 6,
        max_q: int = 6,
        sigma: float = 1.0,
    ) -> float:
        """
        Compute the Resonance Coherence (RC) score across detected peaks.

        Definition
        ----------
        RC = Σ_{i≠j} Σ_{p=1}^{max_p} Σ_{q=1}^{max_q}
              exp( -|f_i - (p/q) * f_j| / σ_eff )

        For stellar mode the RC is computed on wavelength-periodogram peaks
        (1/Å units, period of recurring absorption spacings) rather than raw
        optical frequencies (10^14 Hz).  This is physically correct because:
          - Optical frequencies of absorption lines do NOT form harmonic ratios
            (they reflect discrete quantum transitions, not oscillation modes)
          - Recurring SPACINGS between absorption lines DO form harmonic series
            in stars with eigenmode excitation (p-modes, g-modes)
          - σ is auto-scaled to the median peak frequency so the Gaussian
            kernel width is ~5% of the typical spacing — prevents RC≡0

        For NMR mode the original Hz-domain peaks are used (J-coupling multiplets
        DO form harmonic ratios in the direct frequency space).

        Parameters
        ----------
        max_p, max_q : int
            Upper limit on numerator/denominator integers.
        sigma : float
            Sensitivity scale as a *fraction of the median peak frequency*.
            Default 1.0 means 100% — use 0.05 for 5% window (recommended
            for periodogram peaks where adjacent harmonics are close).

        Returns
        -------
        float : RC score (non-negative; larger = more harmonic structure)
        """
        # ── Choose which peak set to score ───────────────────────────────────
        if self._mode_resolved == "stellar":
            # Use periodogram peaks (1/Å) — these represent eigenmode spacings
            if self._pgram_peak_freqs is not None and len(self._pgram_peak_freqs) >= 2:
                freqs = np.abs(self._pgram_peak_freqs)
            elif self._peaks is not None and len(self._peaks) >= 2:
                # Fallback: use absorption-line optical frequencies but
                # normalise so RC is scale-invariant
                freqs = np.abs(self._fft_freqs[self._peaks])
                freqs = freqs[freqs > 0]
            else:
                self._metrics["coherence_score"] = 0.0
                return 0.0
        else:
            if self._peaks is None or len(self._peaks) < 2:
                return 0.0
            freqs = np.abs(self._fft_freqs[self._peaks])
            freqs = np.abs(freqs[freqs != 0])

        if len(freqs) < 2:
            self._metrics["coherence_score"] = 0.0
            return 0.0

        # ── Auto-scale sigma ─────────────────────────────────────────────────
        freq_median = float(np.median(freqs))
        if freq_median == 0:
            sigma_eff = max(sigma, 1e-30)
        else:
            sigma_eff = sigma * freq_median   # sigma is now a fraction
        # For NMR keep old behaviour (sigma=1.0 Hz reasonable)
        if self._mode_resolved == "nmr" and sigma == 1.0:
            sigma_eff = 1.0

        p_vals = np.arange(1, max_p + 1)
        q_vals = np.arange(1, max_q + 1)
        ratios = (p_vals[:, None] / q_vals[None, :]).ravel()
        ratios = np.unique(np.round(ratios, 8))

        rc = 0.0
        for i, fi in enumerate(freqs):
            for j, fj in enumerate(freqs):
                if i == j:
                    continue
                for r in ratios:
                    rc += np.exp(-abs(fi - r * fj) / sigma_eff)

        n_pairs = len(freqs) * (len(freqs) - 1)
        rc_norm = rc / max(n_pairs * len(ratios), 1)
        self._metrics["coherence_score"] = float(rc_norm)
        return float(rc_norm)

    # ------------------------------------------------------------------
    # 6. Energy distribution
    # ------------------------------------------------------------------

    def compute_energy_metrics(self) -> Dict[str, Any]:
        """
        Compute energy-related metrics.

        NMR:   E_k = h * f_k  for each peak (Joules)
        Stellar: Integrate flux over UV / VIS / IR wavelength bands.
                 Returns E_band = ∫ F(λ) dλ  (erg/s/cm²) per band.
        """
        metrics: Dict[str, Any] = {}

        if self._peaks is not None and len(self._peaks) > 0:
            peak_freqs = np.abs(self._fft_freqs[self._peaks])
            energy_per_peak = [PLANCK_H * float(f) for f in peak_freqs]
            metrics["energy_per_peak"] = energy_per_peak
            metrics["peak_frequencies"] = peak_freqs.tolist()
            metrics["peak_amplitudes"]  = self._fft_mag[self._peaks].tolist()

        if self._mode_resolved == "stellar" and self._raw_signal is not None:
            wl = self._raw_x         # Angstroms
            flux = np.asarray(
                self._processed if self._processed is not None else self._raw_signal,
                dtype=float,
            )

            def band_flux(lo: float, hi: float) -> float:
                mask = (wl >= lo) & (wl <= hi)
                if mask.sum() < 2:
                    return 0.0
                return float(simpson(flux[mask], x=wl[mask]))

            metrics["e_uv"]   = band_flux(*BAND_UV_RANGE)
            metrics["e_vis"]  = band_flux(*BAND_VIS_RANGE)
            metrics["e_ir"]   = band_flux(*BAND_IR_RANGE)
            metrics["e_total"] = band_flux(wl[0], wl[-1])

        metrics["coherence_score"] = self._metrics.get("coherence_score")
        self._metrics.update(metrics)
        return metrics

    # ------------------------------------------------------------------
    # 7. Full analysis pipeline (convenience wrapper)
    # ------------------------------------------------------------------

    def analyse(
        self,
        use_ml_denoise: bool = True,
        height_frac: float = 0.05,
        prominence_frac: float = 0.03,
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline in one call:
          preprocess → transform → detect_peaks → resonance_coherence
                     → compute_energy_metrics → identify_features

        Returns the combined metrics dictionary.
        """
        self.preprocess(use_ml=use_ml_denoise)
        self.transform()
        self.detect_peaks(height_frac=height_frac, prominence_frac=prominence_frac)
        self.resonance_coherence()
        self.compute_energy_metrics()
        features = self.identify_features()
        self._metrics["features"] = features
        self._metrics["n_peaks"]  = len(self._peaks) if self._peaks is not None else 0
        self._metrics["object_name"] = self._object_name
        return self._metrics

    # ------------------------------------------------------------------
    # 8. Harmonic family detection
    # ------------------------------------------------------------------

    def find_harmonic_families(
        self,
        base_tolerance: float = 0.02,
    ) -> List[List[float]]:
        """
        Group detected peaks into harmonic series.

        For stellar mode this searches for harmonics in the wavelength
        periodogram peaks (recurring absorption-line spacings in 1/Å).
        For NMR mode it searches in the direct-frequency FFT peaks.

        Returns list of groups:  [[f0, 2f0, 3f0, ...], ...]
        """
        # Choose the peak set for harmonic search
        if self._mode_resolved == "stellar" and self._pgram_peak_freqs is not None and len(self._pgram_peak_freqs) >= 2:
            raw_freqs = np.abs(self._pgram_peak_freqs)
        elif self._peaks is not None and len(self._peaks) > 0:
            raw_freqs = np.abs(self._fft_freqs[self._peaks])
        else:
            return []

        freqs = sorted(f for f in raw_freqs if f > 0)
        used  = set()
        families = []

        for i, f0 in enumerate(freqs):
            if i in used:
                continue
            family = [f0]
            for j, fj in enumerate(freqs):
                if j == i or j in used:
                    continue
                ratio = fj / f0
                nearest_int = round(ratio)
                if (
                    nearest_int >= 2
                    and abs(ratio - nearest_int) / nearest_int < base_tolerance
                ):
                    family.append(fj)
                    used.add(j)
            if len(family) >= 2:
                families.append(sorted(family))
                used.add(i)

        self._metrics["harmonic_families"] = families
        return families

    # ------------------------------------------------------------------
    # 9. Visualisation
    # ------------------------------------------------------------------

    def plot_pipeline(
        self,
        object_name: Optional[str] = None,
        figsize: Tuple[int, int] = (16, 10),
        show: bool = True,
    ) -> plt.Figure:
        """
        4-panel notebook-friendly plot:
          (A) Raw signal       (B) Denoised signal
          (C) FFT / spectrum   (D) Peak eigenmodes
        """
        name = object_name or self._object_name or "Signal"
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        ax_raw, ax_proc, ax_fft, ax_peaks = axes.ravel()

        xlabel_x = "Time (s)" if self._mode_resolved == "nmr" else "Wavelength (Å)"
        ylabel_x = "Amplitude" if self._mode_resolved == "nmr" else "Flux"
        xlabel_f = "Frequency (Hz)" if self._mode_resolved == "nmr" else "Optical Frequency ν (Hz)"

        raw_y = np.real(self._raw_signal) if np.iscomplexobj(self._raw_signal) \
                else self._raw_signal

        # (A) Raw
        ax_raw.plot(self._raw_x, raw_y, linewidth=0.8, color="steelblue")
        ax_raw.set_title(f"{name} — Raw", fontweight="bold")
        ax_raw.set_xlabel(xlabel_x)
        ax_raw.set_ylabel(ylabel_x)

        # (B) Denoised
        if self._processed is not None:
            proc_y = np.real(self._processed) if np.iscomplexobj(self._processed) \
                     else self._processed
            ax_proc.plot(self._raw_x, proc_y, linewidth=0.8, color="darkorange")
            ax_proc.set_title(f"{name} — Denoised", fontweight="bold")
        else:
            ax_proc.text(0.5, 0.5, "Not preprocessed", ha="center", va="center",
                         transform=ax_proc.transAxes)
        ax_proc.set_xlabel(xlabel_x)
        ax_proc.set_ylabel(ylabel_x)

        # (C) FFT / Spectrum
        if self._fft_freqs is not None and self._fft_mag is not None:
            ax_fft.plot(self._fft_freqs, self._fft_mag, linewidth=0.7, color="mediumpurple")
            ax_fft.set_title(f"{name} — Frequency Domain", fontweight="bold")
            ax_fft.set_xlabel(xlabel_f)
            ax_fft.set_ylabel("Magnitude / Flux(ν)")

        # (D) Peak eigenmodes
        if self._fft_freqs is not None and self._fft_mag is not None:
            ax_peaks.plot(self._fft_freqs, self._fft_mag, linewidth=0.7,
                          color="mediumpurple", alpha=0.5)
            if self._peaks is not None and len(self._peaks) > 0:
                ax_peaks.plot(
                    self._fft_freqs[self._peaks],
                    self._fft_mag[self._peaks],
                    "x", color="crimson", ms=8, mew=2,
                    label=f"{len(self._peaks)} peaks"
                )
                ax_peaks.legend(fontsize=9)
            ax_peaks.set_title(f"{name} — Peak Eigenmodes", fontweight="bold")
            ax_peaks.set_xlabel(xlabel_f)
            ax_peaks.set_ylabel("Magnitude / Flux(ν)")

            # Annotate RC score
            rc  = self._metrics.get("coherence_score")
            if rc is not None:
                ax_peaks.text(
                    0.97, 0.95, f"RC={rc:.4f}",
                    ha="right", va="top", transform=ax_peaks.transAxes,
                    fontsize=10, color="crimson",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="crimson", alpha=0.7),
                )

        plt.suptitle(f"Spectral State Estimator — {name}", fontsize=13, fontweight="bold")
        plt.tight_layout()
        if show:
            plt.show()
        return fig

    def plot_stellar_wavelength_spectrum(
        self,
        object_name: Optional[str] = None,
        annotate_lines: bool = True,
        show: bool = True,
    ) -> plt.Figure:
        """
        Single-panel calibrated stellar spectrum in wavelength space with
        canonical spectral line markers.  (Stellar mode only.)
        """
        if self._mode_resolved != "stellar":
            raise RuntimeError("This plot is for stellar mode spectra only.")

        name = object_name or self._object_name or "Stellar Spectrum"
        flux = (np.asarray(self._processed, dtype=float)
                if self._processed is not None
                else np.asarray(self._raw_signal, dtype=float))

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(self._raw_x, flux, linewidth=0.8, color="navy", alpha=0.9, label="Flux")

        if annotate_lines:
            LINES = {
                "Hα": 6562.8, "Hβ": 4861.3, "Hγ": 4340.5,
                "Ca K": 3933.7, "Ca H": 3968.5,
                "Mg I": 5175.0, "Na D": 5892.5,
                "TiO": 7054.0,
            }
            y_top = np.nanmax(flux)
            for lname, lwl in LINES.items():
                if self._raw_x[0] < lwl < self._raw_x[-1]:
                    ax.axvline(lwl, color="tomato", linewidth=0.8, linestyle="--", alpha=0.6)
                    ax.text(lwl + 5, y_top * 0.92, lname, fontsize=7,
                            color="tomato", rotation=90, va="top")

        if self._peaks is not None and len(self._peaks) > 0:
            # Convert peak optical-freq indices back to wavelength for plotting
            peak_nu  = self._fft_freqs[self._peaks]
            peak_wl  = (SPEED_OF_LIGHT / peak_nu) * 1e10
            peak_amp = self._fft_mag[self._peaks]
            # Normalise amplitudes to flux scale
            scale = np.nanmax(flux) / (peak_amp.max() + 1e-30)
            ax.scatter(peak_wl, peak_amp * scale, marker="v", s=50,
                       color="crimson", zorder=5, label="Detected Peaks")

        ax.set_xlabel("Wavelength (Å)", fontsize=12)
        ax.set_ylabel("Flux (erg s⁻¹ cm⁻² Å⁻¹)", fontsize=12)
        ax.set_title(f"Stellar Spectrum: {name}", fontsize=13, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.25)
        plt.tight_layout()
        if show:
            plt.show()
        return fig

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def compare_transforms(
        self,
        figsize: Tuple[int, int] = (16, 10),
        show: bool = True,
    ) -> plt.Figure:
        """
        Side-by-side FFT vs CWT comparison plot.

        Requires transform() and transform_cwt() to have been run.
        """
        name = self._object_name or "Spectrum"
        has_fft = self._fft_freqs is not None
        has_cwt = self._cwt_matrix is not None

        if not has_fft:
            raise RuntimeError("Run transform() (FFT) first.")

        nrows = 2 if has_cwt else 1
        fig, axes = plt.subplots(nrows, 2, figsize=figsize)
        axs = axes.ravel() if has_cwt else axes

        # ── Top-left: FFT periodogram (1/Å domain)
        ax0 = axs[0] if has_cwt else axes[0]
        if hasattr(self, '_periodogram_freqs') and self._periodogram_freqs is not None:
            ax0.semilogy(self._periodogram_freqs, self._periodogram_power,
                        linewidth=0.9, color="steelblue")
            if self._pgram_peaks is not None and len(self._pgram_peaks):
                ax0.semilogy(
                    self._pgram_peak_freqs,
                    self._periodogram_power[self._pgram_peaks],
                    "x", ms=8, mew=2, color="crimson",
                    label=f"{len(self._pgram_peaks)} periodogram peaks"
                )
                ax0.legend(fontsize=9)
            ax0.set_xlabel("Spatial Frequency (1/Å)", fontsize=11)
            ax0.set_ylabel("Periodogram Power", fontsize=11)
            ax0.set_title(
                f"FFT Periodogram — {name}\n"
                "Shows recurring absorption-line spacing patterns",
                fontsize=11, fontweight="bold"
            )
            rc_val = self._metrics.get("coherence_score")
            if rc_val is not None:
                ax0.text(0.97, 0.95, f"RC = {rc_val:.5f}",
                        ha="right", va="top", transform=ax0.transAxes,
                        fontsize=10, color="crimson",
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="crimson", alpha=0.8))
        else:
            ax0.text(0.5, 0.5, "No periodogram data — run transform() first",
                    ha="center", va="center", transform=ax0.transAxes)

        # ── Top-right: Flux(ν) optical frequency
        ax1 = axs[1] if has_cwt else axes[1]
        ax1.plot(self._fft_freqs, self._fft_mag, linewidth=0.7, color="mediumpurple")
        if self._peaks is not None and len(self._peaks):
            ax1.plot(self._fft_freqs[self._peaks], self._fft_mag[self._peaks],
                    "x", ms=8, mew=2, color="crimson",
                    label=f"{len(self._peaks)} absorption peaks")
            ax1.legend(fontsize=9)
        ax1.set_xlabel("Optical Frequency ν (Hz)", fontsize=11)
        ax1.set_ylabel("Flux(ν)  (erg s⁻¹ cm⁻² Hz⁻¹)", fontsize=11)
        ax1.set_title(
            f"Optical Frequency Spectrum — {name}\n"
            "Each dip = absorption line quantum transition",
            fontsize=11, fontweight="bold"
        )

        if has_cwt:
            # ── Bottom-left: CWT power map
            ax2 = axs[2]
            extent = [
                self._cwt_wl_uniform[0], self._cwt_wl_uniform[-1],
                self._cwt_freqs_aa[-1], self._cwt_freqs_aa[0],
            ]
            im = ax2.imshow(
                self._cwt_matrix,
                aspect="auto",
                extent=extent,
                origin="upper",
                cmap="inferno",
                interpolation="bilinear",
            )
            plt.colorbar(im, ax=ax2, label="CWT Power", pad=0.01)
            ax2.set_xlabel("Wavelength (Å)", fontsize=11)
            ax2.set_ylabel("Pseudo-frequency (1/Å)", fontsize=11)
            ax2.set_title(
                f"CWT Power Map (Morlet) — {name}\n"
                "Bright = strong feature at that wavelength & scale",
                fontsize=11, fontweight="bold"
            )

            # ── Bottom-right: CWT ridge (dominant scale per wavelength)
            ax3 = axs[3]
            dominant_scale_idx = np.argmax(self._cwt_matrix, axis=0)
            dominant_freq = self._cwt_freqs_aa[dominant_scale_idx]
            ax3.plot(self._cwt_wl_uniform, dominant_freq,
                    linewidth=0.8, color="darkorange")
            ax3.set_xlabel("Wavelength (Å)", fontsize=11)
            ax3.set_ylabel("Dominant Feature Scale (1/Å)", fontsize=11)
            ax3.set_title(
                f"CWT Ridge — {name}\n"
                "Dominant feature width at each wavelength position",
                fontsize=11, fontweight="bold"
            )

        plt.suptitle(
            f"Transform Comparison: FFT vs CWT — {name}",
            fontsize=13, fontweight="bold"
        )
        plt.tight_layout()
        if show:
            plt.show()
        return fig

    @property
    def metrics(self) -> Dict[str, Any]:
        """Latest computed metrics dict."""
        return self._metrics

    def summary(self) -> str:
        m = self._metrics
        lines = [
            f"SpectralStateEstimator — {self._object_name}",
            f"  Mode            : {self._mode_resolved}",
            f"  Points          : {len(self._raw_x) if self._raw_x is not None else 0}",
            f"  Peaks detected  : {m.get('n_peaks', '—')}",
            f"  Coherence (RC)  : {m.get('coherence_score', '—')}",
        ]
        if self._mode_resolved == "stellar":
            for band in ("e_uv", "e_vis", "e_ir", "e_total"):
                lines.append(f"  {band:<16}: {m.get(band, '—')}")
        else:
            ep = m.get("energy_per_peak", [])
            if ep:
                lines.append(
                    f"  E_peak range    : {min(ep):.3e} – {max(ep):.3e} J"
                )
        if m.get("harmonic_families"):
            lines.append(f"  Harmonic families: {len(m['harmonic_families'])}")
        return "\n".join(lines)
