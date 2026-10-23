# Software

Every tool this project uses, what it does here, why it was picked, and what was passed over.

## Machine learning

| Tool | What it is | What it does here | Why this one | Passed over, and why |
|---|---|---|---|---|
| Python 3.14 | Programming language | Everything outside the AWS console | The language nearly all ML tooling is written for | |
| PyTorch 2.14 | Tensor library with automatic gradients (autograd) | Builds the models, computes gradients, runs training on Apple GPUs (MPS), NVIDIA GPUs (CUDA), or CPU | You write the training loop yourself, which was the point. One codebase runs on a Mac and on AWS GPUs | **TensorFlow/Keras:** `model.fit()` hides the loop. **JAX:** a more functional style to learn on top of ML itself |
| MedMNIST | Python package for a set of small medical imaging datasets | Downloads PathMNIST as NumPy arrays, already split into train, validation, and test, at 28 or 64 pixels | Clean labels and a fixed split, so time goes into the model, not data wrangling. Small enough to train in minutes | **Raw NCT-CRC-HE-100K at 224 pixels:** bigger downloads and slower training; 64 pixels was enough to see the effect of resolution |
| NumPy | Array library | Holds the downloaded images; reads uploaded images in `histostate ask` | MedMNIST returns NumPy arrays | |
| Pillow | Image library | Opens and resizes images in `histostate ask`; draws the filter, activation, and README figures | Already a dependency, and enough for grids of tiles | **matplotlib:** charts weren't needed, so it would have been an extra dependency for no gain |

Not used on purpose:

- **Training frameworks** (PyTorch Lightning, fastai, Hugging Face Trainer). They wrap the
  training loop, gradient steps, and checkpointing, which are exactly the parts this project set
  out to write by hand.
- **Pretrained models** (Owkin's Phikon-v2 was the original plan). A frozen foundation model does
  the learning for you. Good for results, bad for understanding.

## Development

| Tool | What it is | What it does here | Why this one | Passed over, and why |
|---|---|---|---|---|
| uv | Python package and environment manager | Installs dependencies, pins exact versions in `uv.lock`, runs every command (`uv run`) | One fast tool, and the lockfile makes every machine and the AWS image install the same versions | **pip + venv:** no lockfile by default. **Poetry:** slower, and uv covers the same ground. **Conda:** heavy, and nothing here needs non-Python packages |
| `uv_build` | Build backend | Turns `src/histostate` into an installable package | Native to uv and the src layout, no extra config | **setuptools:** more config for the same result |
| ruff | Linter and formatter | Checks style and common bugs, formats code | One tool, runs in milliseconds | **flake8 + black + isort:** three tools for the same job |
| pytest | Test runner | Checks hand-written math against PyTorch (softmax, gradients, convolutions), plus augmentation, splits, and the `ask` command | The standard for Python | **unittest:** more boilerplate |
| pre-commit | Git hook manager | Runs ruff before every commit | Catches problems before they reach CI | |
| GitHub Actions | CI (continuous integration) | Runs `uv sync --locked`, ruff, and pytest on every pull request | Lives next to the code; free for a personal project | |
| Claude Code | AI coding assistant | Tutor: explained each concept before code changed and interpreted each result (see `CLAUDE.md`) | The learning goal needed explanations at every step, not just code | |

## AWS training (optional)

| Tool | What it is | What it does here | Why this one | Passed over, and why |
|---|---|---|---|---|
| Docker | Container builder | Packages the code and locked dependencies into one Linux image for AWS | AWS Batch runs containers. The PyTorch wheels in `uv.lock` bundle the CUDA libraries, so a plain `python:3.14-slim` base works | **NVIDIA CUDA base images:** several GB larger, and the wheels already carry CUDA |
| Nextflow | Workflow manager | Turns `--jitters 0.3,0.5 --seeds 1,2` into four Batch jobs, moves files through S3, retries jobs when Spot takes an instance back, records time and memory per job | Same tool as my other AWS pipelines, with a mature AWS Batch executor | **A shell loop of `aws batch submit-job`:** would mean hand-writing file staging, retries, and tracking. **Snakemake:** would work too, but Nextflow was already set up |
| AWS Batch | Managed job queue | Starts an EC2 instance per job, runs the container, scales to zero when idle | Pay only while jobs run; GPU and CPU queues side by side | **SageMaker training jobs:** another ML-specific API to learn, and different from my other pipelines. **One long-running EC2 instance:** billed while idle and managed by hand |
| EC2 | Virtual machines | g4dn.xlarge (NVIDIA T4) and g5.xlarge (A10G) for GPU jobs; c6i, c7i, m6i for CPU jobs | Smallest GPU instances; a T4 trained 64-pixel models at about 10 s per epoch | **Spot only:** cheaper, but AWS took back both GPU instances mid-run once, so the 64-pixel runs used on-demand |
| ECR | Container registry | Stores the training image that Batch pulls | Same account and region as Batch, which pulls with its own IAM (Identity and Access Management) role | **Docker Hub:** a separate account, and the image would need to stay private |
| S3 | Object storage | Nextflow's working files (deleted after 30 days) and the final checkpoints and logs | Batch jobs and the laptop both read and write it | |
| AWS CDK (Python) | Infrastructure as code | Defines the compute environments, job queues, launch templates, and S3 bucket in `infra/aws`, with tests | Infrastructure in the same language as the project, deployed with one command | **The AWS console:** not repeatable. **Terraform:** a second language. **Raw CloudFormation:** long YAML for the same result |
