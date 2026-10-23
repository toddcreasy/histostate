import torch
from torch import nn


class CNN(nn.Module):
    def __init__(self, n_classes: int, size: int = 28, blocks: int | None = None):
        super().__init__()
        # Larger tiles get more blocks by default, so the last layer still sees an 8x8 grid and
        # each feature sees a wider patch: 18x18 pixels with 3 blocks, 38x38 with 4.
        blocks = blocks or {28: 2, 64: 3, 128: 4}[size]
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 64, kernel_size=3, padding=1) if blocks >= 3 else None
        self.conv4 = nn.Conv2d(64, 64, kernel_size=3, padding=1) if blocks == 4 else None
        self.pool = nn.MaxPool2d(2)
        side = size // 2**blocks
        self.output = nn.Linear(64 * side * side, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(torch.relu(self.conv1(x)))  # 3x28x28 -> 32x14x14
        x = self.pool(torch.relu(self.conv2(x)))  # 32x14x14 -> 64x7x7
        if self.conv3 is not None:
            x = self.pool(torch.relu(self.conv3(x)))  # 64x7x7 -> 64x3x3, or 64x16x16 -> 64x8x8
        if self.conv4 is not None:
            x = self.pool(torch.relu(self.conv4(x)))  # 64x16x16 -> 64x8x8 for 128-pixel tiles
        return self.output(x.flatten(start_dim=1))
