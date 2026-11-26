"""Export the trained CNN to ONNX for the website, then check it against PyTorch.

The ONNX graph takes raw RGB pixels as a browser canvas gives them (batch x 64 x 64 x 3, values
0 to 255) and returns the 9 class probabilities. Scaling, the training mean and spread, and
softmax are inside the graph, the same steps as histostate.ask.predict, so the browser only has
to resize the image.

The check runs every PathMNIST test tile through both and reports the largest probability
difference and how many top answers disagree.

    uv run --group site python scripts/export_onnx.py
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from medmnist import PathMNIST
from torch import nn

from histostate.ask import TISSUES
from histostate.cnn import CNN
from histostate.softmax import softmax

logger = logging.getLogger(__name__)


class PixelsToProbabilities(nn.Module):
    def __init__(self, model: CNN, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.model = model
        self.register_buffer("mean", mean)
        self.register_buffer("std", std)

    def forward(self, pixels: torch.Tensor) -> torch.Tensor:
        x = (pixels / 255 - self.mean) / self.std
        return softmax(self.model(x.permute(0, 3, 1, 2)))


def load(model_path: Path) -> tuple[PixelsToProbabilities, int]:
    checkpoint = torch.load(model_path, map_location="cpu")
    size = checkpoint.get("size", 28)
    model = CNN(len(TISSUES), size, checkpoint.get("blocks"))
    model.load_state_dict(checkpoint["weights"])
    wrapped = PixelsToProbabilities(model, checkpoint["mean"].cpu(), checkpoint["std"].cpu())
    return wrapped.eval(), size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=Path("models/stage3_cnn.pt"))
    parser.add_argument("--out", type=Path, default=Path("models/stage3_cnn.onnx"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    wrapped, size = load(args.model)
    # A batch of 2: the exporter treats an example batch of 1 as fixed, not dynamic.
    example = torch.zeros(2, size, size, 3)
    torch.onnx.export(
        wrapped,
        (example,),
        args.out,
        input_names=["pixels"],
        output_names=["probabilities"],
        dynamic_shapes={"pixels": {0: torch.export.Dim.DYNAMIC}},
        dynamo=True,
        external_data=False,
    )
    logger.info("wrote %s (%.0f KB)", args.out, args.out.stat().st_size / 1024)

    test = PathMNIST(split="test", size=size, download=True)
    pixels = torch.from_numpy(test.imgs).float()
    with torch.no_grad():
        expected = wrapped(pixels).numpy()
    session = ort.InferenceSession(args.out, providers=["CPUExecutionProvider"])
    got = session.run(None, {"pixels": pixels.numpy()})[0]

    disagree = int((expected.argmax(1) != got.argmax(1)).sum())
    accuracy = float((got.argmax(1) == test.labels[:, 0]).mean())
    logger.info("test tiles: %d", len(pixels))
    logger.info("largest probability difference: %.2e", float(np.abs(expected - got).max()))
    logger.info("top answers that disagree: %d", disagree)
    logger.info("ONNX accuracy on the full test set: %.1f%%", 100 * accuracy)
    if disagree:
        raise SystemExit("ONNX and PyTorch disagree")


if __name__ == "__main__":
    main()
