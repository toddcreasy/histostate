"""Fit a line y = w * x + b with gradient descent, using torch.optim.SGD for the update.

Run: uv run python scripts/warmup_fit_line.py [--lr 0.01] [--steps 1000]
"""

import argparse

import torch

parser = argparse.ArgumentParser()
parser.add_argument("--lr", type=float, default=0.01)
parser.add_argument("--steps", type=int, default=1000)
args = parser.parse_args()

torch.manual_seed(0)

# Fake data from a known line, plus noise. The model never sees TRUE_W or TRUE_B.
TRUE_W, TRUE_B = 2.0, 1.0
x = torch.rand(100) * 10
y = TRUE_W * x + TRUE_B + torch.randn(100)

# requires_grad=True tells autograd to compute d(loss)/d(weight) for these.
w = torch.tensor(0.0, requires_grad=True)
b = torch.tensor(0.0, requires_grad=True)

optimizer = torch.optim.SGD([w, b], lr=args.lr)

for step in range(args.steps + 1):
    prediction = w * x + b
    loss = ((prediction - y) ** 2).mean()

    loss.backward()

    if step % (args.steps // 10) == 0:
        print(
            f"step {step:5d}  loss {loss.item():10.4f}  "
            f"w {w.item():7.4f}  b {b.item():7.4f}  "
            f"grad_w {w.grad.item():9.4f}  grad_b {b.grad.item():9.4f}"
        )

    # Same as: w -= lr * w.grad; b -= lr * b.grad
    optimizer.step()

    # Gradients accumulate across backward() calls, so reset them every step.
    optimizer.zero_grad()

print(f"\nlearned: w = {w.item():.4f}, b = {b.item():.4f}")
print(f"true:    w = {TRUE_W:.4f}, b = {TRUE_B:.4f}")
