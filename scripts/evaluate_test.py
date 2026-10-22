"""Score a saved Stage 3 CNN on validation and on the final test half, side by side.

The test set (CRC-VAL-HE-7K) comes from patients the model never trained on. It is split in half
(histostate.splits): shifted validation for tuning, and this final test half. Look at the final
half once, after all tuning is done; tuning against it turns it into another validation set.

Run: uv run python scripts/evaluate_test.py [--model models/stage3_cnn.pt] [--device mps]
"""

import argparse
from pathlib import Path

import torch
from medmnist import PathMNIST

from histostate.cnn import CNN
from histostate.softmax import cross_entropy
from histostate.splits import split_test

parser = argparse.ArgumentParser()
parser.add_argument("--model", type=Path, default=Path("models/stage3_cnn.pt"))
parser.add_argument("--device", default="mps", choices=["cpu", "mps"])
args = parser.parse_args()

device = torch.device(args.device)
n_classes = 9
codes = ["ADI", "BACK", "DEB", "LYM", "MUC", "MUS", "NORM", "STR", "TUM"]

checkpoint = torch.load(args.model, map_location=device)
# Checkpoints from before --size existed are 28-pixel models.
size = checkpoint.get("size", 28)
model = CNN(n_classes, size, checkpoint.get("blocks")).to(device)
model.load_state_dict(checkpoint["weights"])
model.eval()
mean, std = checkpoint["mean"].cpu(), checkpoint["std"].cpu()


def load(split):
    data = PathMNIST(split=split, download=True, size=None if size == 28 else size)
    # Same scaling as training, using the training set's mean and spread saved with the model.
    x = (torch.from_numpy(data.imgs).float() / 255 - mean) / std
    x = x.permute(0, 3, 1, 2).contiguous().to(device)
    y = torch.from_numpy(data.labels).long().squeeze(1).to(device)
    if split == "test":
        _, final_idx = split_test(y.cpu())
        return x[final_idx.to(device)], y[final_idx.to(device)]
    return x, y


def score(x, y):
    with torch.no_grad():
        logits = torch.cat([model(x[i : i + 2048]) for i in range(0, len(x), 2048)])
    predicted = logits.argmax(dim=1)
    confusion = torch.bincount(y * n_classes + predicted, minlength=n_classes**2)
    confusion = confusion.reshape(n_classes, n_classes).cpu()
    accuracy = (predicted == y).float().mean().item()
    return cross_entropy(logits, y).item(), accuracy, confusion


results = {}
for split in ["val", "test"]:
    x, y = load(split)
    loss, accuracy, confusion = score(x, y)
    majority = torch.bincount(y, minlength=n_classes).max().item() / len(y)
    results[split] = confusion
    print(
        f"{split:<5} n={len(y):>6}  loss {loss:.4f}  accuracy {accuracy:.1%}  "
        f"(majority-class baseline {majority:.1%})"
    )

print("\nrecall by class")
print("       " + "".join(f"{c:>6}" for c in codes))
for split, confusion in results.items():
    recall = confusion.diag() / confusion.sum(dim=1)
    print(f"{split:<6} " + "".join(f"{r:>6.0%}" for r in recall.tolist()))

confusion = results["test"]
recall = confusion.diag() / confusion.sum(dim=1)
precision = confusion.diag() / confusion.sum(dim=0)
print("\nconfusion matrix (final test half), rows = true, columns = predicted")
print("true\\pred " + "".join(f"{c:>6}" for c in codes) + "  recall")
for i, code in enumerate(codes):
    row = "".join(f"{n:>6}" for n in confusion[i].tolist())
    print(f"{code:<9} {row}  {recall[i]:>6.1%}")
print("precision " + "".join(f"{p:>6.0%}" for p in precision.tolist()))
