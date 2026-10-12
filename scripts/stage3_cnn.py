"""Stage 3: a small CNN on PathMNIST, built from nn.Conv2d, nn.MaxPool2d, and nn.Linear.

Run: uv run python scripts/stage3_cnn.py [--lr 0.1] [--epochs 15] [--batch-size 128] [--clip 5.0]
                                         [--augment] [--device mps] [--save models/stage3_cnn.pt]
"""

import argparse
import copy
import time
from pathlib import Path

import torch
from medmnist import PathMNIST

from histostate.augment import flip_rotate
from histostate.cnn import CNN
from histostate.softmax import cross_entropy

parser = argparse.ArgumentParser()
parser.add_argument("--lr", type=float, default=0.1)
parser.add_argument("--epochs", type=int, default=15)
parser.add_argument("--batch-size", type=int, default=128)
parser.add_argument("--clip", type=float, default=5.0)
parser.add_argument("--augment", action="store_true", help="random flips and quarter turns")
parser.add_argument("--device", default="mps", choices=["cpu", "mps"])
parser.add_argument("--save", type=Path, default=Path("models/stage3_cnn.pt"))
args = parser.parse_args()

torch.manual_seed(0)
device = torch.device(args.device)
# Augmentation draws from its own generator so batch order matches a run without --augment.
augment_generator = torch.Generator(device=device).manual_seed(1)

train = PathMNIST(split="train", download=True)
val = PathMNIST(split="val", download=True)

# uint8 0-255, shape (N, 28, 28, 3) -> float 0-1
x_train = torch.from_numpy(train.imgs).float() / 255
x_val = torch.from_numpy(val.imgs).float() / 255
y_train = torch.from_numpy(train.labels).long().squeeze(1)
y_val = torch.from_numpy(val.labels).long().squeeze(1)

# Per-channel mean and spread from the training set only, applied to both splits.
# Conv layers want (N, channels, height, width), so move channels first instead of flattening.
mean = x_train.mean(dim=(0, 1, 2))
std = x_train.std(dim=(0, 1, 2))
x_train = ((x_train - mean) / std).permute(0, 3, 1, 2).contiguous().to(device)
x_val = ((x_val - mean) / std).permute(0, 3, 1, 2).contiguous().to(device)
y_train, y_val = y_train.to(device), y_val.to(device)

n_classes = 9
model = CNN(n_classes).to(device)
optimizer = torch.optim.SGD(model.parameters(), lr=args.lr)
# Cosine decay: the learning rate follows a smooth curve from --lr down to near 0 by the last epoch.
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
print(f"CNN with {sum(p.numel() for p in model.parameters())} weights")


def predict(x):
    # Chunks keep memory small: all 89,996 images through conv1 at once would be about 9 GB.
    with torch.no_grad():
        return torch.cat([model(x[i : i + 2048]) for i in range(0, len(x), 2048)])


def evaluate(x, y):
    logits = predict(x)
    return cross_entropy(logits, y).item(), (logits.argmax(dim=1) == y).float().mean().item()


val_loss, val_acc = evaluate(x_val, y_val)
print(f"before training: val loss {val_loss:.4f} (ln 9 = 2.1972), val acc {val_acc:.1%}")

best_val_acc, best_epoch, best_weights = 0.0, 0, None
for epoch in range(1, args.epochs + 1):
    lr = optimizer.param_groups[0]["lr"]
    start = time.perf_counter()
    order = torch.randperm(len(x_train), device=device)
    for i in range(0, len(order), args.batch_size):
        batch = order[i : i + args.batch_size]
        x = x_train[batch]
        if args.augment:
            x = flip_rotate(x, augment_generator)  # training batches only, never validation
        loss = cross_entropy(model(x), y_train[batch])
        loss.backward()
        # Typical gradient size is about 2.5; rare spikes of 15-25 knocked training off course.
        # Shrink any gradient longer than --clip to that length, keeping its direction.
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
        optimizer.step()
        optimizer.zero_grad()
    scheduler.step()
    if device.type == "mps":
        torch.mps.synchronize()  # GPU work runs asynchronously; wait so the timing is real
    elapsed = time.perf_counter() - start

    # Train metrics use the end-of-epoch weights so they compare fairly with validation.
    train_loss, train_acc = evaluate(x_train, y_train)
    val_loss, val_acc = evaluate(x_val, y_val)
    print(
        f"epoch {epoch:2d}  lr {lr:.5f}  train loss {train_loss:.4f}  acc {train_acc:.1%}  |  "
        f"val loss {val_loss:.4f}  acc {val_acc:.1%}  ({elapsed:.1f}s)"
    )

    if val_acc > best_val_acc:
        best_val_acc, best_epoch = val_acc, epoch
        best_weights = copy.deepcopy(model.state_dict())

# Use the best epoch's weights, not whatever the last epoch happened to land on.
model.load_state_dict(best_weights)
args.save.parent.mkdir(parents=True, exist_ok=True)
# Save the normalization too: new images must be scaled exactly like the training images.
torch.save({"weights": best_weights, "mean": mean, "std": std}, args.save)
print(f"\nbest: epoch {best_epoch}, val acc {best_val_acc:.1%}, saved to {args.save}")

# Confusion matrix on validation: row = true class, column = predicted class.
codes = ["ADI", "BACK", "DEB", "LYM", "MUC", "MUS", "NORM", "STR", "TUM"]
predicted = predict(x_val).argmax(dim=1)
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
