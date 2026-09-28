# histostate

Predict glioblastoma cell-state composition (MES-like, AC-like, OPC-like,
NPC-like) from routine H&E slides, using pathology foundation models.

## Approach

1. Tile TCGA-GBM diagnostic slides and embed each tile with a frozen
   foundation model (Owkin Phikon-v2).
2. Derive per-patient cell-state fractions by deconvolving matched bulk
   RNA-seq with Neftel et al. (2019) signatures.
3. Train an attention-based multiple instance learning (MIL) head to regress
   those fractions from the slide.
4. Use attention maps to show where each state sits on the slide, and check
   them against public GBM spatial transcriptomics.

## Layout

```
src/histostate/     reusable package code
tutorials/          step-by-step learning exercises
tests/              pytest tests
data/               cached embeddings (git-ignored)
```

## Roadmap

- [x] Step 1: linear probe on NCT-CRC-HE (`tutorials/01_linear_probe`)
- [ ] Step 2: attention MIL on Camelyon16 features
- [ ] Step 3: tile and embed TCGA-GBM slides
- [ ] Step 4: cell-state labels from bulk RNA-seq deconvolution
- [ ] Step 5: MIL regression of cell-state fractions
- [ ] Step 6: LoRA fine-tuning of the backbone with `peft`

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
```

Runs on CUDA, Apple Silicon (MPS), or CPU.

## Model licenses

Phikon-v2 uses a custom Owkin license, not a standard open-source one. Read
the model card terms before any commercial use.
