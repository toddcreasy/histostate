# histostate

Name the tissue type in a colorectal H&E (hematoxylin and eosin) image with a small CNN
(convolutional neural network) built and trained from scratch in PyTorch. No pretrained weights,
no trainer libraries: the point is to learn every piece, from gradient descent up.

```bash
uv run histostate ask tile.png
```

## Data

[PathMNIST](https://medmnist.com/) from MedMNIST: about 107,000 colorectal H&E tiles at 28x28
pixels, 9 tissue classes (adipose, background, debris, lymphocytes, mucus, smooth muscle, normal
mucosa, stroma, tumor). It downloads on first use.

The official test set comes from a separate set of slides (CRC-VAL-HE-7K) than train and
validation, so it shows a color and staining shift. `src/histostate/splits.py` cuts it into two
stratified halves: shifted validation, used for tuning, and final test, scored once.

## Stages

Each stage is one script in `scripts/`, building on the last.

| Stage | Script | Validation accuracy |
|---|---|---|
| Warm-up: fit a line with hand-written gradient descent | `warmup_fit_line.py` | n/a |
| 1: logistic regression on pixels | `stage1_logreg.py` | about 47% |
| 2: MLP (multilayer perceptron) | `stage2_mlp.py` | about 66% |
| 3: CNN, 47,625 weights | `stage3_cnn.py` | 95.1% |

Stage 3 trains with SGD (stochastic gradient descent), gradient clipping, cosine learning-rate
decay, flip and rotate augmentation, and color jitter (0.3). It keeps the epoch with the best
validation accuracy.

Final model: 90.3% on shifted validation and 91.4% on final test (scored once, 2026-10-22,
`scripts/evaluate_test.py`). Stroma (63% recall) and smooth muscle (76%) are its main confusion.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run python scripts/stage3_cnn.py --save models/stage3_cnn.pt
```

Runs on CUDA, Apple Silicon (MPS, Metal Performance Shaders), or CPU; pick with `--device`.

## Train on AWS

`main.nf` runs Stage 3 training on AWS Batch, one job per jitter and seed pair, on GPU
instances (`-profile aws,gpu`) or CPU instances (`-profile aws,cpu`).
Requires Nextflow >= 26.04, AWS credentials, the stack in `infra/aws` deployed, and the image
pushed to ECR (Elastic Container Registry); `infra/aws/README.md` covers both. Copy
`.env.example` to `.env` and fill it in.

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
docs/               long-form docs
```
