"""Stage 2: a one-hidden-layer MLP on PathMNIST pixels, weights written by hand.

Run: uv run python scripts/stage2_mlp.py [--lr 0.003] [--epochs 15] [--hidden 256]
                                         [--batch-size 128] [--device cpu]
"""

import argparse
import math
import time

import torch
from medmnist import PathMNIST

from histostate.softmax import cross_entropy

parser = argparse.ArgumentParser()
parser.add_argument("--lr", type=float, default=0.003)
parser.add_argument("--epochs", type=int, default=15)
parser.add_argument("--hidden", type=int, default=256)
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

# He initialization: random, scaled by sqrt(2 / inputs) so values keep a steady size per layer.
# Starting at zero would make every hidden unit identical forever.
W1 = torch.randn(n_features, args.hidden, device=device) * math.sqrt(2 / n_features)
W2 = torch.randn(args.hidden, n_classes, device=device) * math.sqrt(2 / args.hidden)
W1.requires_grad_()
W2.requires_grad_()
b1 = torch.zeros(args.hidden, device=device, requires_grad=True)
b2 = torch.zeros(n_classes, device=device, requires_grad=True)
params = [W1, b1, W2, b2]
optimizer = torch.optim.SGD(params, lr=args.lr)
print(
    f"{n_features} pixels -> {args.hidden} hidden -> {n_classes} classes = "
    f"{sum(p.numel() for p in params)} weights"
)


def model(x):
    hidden = (x @ W1 + b1).clamp(min=0)  # ReLU: negatives become 0
    return hidden @ W2 + b2


def evaluate(x, y):
    with torch.no_grad():
        logits = model(x)
        return cross_entropy(logits, y).item(), (logits.argmax(dim=1) == y).float().mean().item()


val_loss, val_acc = evaluate(x_val, y_val)
print(f"before training: val loss {val_loss:.4f} (ln 9 = 2.1972), val acc {val_acc:.1%}")

for epoch in range(1, args.epochs + 1):
    start = time.perf_counter()
    order = torch.randperm(len(x_train), device=device)
    for i in range(0, len(order), args.batch_size):
        batch = order[i : i + args.batch_size]
        loss = cross_entropy(model(x_train[batch]), y_train[batch])
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
    elapsed = time.perf_counter() - start

    # Train metrics use the end-of-epoch weights so they compare fairly with validation.
    train_loss, train_acc = evaluate(x_train, y_train)
    val_loss, val_acc = evaluate(x_val, y_val)
    print(
        f"epoch {epoch:2d}  train loss {train_loss:.4f}  acc {train_acc:.1%}  |  "
        f"val loss {val_loss:.4f}  acc {val_acc:.1%}  ({elapsed:.1f}s)"
    )

# Confusion matrix on validation: row = true class, column = predicted class.
codes = ["ADI", "BACK", "DEB", "LYM", "MUC", "MUS", "NORM", "STR", "TUM"]
with torch.no_grad():
    predicted = model(x_val).argmax(dim=1)
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
