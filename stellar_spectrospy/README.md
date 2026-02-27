# ⭐ Stellar Spectroscopy Analysis

A comprehensive framework for analyzing stellar spectra from astronomical archives, with a focus on zodiac constellation targets. This project integrates data from SDSS (Sloan Digital Sky Survey) and SIMBAD astronomical databases to perform spectral analysis and energy modeling.

---

## ✨ Features

- 🔭 **Automatic Spectrum Retrieval**: Query SDSS and SIMBAD for stellar spectra with built-in caching
- 📊 **Spectral Analysis Pipeline**: End-to-end workflow for spectrum processing and analysis
- 🎯 **Zodiac Constellation Targets**: Complete catalog of stars in all 12 zodiac constellations
- ⚡ **Energy & Tensor Analysis**: Advanced spectral state estimation and energy modeling
- 💾 **Results Persistence**: SQLite database and CSV export for comprehensive tracking
- 📈 **Interactive Notebooks**: Phase-based analysis workflows for exploration and learning

---

## 📁 Project Structure

```
stellar_spectrospy/
├── analysis_runner.py              # Main orchestration pipeline
├── zodiac_targets.py               # 12 constellation star catalog
├── spectral_database.py            # SQLite database interface
├── spectral_results.csv            # Analysis results export
├── spectral_results.db             # Persistent results database
│
├── Core Analysis Modules:
│   ├── planetary_model.py          # Planetary motion modeling
│   ├── stellar_energy_model.py     # Energy calculations & analysis
│   ├── tensor_analysis.py          # Tensor operations for spectra
│   ├── unified_signal_engine.py    # Unified signal processing
│   └── spectral_database.py        # Data persistence layer
│
├── Notebooks:
│   ├── intro_to_stellar_spec.ipynb          # Introduction & basics
│   ├── phase1_spectral_analysis.ipynb       # Phase 1 detailed analysis
│   ├── stellar_spec_ana.ipynb               # General spectral analysis
│   └── spectral_cache/                      # Cached star data (CSV)
│
└── README.md (this file)
```

---

## 🚀 Quick Start

### Basic Usage

```python
from stellar_spectrospy.analysis_runner import ZodiacRunner

# Initialize the analysis runner
runner = ZodiacRunner(
    cache_dir="spectral_cache",
    db_path="spectral_results.db"
)

# Analyze a single constellation (e.g., Taurus)
df = runner.run_constellation("Taurus")
print(df)

# Analyze all 12 constellations
runner.run_all(max_stars_per_const=3)

# Load previously cached results
results_df = runner.summary_dataframe()
```

### Running in Jupyter

1. Open `phase1_spectral_analysis.ipynb` or `intro_to_stellar_spec.ipynb`
2. The notebooks handle:
   - Spectrum retrieval and caching
   - Spectral analysis and processing
   - Results visualization and storage
   - Energy and tensor calculations

---

## 🔑 Key Modules

### `analysis_runner.py`
Orchestrates the complete spectral analysis workflow:
- **ZodiacRunner**: Main class for constellation-by-constellation analysis
- Handles SDSS/SIMBAD querying with local caching
- Integrates SpectralStateEstimator for analysis
- Persists results to SQLite and CSV

**Usage Pattern:**
```python
runner = ZodiacRunner(cache_dir="spectral_cache", db_path="spectral_results.db")
df = runner.run_all(max_stars_per_const=5)
```

### `zodiac_targets.py`
Complete catalog of stars in each zodiac constellation:
- Maintains a mapping of constellations to stellar targets
- Provides easy access to constellation data
- Used by ZodiacRunner for target selection

### `spectral_database.py`
SQLite database interface for persistent storage:
- Stores spectral analysis results
- Tracks metadata and analysis parameters
- Enables querying and exporting results
- Supports CSV export for external analysis

### `stellar_energy_model.py`
Energy and spectral state estimation:
- Computes stellar energy parameters
- Estimates spectral states from data
- Performs advanced spectral classification

### `tensor_analysis.py`
Tensor operations for multi-dimensional spectral data:
- Decomposes spectral matrices
- Performs tensor-based analysis
- Supports higher-order spectral relationships

### `unified_signal_engine.py`
Centralized signal processing framework:
- Handles FFT and spectral transformations
- Implements filtering and smoothing
- Coordinates between modules

---

## 📊 Spectral Analysis Workflow

```
1. Data Retrieval
   ↓
2. Spectrum Loading & Caching
   ↓
3. Preprocessing (normalization, filtering)
   ↓
4. Spectral Analysis (peaks, features, classification)
   ↓
5. Energy & Tensor Analysis
   ↓
6. Results Persistence (DB + CSV)
   ↓
7. Visualization & Export
```

---

## 🎯 Zodiac Constellations

The project includes stars from all 12 zodiac constellations:
- **Aries, Taurus, Gemini, Cancer, Leo, Virgo**
- **Libra, Scorpius, Sagittarius, Capricornus, Aquarius, Pisces**

Each constellation has multiple target stars with their SDSS IDs and SIMBAD identifiers.

---

## 💾 Output Formats

### SQLite Database
Results are stored in `spectral_results.db`:
- Complete metadata for each star analyzed
- Spectral parameters and metrics
- Timestamps and analysis versions
- Queryable for custom analysis

### CSV Export
`spectral_results.csv` provides:
- Tabular format for spreadsheet analysis
- Compatible with pandas and external tools
- Easy integration with visualization software

---

## 🛠️ Requirements

- Python 3.7+
- numpy
- pandas
- matplotlib
- scipy
- Request library for SDSS/SIMBAD queries
- (See main `requirements.txt` in repository root)

---

## 📈 Advanced Features

### Caching System
Local CSV cache in `spectral_cache/` prevents redundant archive queries:
- Stores previously retrieved spectra
- Dramatically speeds up repeated analyses
- Enables offline experimentation

### Database Interface
SQLite backend for scalable storage:
- ACID-compliant persistent storage
- Efficient querying across results
- Version tracking for reproducibility

### Modular Architecture
Easy to extend with new analysis methods:
- Add custom spectral metrics in `stellar_energy_model.py`
- Implement new tensor operations in `tensor_analysis.py`
- Integrate additional data sources

---

## 📚 Example Analysis

```python
import pandas as pd
from stellar_spectrospy.analysis_runner import ZodiacRunner

# Run analysis on Taurus constellation
runner = ZodiacRunner(cache_dir="spectral_cache")
taurus_results = runner.run_constellation("Taurus")

# Export to CSV for further analysis
taurus_results.to_csv("taurus_analysis.csv", index=False)

# Query results by star
aldebaran = taurus_results[taurus_results['star'] == 'Aldebaran']
print(aldebaran)
```

---

## 🔗 Related Resources

- [SDSS Data Release](https://www.sdss.org/)
- [SIMBAD Astronomical Database](http://simbad.u-strasbg.fr/)
- [Main Repository README](../README.md)

---

## 📝 Notes

- Initial constellation runs may be slow due to archive queries; results are cached automatically
- For large-scale analyses, consider adding intermediate checkpoints
- Results are additive—running `run_all()` multiple times will append new results

---

## 🤝 Contribution

To add new constellations or analysis methods:
1. Update `zodiac_targets.py` with new targets
2. Add analysis logic to appropriate module
3. Ensure results persist to database
4. Document changes in relevant notebook

