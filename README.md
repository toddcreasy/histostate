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
src/histostate/     package code
tests/              pytest tests, no network by default
scripts/            one-shot scripts, never imported
docs/               long-form docs
```

## Roadmap

- [ ] Step 1: linear probe on NCT-CRC-HE
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

## Train on AWS

`main.nf` runs Stage 3 training on AWS Batch GPU instances, one job per jitter and seed pair.
Requires Nextflow >= 26.04, AWS credentials, the stack in `infra/aws` deployed, and the image
pushed to ECR (Elastic Container Registry); `infra/aws/README.md` covers both. Copy
`.env.example` to `.env` and fill it in.

```bash
set -a; source .env; set +a
nextflow run main.nf -profile aws --jitters 0.3,0.5 --seeds 1,2
```

Checkpoints and logs land in `$AWS_S3_OUTDIR/stage3/`; `pipeline_info/trace.tsv` there records
time and peak memory per run.

## Model licenses

Phikon-v2 uses a custom Owkin license, not a standard open-source one. Read
the model card terms before any commercial use.
