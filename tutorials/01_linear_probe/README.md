# Step 1: Linear probe on NCT-CRC-HE

## Goal

Learn the core PyTorch loop (model, loss, optimizer, backward, step) on the
easiest possible setup, and see how much a pathology foundation model already
knows before any fine-tuning.

## Setup

- **Backbone:** `owkin/phikon-v2`, frozen. Each 224px tile becomes a 1024-dim vector.
- **Head:** `BatchNorm1d` (feature standardization) plus one `nn.Linear` layer. About 9k trainable parameters.
- **Train:** `nct_crc_he_1k` (999 tiles).
- **Test:** `crc_val_he_7k` (7,180 tiles from different patients and a different lab).
- **Classes:** ADI, BACK, DEB, LYM, MUC, MUS, NORM, STR, TUM.

## Run

From the repo root:

```bash
uv sync
uv run python tutorials/01_linear_probe/run.py
```

The first run downloads about 1.1 GB of images plus the 1.2 GB model and caches
embeddings in `data/features/`. Later runs skip embedding and train in seconds.

View the training curve:

```bash
uv run mlflow ui
```

## What to expect

A frozen backbone plus a linear layer should score well above 0.90 balanced
accuracy. If it does, the backbone already separates tissue types, and the head
only draws lines between clusters.

## Things to try

1. Swap `owkin/phikon-v2` for `owkin/phikon` and compare.
2. Replace `LinearProbe` with a two-layer MLP. Does it help, or overfit on 999 tiles?
3. Train on only 10 tiles per class. How far does accuracy drop?
4. Swap `BatchNorm1d` for `LayerNorm` and compare. `tests/test_probe.py` shows a
   case where `LayerNorm` fails completely; work out why.
