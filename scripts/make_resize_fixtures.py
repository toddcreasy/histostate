"""Write frontend/src/lib/resize.fixtures.json.gz: images of assorted sizes and what Pillow's
bicubic resize to 64x64 makes of them, the step histostate.ask.predict runs on an upload.
frontend/src/lib/resize.test.ts checks the website's resize against these byte for byte.

Inputs are PathMNIST test tiles blown up to each size with nearest-neighbor (so they keep real
tissue texture), plus a crop of a README figure. Rerun when Pillow's resize might have changed.

    uv run python scripts/make_resize_fixtures.py
"""

import base64
import gzip
import json
import logging
from pathlib import Path

import numpy as np
from medmnist import PathMNIST
from PIL import Image

logger = logging.getLogger(__name__)

OUT = Path("frontend/src/lib/resize.fixtures.json.gz")
TARGET = 64
# Shrink a little, a lot, not square, grow, and the identity.
SIZES = [(65, 65), (100, 100), (128, 128), (224, 224), (300, 300), (150, 90), (97, 211), (50, 50)]
SIZES += [(64, 64)]


def case(name: str, image: Image.Image) -> dict:
    rgb = image.convert("RGB")
    resized = rgb.resize((TARGET, TARGET), Image.Resampling.BICUBIC)
    return {
        "name": name,
        "width": rgb.width,
        "height": rgb.height,
        "input": base64.b64encode(np.asarray(rgb).tobytes()).decode(),
        "output": base64.b64encode(np.asarray(resized).tobytes()).decode(),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    test = PathMNIST(split="test", size=64, download=True)
    cases = []
    for i, (w, h) in enumerate(SIZES):
        tile = Image.fromarray(test.imgs[i * 97]).resize((w, h), Image.Resampling.NEAREST)
        cases.append(case(f"tile {i * 97} at {w}x{h}", tile))
    figure = Image.open("docs/images/tissue_classes.png").convert("RGB")
    cases.append(case("README figure crop 257x183", figure.crop((10, 10, 267, 193))))

    with gzip.open(OUT, "wt") as f:
        json.dump(cases, f)
    logger.info("wrote %s: %d cases, %.0f KB", OUT, len(cases), OUT.stat().st_size / 1024)


if __name__ == "__main__":
    main()
