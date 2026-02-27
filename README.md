# Spectroscopy & Analysis Projects

A comprehensive repository for spectroscopic analysis and data processing, featuring Nuclear Magnetic Resonance (NMR), Stellar Spectroscopy, and related computational tools.

## 📂 Project Structure

### 🧲 [Nuclear Magnetic Resonance (NMR)](./nuclear_magnetic_resonance_spectrospy/)
Advanced analysis pipeline for NMR spectroscopy data, including:
- **1D NMR Analysis**: Hydrogen (¹H) and carbon (¹³C) NMR processing
- **2D NMR Spectroscopy**: Complex multi-dimensional NMR techniques
- **Peak Assignment**: Functional group identification and J-coupling analysis
- **Quantum Mechanical Simulation**: Spin system modeling and wavefunction evolution
- **Data Processing**: FFT, peak detection, integration, and visualization

📍 [See NMR README](./nuclear_magnetic_resonance_spectrospy/README.md)

### ⭐ [Stellar Spectroscopy](./stellar_spectrospy/)
Zodiac constellation spectral analysis framework with:
- **SDSS/SIMBAD Data Integration**: Automatic spectrum retrieval from astronomical archives
- **Spectral Analysis Pipeline**: State estimation, energy models, and tensor analysis
- **Zodiac Target Catalog**: Complete 12-constellation stellar database
- **Results Persistence**: SQLite database and CSV output for analysis tracking
- **Interactive Notebooks**: Phase-by-phase spectral analysis workflows

📍 [See Stellar Spectroscopy README](./stellar_spectrospy/README.md)

### 🤖 [Machine Learning](./machine_learning/)
Deep learning models for spectroscopy:
- **Deep Learning Models**: Neural network architectures for spectrum analysis
- **Denoising Networks**: Physics-informed denoising for spectroscopic data
- Model checkpoints and training utilities

### ☀️ [Solar Project](./solar_project/)
Solar irradiance and spectral analysis:
- Solar irradiance data sampling and processing for future api integration
- Spectroscopic visualization tools

---

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/Quintinlf/Spectroscopy.git
cd Spectroscopy

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Analysis
- **NMR Analysis**: See [NMR Project README](./nuclear_magnetic_resonance_spectrospy/README.md)
- **Stellar Spectroscopy**: See [Stellar Spectroscopy README](./stellar_spectrospy/README.md)

---

## 📊 Key Features Across Projects

| Feature | NMR | Stellar | ML |
|---------|-----|---------|-----|
| Data Import/Processing | ✅ | ✅ | ✅ |
| Fourier Analysis | ✅ | ✅ | ✅ |
| Peak Detection | ✅ | ✅ | ✅ |
| Visualization | ✅ | ✅ | ✅ |
| Database Storage | ✅ | ✅ | - |
| Quantum Simulation | ✅ | - | - |
| Archive Integration | - | ✅ | - |
| Deep Learning | - | - | ✅ |

---

## 🛠️ Technology Stack

- **Python 3.7+**
- **Data Processing**: NumPy, Pandas, SciPy
- **Visualization**: Matplotlib, Seaborn
- **Machine Learning**: PyTorch (for deep learning models)
- **Scientific Computing**: Quantum mechanics simulation, FFT analysis
- **Database**: SQLite (for stellar spectroscopy results)
- **Notebooks**: Jupyter

---

## 📝 Repository Contents

```
NMR-Project/
├── nuclear_magnetic_resonance_spectrospy/    # NMR analysis pipeline
│   ├── nmr_function.py
│   ├── peak_assignment.py
│   ├── fall_semester_2025/                   # Advanced NMR techniques
│   ├── spring_semester_2025/                 # Basic NMR analysis
│   ├── quantum_mechanics/                    # QM simulations
│   └── README.md
│
├── stellar_spectrospy/                       # Stellar spectroscopy
│   ├── analysis_runner.py
│   ├── zodiac_targets.py
│   ├── spectral_database.py
│   ├── unified_signal_engine.py
│   ├── phase1_spectral_analysis.ipynb
│   └── README.md
│
├── machine_learning/                         # Deep learning models
│   ├── neural_net.py
│   ├── deep_learning_model.ipynb
│   └── checkpoints/
│
├── solar_project/                            # Solar analysis
│   ├── solar_spec.ipynb
│   └── data/
│
└── README.md                                 # This file
```

---

## 📚 Additional Resources

- **NMR Theory**: See nuclear_magnetic_resonance_spectrospy/ for technical details
- **Stellar Data**: Check stellar_spectrospy/ for constellation targets and analysis methods
- **ML Models**: Review machine_learning/ for model architecture details

---

## 🤝 Contributing

Contributions are welcome! Please ensure that:
- Code follows the existing style conventions
- New features include relevant notebook demonstrations
- Analysis results are documented

---

## 📄 License

See [LICENSE](./LICENSE) file for details.

---

## ✉️ Contact

For questions or collaboration inquiries, please open an issue or reach out through the repository.
