# 🧲 Nuclear Magnetic Resonance (NMR) Spectroscopy Analysis

A comprehensive pipeline for parsing, analyzing, and visualizing Nuclear Magnetic Resonance (NMR) spectroscopy data. This project provides end-to-end analysis capabilities including 1D NMR (¹H and ¹³C), 2D NMR techniques, peak assignment, functional group identification, spin-spin coupling analysis, and quantum mechanical simulation of spin systems.

---

## ✨ Features

- 📥 **Data Import & Visualization**  
  Reads JEOL ASCII FID files and visualizes raw time-domain signals. **(ASCII format recommended)**

- 🔄 **Fourier Transform**  
  Converts time-domain FID to frequency domain using FFT, producing publication-quality NMR spectra.

- 📈➕ **Peak Detection & Integration**  
  Detects significant peaks using customizable thresholds and integrates peak areas to estimate relative proton/carbon counts.

- 🧬 **Functional Group Identification**  
  Maps detected peaks to chemical functional groups based on chemical shift (δ, ppm) ranges with interactive visualization.

- 🔗 **Spin-Spin Coupling (J-Coupling) Analysis**  
  Detects multiplets, estimates J-coupling constants ($J$), and visualizes multiplet structures with annotated coupling patterns.

- 📊 **1D & 2D NMR Techniques**  
  Support for hydrogen (¹H), carbon (¹³C), and 2D NMR experiments (COSY, HMQC, etc.)

- ⚛️ **Quantum Mechanical Simulation**  
  Simulates NMR Hamiltonians for coupled spin systems, computes eigenstates, and animates wavefunction evolution.

---

## 📁 Project Structure

```
nuclear_magnetic_resonance_spectrospy/
│
├── nmr_function.py                      # Core NMR analysis functions
├── peak_assignment.py                   # Peak identification & functional group mapping
│
├── fall_semester_2025/                  # Advanced NMR techniques
│   ├── 2D_nmr.ipynb                     # 2D NMR experiments
│   ├── carbon_nmr.ipynb                 # ¹³C NMR analysis
│   ├── chemical_visualization.ipynb     # Advanced visualization
│   ├── decoupling_logic.ipynb           # Decoupling techniques
│   ├── krishna_presentation.ipynb       # Presentation materials
│   └── checkpoints/                     # Model checkpoints
│
├── spring_semester_2025/                # Foundational NMR analysis
│   ├── hydrogen_nmr.ipynb               # ¹H NMR analysis
│   ├── 13_03_11_indst_1H fid.asc        # Sample JEOL FID ASCII data
│   └── raw.githubusercontent.com/       # Cached remote data
│
├── quantum_mechanics/                   # Quantum mechanical simulations
│   └── quauntum_nmr.ipynb               # QM spin system simulation
│
├── chem_tools/                          # Chemistry utilities & visualization
│   └── chem_details.ipynb
│
├── data/                                # Additional NMR datasets
│
└── README.md                            # This file
```

---

## 🚀 Quick Start

### Basic NMR Analysis

**Option 1: Interactive Jupyter Notebook (Recommended)**
1. Navigate to `spring_semester_2025/` for basic ¹H NMR analysis
2. Open `hydrogen_nmr.ipynb` in Jupyter, VS Code, or Google Colab
3. Edit the file path in the data import cell to point to your JEOL FID ASCII file
4. Run all cells sequentially to perform complete analysis pipeline

**Option 2: Advanced Analysis**
- For ¹³C NMR: See `fall_semester_2025/carbon_nmr.ipynb`
- For 2D NMR: See `fall_semester_2025/2D_nmr.ipynb`
- For quantum simulation: See `quantum_mechanics/quauntum_nmr.ipynb`

### Data Import & Processing

```python
from nmr_function import load_fid_and_preview, perform_fft, find_peaks_adaptive

# Load JEOL ASCII FID data
df, name = load_fid_and_preview('path/to/your_nmr_data.asc')

# Perform Fourier transformation
spectrum = perform_fft(df)

# Detect peaks
peaks = find_peaks_adaptive(spectrum, threshold=0.05)
```

---

## 🛠️ Key Functions & Modules

### `nmr_function.py`
Core NMR analysis utilities:

| Function | Purpose |
|----------|---------|
| `load_fid_and_preview()` | Load JEOL ASCII FID, validate, and preview |
| `perform_fft()` | Convert time-domain FID to frequency domain |
| `find_peaks_adaptive()` | Detect peaks with customizable thresholds |
| `integrate_peaks()` | Calculate peak areas (proton/carbon integration) |
| `estimate_jcoupling()` | Extract J-coupling constants from multiplets |
| `identify_functional_groups()` | Map peaks to functional groups by chemical shift |
| `plot_spectrum_with_peaks()` | Publication-quality spectrum visualization |

### `peak_assignment.py`
Functional group identification and peak assignment:
- Maps chemical shifts (ppm) to functional group types
- Supports common organic functional groups (alkyl, aromatic, aldehyde, etc.)
- Customizable chemical shift ranges for specific conditions

### Chemical Shift Reference (PPM ranges)

| Functional Group | δ (ppm) |
|------------------|---------|
| Alkyl (sp³ CH₃/CH₂/CH) | 0.80–1.50 |
| Allylic / Next to C=C | 1.60–2.20 |
| Benzylic / Next to Ar | 2.20–2.90 |
| Alkyne (≡C–H) | 1.80–2.60 |
| α to C=O (ketone/ester) | 2.00–3.20 |
| Halogen / O / N adjacent | 3.00–4.50 |
| Vinylic (C=C–H) | 4.50–6.50 |
| Aromatic (Ar–H) | 6.00–8.50 |
| Aldehyde (–CHO) | 9.50–10.50 |
| Carboxylic Acid (–COOH) | 10.00–13.00 |

---

## 📋 Complete Analysis Workflow

Each notebook implements this standard workflow:

```
1️⃣  Data Import & Preview
    ↓ (load_fid_and_preview)
    
2️⃣  Fourier Transform
    ↓ (perform_fft)
    
3️⃣  Spectrum Visualization
    ↓ (plot_spectrum)
    
4️⃣  Peak Detection
    ↓ (find_peaks_adaptive)
    
5️⃣  Peak Integration
    ↓ (integrate_peaks)
    
6️⃣  Functional Group Assignment
    ↓ (identify_functional_groups)
    
7️⃣  J-Coupling Analysis
    ↓ (estimate_jcoupling)
    
8️⃣  Result Visualization & Export
    → CSV/tables/plots
```

---

## 📊 Analysis Examples

### Basic ¹H NMR Analysis
```python
import matplotlib.pyplot as plt
from nmr_function import (
    load_fid_and_preview, perform_fft, 
    find_peaks_adaptive, identify_functional_groups
)

# Load data
df, name = load_fid_and_preview('sample.asc')

# FFT and peak detection
spectrum = perform_fft(df)
peaks = find_peaks_adaptive(spectrum, threshold=0.05)

# Identify functional groups
groups = identify_functional_groups(peaks, spectrum)

# Visualize
plt.figure(figsize=(12, 5))
plt.plot(spectrum)
plt.scatter(peaks['position'], peaks['height'], color='red')
plt.xlabel('Chemical Shift (ppm)')
plt.ylabel('Intensity')
plt.title(f'{name} - ¹H NMR')
plt.show()
```

### ¹³C NMR Analysis
```python
# See: fall_semester_2025/carbon_nmr.ipynb
# Similar workflow but optimized for ¹³C data and broader chemical shift ranges
```

### 2D NMR (COSY/HMQC)
```python
# See: fall_semester_2025/2D_nmr.ipynb
# Handle 2D array data with correlation analysis
```

---

## 🛠️ Requirements & Installation

### Minimal Requirements
- Python 3.7+
- numpy
- pandas
- matplotlib
- scipy

### Full Installation (for all features)
```bash
pip install numpy pandas matplotlib seaborn scipy pillow scikit-image
```

### Optional (for quantum simulation)
```bash
pip install qiskit  # For advanced quantum simulations
```

All dependencies are listed in the main repository's `requirements.txt`.

---

## 📂 Data Format

### Supported Input Format: JEOL ASCII FID

```
X (index)    Real (FID)    Imaginary (FID)
0            123.45        98.76
1            125.34        97.65
2            124.56        96.54
...          ...           ...
```

**File Requirements:**
- Tab or space-delimited text file
- Header row (skipped by default)
- Exactly 3 columns: (Index, Real, Imaginary)
- Can be local file or HTTP(S) URL

**Loading:**
```python
df, name = load_fid_and_preview('path/to/file.asc')
```

---

## 🔬 Advanced Topics

### Quantum Mechanical Simulation
Simulate NMR behavior for coupled spin systems:
- Build spin system Hamiltonian
- Compute eigenvalues/eigenstates
- Animate wavefunction evolution
- See: `quantum_mechanics/quauntum_nmr.ipynb`

### 2D NMR Techniques
Analyze multi-dimensional correlations:
- **COSY**: Carbon-oxygen coupling
- **HMQC**: Heteronuclear Multiple-Quantum Coherence
- **HSQC**: Heteronuclear Single-Quantum Coherence
- See: `fall_semester_2025/2D_nmr.ipynb`

### Custom Functional Groups
Extend the functional group database:
1. Edit `PPM_SHIFT_DEFAULTS` in `nmr_function.py`
2. Add new (name, ppm_range) pairs
3. Use in `identify_functional_groups()`

---

## 📚 Notebooks Guide

| Notebook | Focus | Level |
|----------|-------|-------|
| `spring_semester_2025/hydrogen_nmr.ipynb` | ¹H NMR fundamentals | Beginner |
| `fall_semester_2025/carbon_nmr.ipynb` | ¹³C NMR analysis | Intermediate |
| `fall_semester_2025/2D_nmr.ipynb` | 2D techniques (COSY, HMQC) | Advanced |
| `fall_semester_2025/decoupling_logic.ipynb` | Proton decoupling | Intermediate |
| `quantum_mechanics/quauntum_nmr.ipynb` | Quantum simulation | Advanced |
| `fall_semester_2025/krishna_presentation.ipynb` | Research presentation | Reference |

---

## 📈 Output & Results

Typical analysis outputs:
- **Spectrum plots** with detected peaks marked
- **Integration table** with peak areas and assignments
- **Functional group summary** with chemical shift assignments
- **J-coupling constants** extracted from multiplet patterns
- **GIF animations** (for quantum simulations)

---

## 🤝 Troubleshooting

### Common Issues

**"Failed to read data"**
- Ensure file is JEOL ASCII format (3 columns: X, Real, Imaginary)
- Check delimiter (tab or space)
- Verify file path is correct

**"No peaks detected"**
- Lower the `threshold` parameter in `find_peaks_adaptive()`
- Check that spectrum was properly normalized
- Verify data quality

**"Functional groups not identified"**
- Ensure peaks are within expected ppm ranges
- Check for proper chemical shift calibration (TMS reference)
- Review functional group database for your solvent/compound

---

## 🔗 Related Resources

- [JEOL NMR Data Format](https://www.jeol.co.jp/)
- [Chemical Shift Database](https://www.sigmaaldrich.com/)
- [Spin-Spin Coupling Reference](https://chem.libretexts.org/)
- [Main Repository README](../README.md)

---

## 💡 Tips & Best Practices

1. **Data Quality**: Raw JEOL ASCII format is recommended; other formats may require preprocessing
2. **Calibration**: Ensure proper TMS (0 ppm) reference for accurate chemical shift assignment
3. **Threshold Tuning**: Start with threshold=0.05 and adjust based on noise level
4. **Peak Assignment**: Always verify functional group assignments visually
5. **Documentation**: Keep notes on solvent, temperature, and acquisition parameters
6. **Reproducibility**: Store analysis scripts alongside raw data

---

## 🤓 Using in Google Colab

For cloud-based analysis without local Python installation:

```python
# Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Clone repository
!git clone https://github.com/Quintinlf/Spectroscopy.git
%cd Spectroscopy

# Install dependencies
!pip install -r requirements.txt

# Import and use
from nuclear_magnetic_resonance_spectrospy.nmr_function import *
```

  See `detect_and_plot_multiplet` for multiplet and J-coupling analysis.

- **Quantum Simulation:**  
  See the final section for Hamiltonian construction, eigenstate computation, and animation.

---

## 🖼️ Example Output

- **NMR Spectrum:**  
  Plots of the frequency-domain spectrum with detected peaks and functional group annotations.

- **Integration Table:**  
  Printed output of relative proton counts for each peak.

- **Multiplet Visualization:**  
  Zoomed-in plots of multiplets with J-coupling constants annotated.

- **Quantum Animation:**  
  Animated GIF (`pen.gif`) showing the time evolution of a quantum wavefunction in a potential.

---

## 📝 Notes

- The code is modular and can be adapted for other NMR datasets or extended for more advanced analyses.
- For best results, use high-quality FID data and adjust thresholds as needed for your instrument and sample.

---

## 📜 License

This project is for educational and research purposes.

---

## 👤 Author

Created by Quintinlf
For questions, open an issue or contact via GitHub.

---

**See `parsing_nmr_data.ipynb` for full code and documentation.**
