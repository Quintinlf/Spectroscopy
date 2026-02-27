# 🤖 Machine Learning for Spectroscopy

This module provides deep learning models optimized for spectroscopic data processing, with a focus on denoising and analysis of NMR and stellar spectra. Featured models leverage physics-informed neural network architectures to enhance signal quality while preserving spectroscopic features.

---

## ✨ Features

- 🧠 **Deep Learning Models**: PyTorch-based neural network architectures for spectrum analysis
- 🔇 **Physics-Informed Denoising**: DenoiseNetPhysics architecture with dilated residual blocks
- 🎯 **Checkpoint Management**: Load and manage pre-trained model checkpoints
- 📊 **Training Pipeline**: Complete workflow for training models on spectroscopic data
- 🔄 **Batch Processing**: Efficient processing of multiple spectral samples
- 📉 **Performance Evaluation**: Built-in metrics and visualization tools
- 🛠️ **Legacy Support**: TensorFlow/Keras models maintained for backwards compatibility

---

## 📁 Project Structure

```
machine_learning/
├── neural_net.py                    # Core PyTorch and TensorFlow models
├── deep_learning_model.ipynb        # Comprehensive training & analysis notebook
│
├── checkpoints/                     # Pre-trained model weights
│   ├── DenoiseNetPhysics_*.pth      # Various checkpoint versions
│   ├── DenoiseNetPhysics_best.pth   # Latest best model
│   ├── DenoiseNetPhysics_final_best.pth
│   ├── DenoiseNetPhysics_aggressive_best.pth
│   └── DenoiseNetPhysics_extended_best.pth
│
└── README.md (this file)
```

---

## 🚀 Quick Start

### Installation

```bash
# Core dependencies (PyTorch)
pip install torch

# Or with CUDA support (GPU acceleration)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Legacy TensorFlow (optional)
pip install tensorflow
```

### Basic Usage: Denoising Spectra

```python
import torch
from machine_learning.neural_net import DenoiseNetPhysics, load_latest_checkpoint

# Build and load the model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = DenoiseNetPhysics()
checkpoint_path = 'checkpoints/DenoiseNetPhysics_final_best.pth'
model = load_latest_checkpoint(model, checkpoint_path)
model.to(device).eval()

# Denoise a batch of spectra
with torch.no_grad():
    noisy_spectrum = torch.randn(1, 1, 8192)  # (batch, channels, length)
    denoised = model(noisy_spectrum.to(device))
    
print(f"Output shape: {denoised.shape}")
```

### Training from Scratch

```python
import torch.optim as optim
from machine_learning.neural_net import DenoiseNetPhysics

# Initialize model
model = DenoiseNetPhysics()
optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.MSELoss()

# Training loop
for epoch in range(num_epochs):
    for noisy_batch, clean_batch in train_loader:
        optimizer.zero_grad()
        denoised = model(noisy_batch)
        loss = criterion(denoised, clean_batch)
        loss.backward()
        optimizer.step()
```

---

## 🏗️ Model Architectures

### DenoiseNetPhysics (Primary Model)

A physics-informed convolutional neural network for spectroscopic denoising:

```
Input (batch, 1, spectrum_length)
    ↓
Conv1d (in_channels=1, out_channels=64)
    ↓
Dilated Residual Blocks (multiple)
    │ ├─ Conv1d (dilation=1, 2, 4, 8, ...)
    │ ├─ ReLU activation
    │ └─ Skip connections
    ↓
Conv1d (out_channels=1)
    ↓
Output (batch, 1, spectrum_length)
```

**Key Features:**
- **Dilated convolutions**: Capture multi-scale spectral features
- **Residual connections**: Preserve low-frequency components
- **Physics-informed loss**: Weights for frequency domain reconstruction
- **Variable receptive field**: Adapts to different spectral widths

### SimpleNeuralNetwork (Legacy)

TensorFlow/Keras MLP for compatibility:
```
Input → Dense(64, ReLU) → Dense(64, ReLU) → Dense(num_classes, Softmax) → Output
```

---

## 📊 Training & Evaluation

### Training Objectives
- **Primary**: Minimize MSE between denoised and clean spectra
- **Secondary**: Preserve spectroscopic features (peaks, fine structure)
- **Regularization**: L2 weight regularization to prevent overfitting

### Data Preparation

```python
import numpy as np
from torch.utils.data import TensorDataset, DataLoader

# Prepare data: (N_samples, 1, spectrum_length)
clean_spectra = np.load('clean_spectra.npy')  # shape: (N, L)
clean_spectra = clean_spectra[:, np.newaxis, :]  # → (N, 1, L)

# Create synthetic noisy version (for demonstration)
noise = np.random.randn(*clean_spectra.shape) * 0.1
noisy_spectra = clean_spectra + noise

# Create DataLoader
dataset = TensorDataset(
    torch.FloatTensor(noisy_spectra),
    torch.FloatTensor(clean_spectra)
)
train_loader = DataLoader(dataset, batch_size=32, shuffle=True)
```

### Checkpoint Management

```python
# Save checkpoint
checkpoint = {
    'epoch': epoch,
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'loss': loss
}
torch.save(checkpoint, 'checkpoints/DenoiseNetPhysics_latest.pth')

# Load checkpoint
checkpoint = torch.load('checkpoints/DenoiseNetPhysics_best.pth')
model.load_state_dict(checkpoint['model_state_dict'])
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
epoch = checkpoint['epoch']
```

---

## 📈 Available Checkpoints

| Checkpoint | Purpose | Notes |
|-----------|---------|-------|
| `DenoiseNetPhysics_final_best.pth` | Production model | Best overall performance |
| `DenoiseNetPhysics_aggressive_best.pth` | Heavy denoising | Strong noise removal, may blur features |
| `DenoiseNetPhysics_extended_best.pth` | Extended training | Longer training runs |
| `DenoiseNetPhysics_adversarial_best.pth` | Adversarial training | Robust to various noise types |
| `DenoiseNetPhysics_*.pth` (dated) | Epoch checkpoints | For recovery of intermediate states |

**Selection Guide:**
- Use `DenoiseNetPhysics_final_best.pth` for most applications
- Use `aggressive_best.pth` for very noisy data
- Use `adversarial_best.pth` for unknown noise characteristics

---

## 🔧 Advanced Features

### GPU Acceleration

```python
import torch

# Check GPU availability
print(f"GPU available: {torch.cuda.is_available()}")
print(f"GPU count: {torch.cuda.device_count()}")

# Move model to GPU
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
model = model.to(device)

# Move batches to GPU during training
for noisy_batch, clean_batch in train_loader:
    noisy_batch = noisy_batch.to(device)
    clean_batch = clean_batch.to(device)
    # ... training code ...
```

### Batch Processing

```python
def denoise_batch(spectra_array, model, device, batch_size=32):
    """Denoise a large array of spectra efficiently."""
    model.eval()
    results = []
    
    with torch.no_grad():
        for i in range(0, len(spectra_array), batch_size):
            batch = torch.FloatTensor(
                spectra_array[i:i+batch_size, np.newaxis, :]
            ).to(device)
            denoised = model(batch)
            results.append(denoised.cpu().numpy())
    
    return np.vstack(results)
```

### Model Evaluation Metrics

```python
from sklearn.metrics import mean_squared_error, mean_absolute_error

def evaluate_model(model, test_loader, device):
    """Compute evaluation metrics on test set."""
    model.eval()
    mse_list, mae_list = [], []
    
    with torch.no_grad():
        for noisy, clean in test_loader:
            noisy = noisy.to(device)
            clean = clean.to(device)
            
            denoised = model(noisy)
            
            mse = torch.nn.functional.mse_loss(denoised, clean)
            mae = torch.nn.functional.l1_loss(denoised, clean)
            
            mse_list.append(mse.item())
            mae_list.append(mae.item())
    
    return {
        'MSE': np.mean(mse_list),
        'MAE': np.mean(mae_list),
        'RMSE': np.sqrt(np.mean(mse_list))
    }
```

---

## 🎓 Using the Jupyter Notebook

Open `deep_learning_model.ipynb` for a complete walkthrough:

1. **Model Architecture**: Detailed explanation of DenoiseNetPhysics
2. **Data Generation**: Synthetic data with physics-informed noise
3. **Training Loop**: Full training with optimization
4. **Checkpoint Saving**: Managing model versions
5. **Evaluation**: Quantitative and visual assessment
6. **Visualization**: Denoising comparisons and error analysis
7. **Export**: Saving for production use

**Key Notebook Sections:**
- Theory and motivation
- Architecture design decisions
- Training strategies and optimization
- Loss functions and metrics
- Results and analysis
- Best practices

---

## 🔬 Physics-Informed Design

### Why Physics Matters

Spectroscopic denoising requires preserving:
- Peak positions and intensities
- Fine multiplet structure
- Phase information (for NMR)
- Chemical shift accuracy

Our architecture uses:
- **Dilated convolutions**: Larger receptive fields without aggressive downsampling
- **Residual connections**: Preserve signal DC bias and low-frequency components
- **Physics-based loss**: Frequency-domain weighting to prioritize spectroscopic features
- **Domain knowledge**: Training synthetic data that mimics realistic spectroscopic noise

---

## 🛠️ Requirements

### Core
- Python 3.7+
- PyTorch 1.9+
- NumPy
- Matplotlib (for visualization)

### Optional
- CUDA 11.8+ (for GPU support)
- TensorFlow 2.x (legacy models)
- scikit-learn (for metrics)

See main `requirements.txt` for complete dependencies.

---

## 📚 Integration with Other Modules

### Use with NMR Analysis
```python
from nuclear_magnetic_resonance_spectrospy.nmr_function import perform_fft
from machine_learning.neural_net import DenoiseNetPhysics

# 1. Load and transform noisy FID data
df, name = load_fid_and_preview('noisy_nmr.asc')
noisy_spectrum = perform_fft(df)

# 2. Denoise with neural network
denoised_spectrum = denoise_model(torch.FloatTensor(noisy_spectrum))

# 3. Continue with standard NMR analysis
peaks = find_peaks_adaptive(denoised_spectrum)
functional_groups = identify_functional_groups(peaks, denoised_spectrum)
```

### Use with Stellar Spectroscopy
```python
from stellar_spectrospy.analysis_runner import ZodiacRunner
from machine_learning.neural_net import DenoiseNetPhysics

# 1. Retrieve stellar spectrum
runner = ZodiacRunner()
spectrum = runner.retrieve_star_spectrum('Aldebaran')

# 2. Pre-process with neural network
denoised = denoise_model(spectrum)

# 3. Proceed with analysis
results = runner.analyze_spectrum(denoised)
```

---

## 🤝 Troubleshooting

### CUDA Out of Memory
```python
# Reduce batch size
batch_size = 8  # instead of 32

# Clear cache
torch.cuda.empty_cache()

# Use CPU
device = torch.device('cpu')
```

### Low Denoising Performance
- Check if using the correct checkpoint (final_best.pth recommended)
- Verify spectrum normalization (input should be ≈ [0, 1])
- Consider using aggressive_best.pth for very noisy data
- Ensure spectrum length matches expected input (typically 8192)

### Model Loading Issues
```python
# If checkpoint doesn't match current architecture:
checkpoint = torch.load('checkpoint.pth', map_location='cpu')

# Load only state dict
model.load_state_dict(checkpoint['model_state_dict'], strict=False)
```

---

## 📖 References & Resources

- **PyTorch Documentation**: https://pytorch.org/docs/
- **Dilated Convolutions**: [Multi-Scale Context Aggregation by Dilated Convolutions](https://arxiv.org/abs/1511.07122)
- **Residual Networks**: [Deep Residual Learning for Image Recognition](https://arxiv.org/abs/1512.03385)
- **Spectroscopy ML**: [Deep Learning Applications in Spectroscopy](https://www.nature.com/articles/s41467-021-25254-7)

---

## 🔗 Related Projects

- [NMR Spectroscopy Analysis](../nuclear_magnetic_resonance_spectrospy/README.md)
- [Stellar Spectroscopy Analysis](../stellar_spectrospy/README.md)
- [Main Repository](../README.md)

---

## 💡 Best Practices

1. **Always use pre-trained checkpoints** rather than training from scratch unless you have domain-specific data
2. **Normalize input spectra** to [0, 1] range before applying the model
3. **Consider ensemble methods** combining multiple checkpoint versions for robustness
4. **Validate results** visually and against known spectroscopic features
5. **Use GPU** for significant speedup (10-100x depending on model size)
6. **Monitor training loss** for convergence and overfitting indicators
7. **Document** hyperparameters and training conditions for reproducibility

---

## 📝 Citation

If you use this machine learning module in your research, please cite:

```bibtex
@software{quintinlf_spectroscopy_2025,
  title={Spectroscopy \& Analysis Projects},
  author={Quintinlf},
  year={2025},
  url={https://github.com/Quintinlf/Spectroscopy}
}
```

