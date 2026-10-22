import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import torch
from medmnist import INFO
from PIL import Image

from histostate.cnn import CNN
from histostate.softmax import softmax

logger = logging.getLogger(__name__)

TISSUES = list(INFO["pathmnist"]["label"].values())


def predict(image_path: Path, model_path: Path) -> torch.Tensor:
    checkpoint = torch.load(model_path, map_location="cpu")
    # Checkpoints from before --size existed are 28-pixel models.
    size = checkpoint.get("size", 28)
    model = CNN(len(TISSUES), size, checkpoint.get("blocks"))
    model.load_state_dict(checkpoint["weights"])
    model.eval()

    # PathMNIST tiles were shrunk from 224x224; the model has only ever seen tiles of its own size.
    image = Image.open(image_path).convert("RGB").resize((size, size), Image.Resampling.BICUBIC)
    # Same scaling as training: 0-1, then the training set's mean and spread, then channels first.
    x = torch.from_numpy(np.array(image)).float() / 255
    x = ((x - checkpoint["mean"].cpu()) / checkpoint["std"].cpu()).permute(2, 0, 1)

    with torch.no_grad():
        return softmax(model(x.unsqueeze(0)))[0]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="histostate")
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser("ask", help="name the tissue type in an H&E image")
    ask.add_argument("image", type=Path)
    ask.add_argument("--model", type=Path, default=Path("models/stage3_cnn.pt"))
    ask.add_argument("--top", type=int, default=3)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    if not args.image.is_file():
        parser.error(f"image not found: {args.image}")
    if not args.model.is_file():
        parser.error(f"model not found: {args.model} (train one with scripts/stage3_cnn.py)")

    probabilities = predict(args.image, args.model)
    ranked = probabilities.argsort(descending=True)[: args.top]
    logger.info("%s (%.0f%% confident)", TISSUES[ranked[0]], 100 * probabilities[ranked[0]])
    for i in ranked[1:]:
        logger.info("  then %-38s %.0f%%", TISSUES[i], 100 * probabilities[i])
