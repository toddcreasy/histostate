"""Look inside a saved Stage 3 CNN: its first-layer filters, and what each layer sees in a tile.

Writes PNGs to --out:
- conv1_filters.png: the 32 learned 3x3 color filters, enlarged
- tile_<name>.png: one shifted-validation tile, then its 32 conv1 maps, then its 64 conv2 maps
  (brighter = filter fired harder); one stroma and one muscle tile the model got right, and one
  stroma tile it called muscle
- channel<N>_top20.png: the 20 tiles that make the strongest stroma/muscle separator fire hardest
Prints the conv2 channels whose average response differs most between stroma and muscle, and for
the strongest one, how it behaves on stroma tiles the model got wrong and how it tracks color.

Run: uv run python scripts/inspect_cnn.py [--model models/stage3_cnn.pt] [--out models/inspect]
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from medmnist import PathMNIST
from PIL import Image

from histostate.cnn import CNN
from histostate.splits import split_test

parser = argparse.ArgumentParser()
parser.add_argument("--model", type=Path, default=Path("models/stage3_cnn.pt"))
parser.add_argument("--out", type=Path, default=Path("models/inspect"))
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)

MUS, STR = 5, 7
checkpoint = torch.load(args.model, map_location="cpu")
model = CNN(9)
model.load_state_dict(checkpoint["weights"])
model.eval()


def grid(maps: torch.Tensor, columns: int, scale: int) -> Image.Image:
    """Lay out (N, H, W) or (N, 3, H, W) maps in a grid, each scaled to its own 0-255 range."""
    if maps.dim() == 3:
        maps = maps.unsqueeze(1).expand(-1, 3, -1, -1)
    low = maps.amin(dim=(1, 2, 3), keepdim=True)
    high = maps.amax(dim=(1, 2, 3), keepdim=True)
    maps = (maps - low) / (high - low).clamp(min=1e-8)
    n, _, h, w = maps.shape
    rows = (n + columns - 1) // columns
    gap = 2
    canvas = np.full((rows * (h * scale + gap), columns * (w * scale + gap), 3), 255, np.uint8)
    for i, m in enumerate(maps):
        tile = (m.permute(1, 2, 0).numpy() * 255).astype(np.uint8).repeat(scale, 0).repeat(scale, 1)
        r, c = divmod(i, columns)
        y, x = r * (h * scale + gap), c * (w * scale + gap)
        canvas[y : y + h * scale, x : x + w * scale] = tile
    return Image.fromarray(canvas)


# Each filter is 3 colors x 3x3 weights. It works on normalized pixels, so its colors show which
# color mix it responds to, not literal stain colors.
filters = model.conv1.weight.detach()
grid(filters, columns=8, scale=12).save(args.out / "conv1_filters.png")
print(f"conv1: {tuple(filters.shape)} weights, saved {args.out / 'conv1_filters.png'}")

test = PathMNIST(split="test", download=True)
y_test = torch.from_numpy(test.labels).long().squeeze(1)
shift_idx, _ = split_test(y_test)
raw = torch.from_numpy(test.imgs)[shift_idx]
y = y_test[shift_idx]
x = ((raw.float() / 255 - checkpoint["mean"]) / checkpoint["std"]).permute(0, 3, 1, 2)

with torch.no_grad():
    a1 = torch.relu(model.conv1(x))  # (N, 32, 28, 28)
    a2 = torch.relu(model.conv2(model.pool(a1)))  # (N, 64, 14, 14)
    predicted = model(x).argmax(dim=1)

picks = {
    "stroma_right": ((y == STR) & (predicted == STR)).nonzero()[0].item(),
    "muscle_right": ((y == MUS) & (predicted == MUS)).nonzero()[0].item(),
    "stroma_called_muscle": ((y == STR) & (predicted == MUS)).nonzero()[0].item(),
}
for name, i in picks.items():
    tile = Image.fromarray(raw[i].numpy()).resize((224, 224), Image.Resampling.NEAREST)
    maps1, maps2 = grid(a1[i], 8, 3), grid(a2[i], 8, 3)
    sheet = Image.new(
        "RGB", (max(224, maps1.width, maps2.width), 224 + maps1.height + maps2.height + 20), "white"
    )
    sheet.paste(tile, (0, 0))
    sheet.paste(maps1, (0, 234))
    sheet.paste(maps2, (0, 244 + maps1.height))
    sheet.save(args.out / f"tile_{name}.png")
    print(f"{name}: shifted-validation tile {i}, saved {args.out / f'tile_{name}.png'}")

# Average each conv2 channel over every stroma and every muscle tile, then rank the gap.
strength = a2.mean(dim=(2, 3))  # (N, 64): how hard each channel fired, averaged over the tile
stroma, muscle = strength[y == STR].mean(dim=0), strength[y == MUS].mean(dim=0)
gap = stroma - muscle
print("\nconv2 channels that separate stroma from muscle (mean response, shifted validation)")
print("channel  stroma  muscle    gap")
for c in gap.abs().argsort(descending=True)[:8].tolist():
    print(f"{c:>7}  {stroma[c]:>6.3f}  {muscle[c]:>6.3f}  {gap[c]:>+6.3f}")
print(f"median |gap| across all 64 channels: {gap.abs().median():.3f}")

# What does the strongest separator respond to? Show the tiles that make it fire hardest.
codes = ["ADI", "BACK", "DEB", "LYM", "MUC", "MUS", "NORM", "STR", "TUM"]
channel = gap.abs().argmax().item()
top = strength[:, channel].argsort(descending=True)[:20]
tiles = raw[top].permute(0, 3, 1, 2).float()
grid(tiles, columns=10, scale=4).save(args.out / f"channel{channel}_top20.png")
print(
    f"\nchannel {channel}: 20 strongest tiles saved to {args.out / f'channel{channel}_top20.png'}"
)
print("their true classes: " + " ".join(codes[c] for c in y[top].tolist()))

# Within stroma only: does the channel fire harder on the tiles the model got wrong, and does it
# track stain color (mean red, green, blue of the tile) rather than structure?
is_stroma = y == STR
s = strength[is_stroma, channel]
wrong = predicted[is_stroma] == MUS
print(f"stroma tiles called stroma: mean {s[~wrong].mean():.3f} (n={(~wrong).sum()})")
print(f"stroma tiles called muscle: mean {s[wrong].mean():.3f} (n={wrong.sum()})")
color = raw[is_stroma].float().mean(dim=(1, 2))  # (n, 3)
for name, values in zip(["red", "green", "blue"], color.T, strict=True):
    r = torch.corrcoef(torch.stack([s, values]))[0, 1]
    print(f"correlation with mean {name:<5} across stroma tiles: {r:+.2f}")
