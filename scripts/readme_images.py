"""Draw the PathMNIST example figures used in the README into docs/images/.

- tissue_classes.png: three 64-pixel tiles of each of the 9 tissue classes
- staining_shift.png: smooth muscle and stroma from the training set next to the test set
- resolution.png: the same smooth muscle and stroma tiles at 28 and 64 pixels

Run: uv run python scripts/readme_images.py [--out docs/images]
"""

import argparse
from pathlib import Path

import numpy as np
from medmnist import PathMNIST
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path, default=Path("docs/images"))
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)

NAMES = ["Adipose", "Background", "Debris", "Lymphocytes", "Mucus", "Smooth muscle",
         "Normal mucosa", "Stroma", "Tumor"]  # fmt: skip
MUS, STR = 5, 7
TILE, GAP, LABEL = 128, 6, 28  # every tile is drawn 128 pixels wide
font = ImageFont.load_default(size=16)
rng = np.random.default_rng(0)

train64 = PathMNIST(split="train", download=True, size=64)
test64 = PathMNIST(split="test", download=True, size=64)
train28 = PathMNIST(split="train", download=True)  # same tiles, same order, at 28 pixels


def pick(data, label, n):
    return rng.choice(np.flatnonzero(data.labels[:, 0] == label), n, replace=False)


def tile(img):
    return Image.fromarray(img).resize((TILE, TILE), Image.Resampling.NEAREST)


def sheet(columns, rows, header_rows=1):
    width = columns * (TILE + GAP) - GAP + 160
    height = header_rows * LABEL + rows * (TILE + GAP) - GAP
    return Image.new("RGB", (width, height), "white")


def paste(canvas, img, row, col, header_rows=1):
    canvas.paste(tile(img), (160 + col * (TILE + GAP), header_rows * LABEL + row * (TILE + GAP)))


def row_label(canvas, text, row, header_rows=1):
    y = header_rows * LABEL + row * (TILE + GAP) + TILE // 2 - 8
    ImageDraw.Draw(canvas).text((4, y), text, fill="black", font=font)


# Nine classes across, three examples down.
canvas = Image.new("RGB", (9 * (TILE + GAP) - GAP, LABEL + 3 * (TILE + GAP) - GAP), "white")
draw = ImageDraw.Draw(canvas)
for c, name in enumerate(NAMES):
    x = c * (TILE + GAP)
    draw.text((x + 2, 4), name, fill="black", font=font)
    for r, i in enumerate(pick(train64, c, 3)):
        canvas.paste(tile(train64.imgs[i]), (x, LABEL + r * (TILE + GAP)))
canvas.save(args.out / "tissue_classes.png")

# Four training tiles, then four test tiles, for each of the two classes the model mixes up.
canvas = sheet(9, 2)
draw = ImageDraw.Draw(canvas)
draw.text((160, 4), "Training set (NCT-CRC-HE-100K)", fill="black", font=font)
draw.text((160 + 5 * (TILE + GAP), 4), "Test set (CRC-VAL-HE-7K)", fill="black", font=font)
for r, label in enumerate([MUS, STR]):
    row_label(canvas, NAMES[label], r)
    for c, i in enumerate(pick(train64, label, 4)):
        paste(canvas, train64.imgs[i], r, c)
    for c, i in enumerate(pick(test64, label, 4)):
        paste(canvas, test64.imgs[i], r, c + 5)
canvas.save(args.out / "staining_shift.png")

# Three tiles per class, each shown at 28 then 64 pixels, both drawn at the same size.
canvas = sheet(8, 2)
draw = ImageDraw.Draw(canvas)
for k in range(3):
    x = 160 + k * 3 * (TILE + GAP)
    draw.text((x, 4), "28 px", fill="black", font=font)
    draw.text((x + TILE + GAP, 4), "64 px", fill="black", font=font)
for r, label in enumerate([MUS, STR]):
    row_label(canvas, NAMES[label], r)
    for k, i in enumerate(pick(train64, label, 3)):
        paste(canvas, train28.imgs[i], r, 3 * k)
        paste(canvas, train64.imgs[i], r, 3 * k + 1)
canvas.save(args.out / "resolution.png")

for name in ["tissue_classes", "staining_shift", "resolution"]:
    print(f"saved {args.out / name}.png")
