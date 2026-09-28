"""Extract tile embeddings with a frozen pathology foundation model.

The backbone is never trained here. Each 224px H&E tile goes in, and one
1024-dim vector (the CLS token from Phikon-v2) comes out. Everything
downstream trains on these cached vectors, which is fast and cheap.
"""

from collections.abc import Sequence
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

from histostate.device import get_device

DEFAULT_BACKBONE = "owkin/phikon-v2"


class TileEncoder:
    """Wraps a Hugging Face vision backbone for batched tile embedding."""

    def __init__(
        self,
        model_name: str = DEFAULT_BACKBONE,
        device: torch.device | None = None,
    ) -> None:
        self.device = device or get_device()
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    @torch.inference_mode()
    def encode(self, images: Sequence[Image.Image]) -> torch.Tensor:
        """Return a (batch, dim) tensor of CLS embeddings on the CPU."""
        rgb = [img.convert("RGB") for img in images]
        inputs = self.processor(images=rgb, return_tensors="pt").to(self.device)
        outputs = self.model(**inputs)
        return outputs.last_hidden_state[:, 0, :].float().cpu()


def extract_dataset_features(
    encoder: TileEncoder,
    dataset,
    batch_size: int = 32,
    image_key: str = "image",
    label_key: str = "label",
) -> tuple[torch.Tensor, torch.Tensor]:
    """Embed every row of a Hugging Face image dataset.

    Returns (features, labels) as tensors of shape (n, dim) and (n,).
    """
    feats, labels = [], []
    for start in range(0, len(dataset), batch_size):
        batch = dataset[start : start + batch_size]
        feats.append(encoder.encode(batch[image_key]))
        labels.append(torch.as_tensor(batch[label_key]))
        done = min(start + batch_size, len(dataset))
        print(f"  embedded {done}/{len(dataset)}", end="\r")
    print()
    return torch.cat(feats), torch.cat(labels)


def load_or_extract(
    cache_path: Path,
    encoder_factory,
    dataset,
    batch_size: int = 32,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Load cached embeddings if present, otherwise compute and save them."""
    if cache_path.exists():
        blob = torch.load(cache_path)
        return blob["features"], blob["labels"]
    feats, labels = extract_dataset_features(
        encoder_factory(), dataset, batch_size=batch_size
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"features": feats, "labels": labels}, cache_path)
    return feats, labels
