# histostate

Name the tissue type in a colorectal H&E (hematoxylin and eosin) image with a small CNN
(convolutional neural network) built and trained from scratch in PyTorch. No pretrained weights,
no trainer libraries: the point is to learn every piece, from gradient descent up.

[docs/walkthrough.md](docs/walkthrough.md) tells the story stage by stage: what each step
taught, the numbers it produced, and what went wrong.

A learning project, not a medical device. Not for clinical or diagnostic use.

```bash
uv run histostate ask tile.png
```

## Data

[PathMNIST](https://medmnist.com/) from MedMNIST: about 107,000 colorectal H&E tiles at 28x28
pixels (also published at 64x64), 9 tissue classes (adipose, background, debris, lymphocytes,
mucus, smooth muscle, normal mucosa, stroma, tumor). It downloads on first use.

The official test set (CRC-VAL-HE-7K) comes from a different clinical center than train and
validation (NCT-CRC-HE-100K), so it shows a color and staining shift. `src/histostate/splits.py`
cuts it into two stratified halves: shifted validation, used for tuning, and final test, scored once
per model choice.

## Stages

Each stage is one script in `scripts/`, building on the last.

| Stage | Script | Validation accuracy |
|---|---|---|
| Warm-up: fit a line with hand-written gradient descent | `warmup_fit_line.py` | n/a |
| 1: logistic regression on pixels | `stage1_logreg.py` | about 47% |
| 2: MLP (multilayer perceptron) | `stage2_mlp.py` | about 66% |
| 3: CNN at 28 pixels, 2 conv blocks, 47,625 weights | `stage3_cnn.py --size 28` | 95.1% |
| 3: CNN at 64 pixels, 3 conv blocks, 93,193 weights | `stage3_cnn.py` | 97.8% |

Stage 3 trains with SGD (stochastic gradient descent), gradient clipping, cosine learning-rate
decay, flip and rotate augmentation, and color jitter (0.3). It keeps the epoch with the best
validation accuracy.

At 28 pixels, a third conv block adds about 1 point on validation and nothing on shifted
validation; going to 64 pixels adds about 3 points there. Fiber shape is what separates stroma
from smooth muscle, and most of it is gone at 28 pixels. `scripts/inspect_cnn.py` shows the
filters and activation maps behind this.

Final model (64 pixels, seed 0): 94.0% on shifted validation and 94.7% on final test
(`scripts/evaluate_test.py`, 2026-10-22). Stroma (75% recall) and smooth muscle (83%) are still
its main confusion. The 28-pixel model scored 91.4% on the same final test half, with stroma at 63%
and muscle at 76%.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run python scripts/stage3_cnn.py --save models/stage3_cnn.pt
```

Picks a CUDA (NVIDIA) GPU, then Apple Silicon (MPS, Metal Performance Shaders), then CPU; override
with `--device`. A laptop is enough for every stage.

## Train on AWS (optional)

Not needed to follow along, and it bills your AWS account. `main.nf` runs Stage 3 training on AWS
Batch, one job per jitter and seed pair, on GPU instances (`-profile aws,gpu`) or CPU instances
(`-profile aws,cpu`). Requires Nextflow >= 26.04, AWS credentials, the stack in `infra/aws`
deployed, and the image pushed to ECR (Elastic Container Registry); `infra/aws/README.md` covers
both. Copy `.env.example` to `.env` and fill it in.

```bash
set -a; source .env; set +a
nextflow run main.nf -profile aws,gpu --jitters 0.3,0.5 --seeds 1,2
```

Checkpoints and logs land in `$AWS_S3_OUTDIR/stage3/`; `pipeline_info/trace.tsv` there records
time and peak memory per run.

## Layout

```
src/histostate/     model, augmentation, splits, and the ask command
tests/              pytest tests, no network by default
scripts/            one training or evaluation script per stage
infra/aws/          CDK stack for AWS Batch
docs/               the walkthrough
```

## Data license and citation

PathMNIST is licensed CC BY 4.0. If you use it, cite MedMNIST and the source dataset:

- Yang, J., et al. "MedMNIST v2: A large-scale lightweight benchmark for 2D and 3D biomedical
  image classification." Scientific Data, 2023.
- Kather, J. N., et al. "Predicting survival from colorectal cancer histology slides using deep
  learning: A retrospective multicenter study." PLOS Medicine, 2019.

Code is Apache-2.0 (`LICENSE`).
