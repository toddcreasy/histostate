"""Stage 1: logistic regression on PathMNIST pixels, with hand-written softmax and cross-entropy.

Run: uv run python scripts/stage1_logreg.py [--lr 0.003] [--epochs 5] [--batch-size 128]
                                            [--device cpu]
"""

import argparse
import time

import torch
from medmnist import PathMNIST

from histostate.softmax import cross_entropy

parser = argparse.ArgumentParser()
parser.add_argument("--lr", type=float, default=0.003)
parser.add_argument("--epochs", type=int, default=5)
parser.add_argument("--batch-size", type=int, default=128)
parser.add_argument("--device", default="cpu", choices=["cpu", "mps"])
args = parser.parse_args()

torch.manual_seed(0)
device = torch.device(args.device)

train = PathMNIST(split="train", download=True)
val = PathMNIST(split="val", download=True)

# uint8 0-255, shape (N, 28, 28, 3) -> float 0-1
x_train = torch.from_numpy(train.imgs).float() / 255
x_val = torch.from_numpy(val.imgs).float() / 255
y_train = torch.from_numpy(train.labels).long().squeeze(1)
y_val = torch.from_numpy(val.labels).long().squeeze(1)

# Per-channel mean and spread from the training set only, applied to both splits.
mean = x_train.mean(dim=(0, 1, 2))
std = x_train.std(dim=(0, 1, 2))
x_train = ((x_train - mean) / std).reshape(len(x_train), -1).to(device)
x_val = ((x_val - mean) / std).reshape(len(x_val), -1).to(device)
y_train, y_val = y_train.to(device), y_val.to(device)

n_features, n_classes = x_train.shape[1], 9
W = torch.zeros(n_features, n_classes, device=device, requires_grad=True)
b = torch.zeros(n_classes, device=device, requires_grad=True)
optimizer = torch.optim.SGD([W, b], lr=args.lr)
print(f"{n_features} pixels x {n_classes} classes = {W.numel() + b.numel()} weights")


def evaluate(x, y):
    with torch.no_grad():
        logits = x @ W + b
        return cross_entropy(logits, y).item(), (logits.argmax(dim=1) == y).float().mean().item()


val_loss, val_acc = evaluate(x_val, y_val)
print(f"before training: val loss {val_loss:.4f} (expect ln 9 = 2.1972), val acc {val_acc:.1%}")

for epoch in range(1, args.epochs + 1):
    start = time.perf_counter()
    order = torch.randperm(len(x_train), device=device)
    total_loss = 0.0
    for i in range(0, len(order), args.batch_size):
        batch = order[i : i + args.batch_size]
        loss = cross_entropy(x_train[batch] @ W + b, y_train[batch])
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
        total_loss += loss.item() * len(batch)

    train_loss = total_loss / len(x_train)
    val_loss, val_acc = evaluate(x_val, y_val)
    elapsed = time.perf_counter() - start
    print(
        f"epoch {epoch}  train loss {train_loss:.4f}  val loss {val_loss:.4f}  "
        f"val acc {val_acc:.1%}  ({elapsed:.1f}s)"
    )

# Confusion matrix on validation: row = true class, column = predicted class.
codes = ["ADI", "BACK", "DEB", "LYM", "MUC", "MUS", "NORM", "STR", "TUM"]
with torch.no_grad():
    predicted = (x_val @ W + b).argmax(dim=1)
confusion = torch.bincount(y_val * n_classes + predicted, minlength=n_classes**2)
confusion = confusion.reshape(n_classes, n_classes).cpu()
recall = confusion.diag() / confusion.sum(dim=1)
precision = confusion.diag() / confusion.sum(dim=0)

print("\nconfusion matrix (validation), rows = true, columns = predicted")
print("true\\pred " + "".join(f"{c:>6}" for c in codes) + "  recall")
for i, code in enumerate(codes):
    row = "".join(f"{n:>6}" for n in confusion[i].tolist())
    print(f"{code:<9} {row}  {recall[i]:>6.1%}")
print("precision " + "".join(f"{p:>6.0%}" for p in precision.tolist()))
