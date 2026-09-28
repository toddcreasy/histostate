"""Pick the best available compute device."""

import torch


def get_device() -> torch.device:
    """Return CUDA if present, then Apple Silicon MPS, then CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
