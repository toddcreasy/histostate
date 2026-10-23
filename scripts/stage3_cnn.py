"""Stage 3: a small CNN on PathMNIST, built from nn.Conv2d, nn.MaxPool2d, and nn.Linear.

Run: uv run python scripts/stage3_cnn.py [--lr 0.1] [--epochs 60] [--batch-size 128] [--clip 5.0]
                                         [--no-augment] [--jitter 0.3] [--seed 0]
                                         [--size 28|64|128] [--blocks 2|3|4]
                                         [--device auto|cuda|mps|cpu]
                                         [--save models/stage3_cnn.pt]
"""

import argparse
import copy
import time
from pathlib import Path

import torch
from medmnist import PathMNIST

from histostate.augment import color_jitter, flip_rotate
from histostate.cnn import CNN
from histostate.softmax import cross_entropy
from histostate.splits import split_test

parser = argparse.ArgumentParser()
parser.add_argument("--lr", type=float, default=0.1)
parser.add_argument("--epochs", type=int, default=60)
parser.add_argument("--batch-size", type=int, default=128)
parser.add_argument("--clip", type=float, default=5.0)
parser.add_argument(
    "--augment",
    action=argparse.BooleanOptionalAction,
    default=True,
    help="random flips and quarter turns",
)
parser.add_argument("--jitter", type=float, default=0.3, help="color jitter strength, 0 = off")
parser.add_argument("--seed", type=int, default=0)
parser.add_argument(
    "--size", type=int, default=64, choices=[28, 64, 128], help="tile width in pixels"
)
parser.add_argument("--blocks", type=int, choices=[2, 3, 4], help="conv blocks; default by size")
parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
parser.add_argument("--save", type=Path, default=Path("models/stage3_cnn.pt"))
args = parser.parse_args()

# auto: the first available of CUDA (NVIDIA GPU), MPS (Apple GPU), then CPU.
if args.device == "auto":
    if torch.cuda.is_available():
        args.device = "cuda"
    elif torch.backends.mps.is_available():
        args.device = "mps"
    else:
        args.device = "cpu"
torch.manual_seed(args.seed)
device = torch.device(args.device)
# Augmentation draws from its own generator so batch order matches a run with --no-augment.
augment_generator = torch.Generator(device=device).manual_seed(args.seed + 1)
jitter_generator = torch.Generator(device=device).manual_seed(args.seed + 2)

size = None if args.size == 28 else args.size  # MedMNIST's original files are 28 pixels
train = PathMNIST(split="train", download=True, size=size)
val = PathMNIST(split="val", download=True, size=size)
test = PathMNIST(split="test", download=True, size=size)


# Images stay as uint8 0-255, shape (N, H, W, 3), and become floats one batch at a time in
# prepare(). At 128 pixels the training set is 4.4 GB this way and 17.7 GB as floats.
x_train = torch.from_numpy(train.imgs)
x_val = torch.from_numpy(val.imgs)
y_train = torch.from_numpy(train.labels).long().squeeze(1)
y_val = torch.from_numpy(val.labels).long().squeeze(1)
# Shifted validation: half of the test patients' tiles. Tune on this; the other half is final test.
y_test = torch.from_numpy(test.labels).long().squeeze(1)
shift_idx, _ = split_test(y_test)
x_shift = torch.from_numpy(test.imgs[shift_idx.numpy()])
y_shift = y_test[shift_idx]

# Per-channel mean and spread from the training set only, one channel at a time to cap memory.
mean = torch.stack([x_train[..., c].float().div_(255).mean() for c in range(3)])
std = torch.stack([x_train[..., c].float().div_(255).std() for c in range(3)])
x_train, x_val, x_shift = x_train.to(device), x_val.to(device), x_shift.to(device)
scale = (mean.to(device)[:, None, None], std.to(device)[:, None, None])


def prepare(x):
    # uint8 (N, H, W, 3) -> normalized float (N, 3, H, W): conv layers want channels first.
    return (x.permute(0, 3, 1, 2).float().div(255) - scale[0]) / scale[1]


y_train, y_val, y_shift = y_train.to(device), y_val.to(device), y_shift.to(device)

n_classes = 9
model = CNN(n_classes, args.size, args.blocks).to(device)
optimizer = torch.optim.SGD(model.parameters(), lr=args.lr)
# Cosine decay: the learning rate follows a smooth curve from --lr down to near 0 by the last epoch.
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
print(f"CNN with {sum(p.numel() for p in model.parameters())} weights")


# Chunks keep memory small: 2048 tiles through conv1 is about 1 GB at 64 pixels, 4 GB at 128.
chunk = 2048 if args.size <= 64 else 512


def predict(x):
    with torch.no_grad():
        return torch.cat([model(prepare(x[i : i + chunk])) for i in range(0, len(x), chunk)])


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
        x = prepare(x_train[batch])
        if args.augment:
            x = flip_rotate(x, augment_generator)  # training batches only, never validation
        if args.jitter:
            x = color_jitter(x, args.jitter, jitter_generator)
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
    elif device.type == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start

    # Train metrics use the end-of-epoch weights so they compare fairly with validation.
    train_loss, train_acc = evaluate(x_train, y_train)
    val_loss, val_acc = evaluate(x_val, y_val)
    shift_loss, shift_acc = evaluate(x_shift, y_shift)
    print(
        f"epoch {epoch:2d}  lr {lr:.5f}  train loss {train_loss:.4f}  acc {train_acc:.1%}  |  "
        f"val loss {val_loss:.4f}  acc {val_acc:.1%}  |  "
        f"shift loss {shift_loss:.4f}  acc {shift_acc:.1%}  ({elapsed:.1f}s)"
    )

    if val_acc > best_val_acc:
        best_val_acc, best_epoch = val_acc, epoch
        best_weights = copy.deepcopy(model.state_dict())

# Use the best epoch's weights, not whatever the last epoch happened to land on.
model.load_state_dict(best_weights)
args.save.parent.mkdir(parents=True, exist_ok=True)
# Save the normalization too: new images must be scaled exactly like the training images.
torch.save(
    {"weights": best_weights, "mean": mean, "std": std, "size": args.size, "blocks": args.blocks},
    args.save,
)
print(f"\nbest: epoch {best_epoch}, val acc {best_val_acc:.1%}, saved to {args.save}")
shift_loss, shift_acc = evaluate(x_shift, y_shift)
print(f"shifted validation for that model: loss {shift_loss:.4f}, acc {shift_acc:.1%}")

# Confusion matrix on both validation sets: row = true class, column = predicted class.
codes = ["ADI", "BACK", "DEB", "LYM", "MUC", "MUS", "NORM", "STR", "TUM"]
for name, x, y in [("validation", x_val, y_val), ("shifted validation", x_shift, y_shift)]:
    predicted = predict(x).argmax(dim=1)
    confusion = torch.bincount(y * n_classes + predicted, minlength=n_classes**2)
    confusion = confusion.reshape(n_classes, n_classes).cpu()
    recall = confusion.diag() / confusion.sum(dim=1)
    precision = confusion.diag() / confusion.sum(dim=0)

    print(f"\nconfusion matrix ({name}), rows = true, columns = predicted")
    print("true\\pred " + "".join(f"{c:>6}" for c in codes) + "  recall")
    for i, code in enumerate(codes):
        row = "".join(f"{n:>6}" for n in confusion[i].tolist())
        print(f"{code:<9} {row}  {recall[i]:>6.1%}")
    print("precision " + "".join(f"{p:>6.0%}" for p in precision.tolist()))
