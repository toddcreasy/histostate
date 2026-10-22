import torch
from torch import nn


class CNN(nn.Module):
    def __init__(self, n_classes: int, size: int = 28):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        # 64-pixel tiles get a third block: the last layer stays small (8x8 grid) and each feature
        # sees an 18x18 patch instead of 8x8, long enough to span a fiber.
        self.conv3 = nn.Conv2d(64, 64, kernel_size=3, padding=1) if size == 64 else None
        self.pool = nn.MaxPool2d(2)
        side = size // 8 if self.conv3 else size // 4
        self.output = nn.Linear(64 * side * side, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(torch.relu(self.conv1(x)))  # 3x28x28 -> 32x14x14
        x = self.pool(torch.relu(self.conv2(x)))  # 32x14x14 -> 64x7x7
        if self.conv3 is not None:
            x = self.pool(torch.relu(self.conv3(x)))  # 64x16x16 -> 64x8x8 for 64-pixel tiles
        return self.output(x.flatten(start_dim=1))
