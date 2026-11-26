"""Upload the demo app to the Hugging Face Space as a Docker Space.

Stages only what app/Dockerfile needs in a temporary folder, then uploads it. Needs a token saved
with `hf auth login` and the released model in models/stage3_cnn.pt.

    uv run --with huggingface_hub python scripts/deploy_space.py
    uv run --with huggingface_hub python scripts/deploy_space.py --stage-only build/space
"""

import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "stage3_cnn.pt"
# SHA-256 of stage3_cnn.pt in the v0.1.0 GitHub release.
MODEL_SHA256 = "c93d8005350c91b2d216b8a30f348cc8e40d25e25c477a46caaa0477d6ad27f2"

# Spaces read their settings from the YAML block at the top of README.md.
SPACE_README = """---
title: histostate
emoji: 🔬
colorFrom: pink
colorTo: purple
sdk: docker
app_port: 7860
license: apache-2.0
short_description: Name the tissue in a colorectal H&E tile, CNN from scratch
---

# histostate

A small CNN (convolutional neural network) built and trained from scratch in PyTorch that names
the tissue type in a colorectal H&E tile. Source, walkthrough, and results:
https://github.com/toddcreasy/histostate

A learning project, not a medical device. Not for clinical or diagnostic use.
"""


def stage(target: Path) -> None:
    digest = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    if digest != MODEL_SHA256:
        raise SystemExit(f"{MODEL} is not the v0.1.0 release model (sha256 {digest})")

    skip = shutil.ignore_patterns("__pycache__", "*.pyc", "Dockerfile", "README.md")
    for name in ("pyproject.toml", "uv.lock", "LICENSE"):
        shutil.copy2(ROOT / name, target / name)
    shutil.copytree(ROOT / "src", target / "src", ignore=skip)
    shutil.copytree(ROOT / "app", target / "app", ignore=skip)
    (target / "models").mkdir()
    shutil.copy2(MODEL, target / "models" / MODEL.name)
    shutil.copy2(ROOT / "app" / "Dockerfile", target / "Dockerfile")
    (target / "README.md").write_text(SPACE_README)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--space", default="tcreasypb/histostate")
    parser.add_argument("--stage-only", type=Path, help="write the build context here; no upload")
    args = parser.parse_args()

    if args.stage_only:
        args.stage_only.mkdir(parents=True)
        stage(args.stage_only)
        print(f"staged in {args.stage_only}")
        return

    api = HfApi()
    api.create_repo(args.space, repo_type="space", space_sdk="docker", exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        stage(Path(folder))
        api.upload_folder(
            repo_id=args.space,
            repo_type="space",
            folder_path=folder,
            commit_message="Deploy from histostate",
            delete_patterns="*",
        )
    print(f"uploaded to https://huggingface.co/spaces/{args.space}")


if __name__ == "__main__":
    main()
