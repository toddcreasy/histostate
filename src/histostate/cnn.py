import torch
from torch import nn


class CNN(nn.Module):
    def __init__(self, n_classes: int):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2)
        self.output = nn.Linear(64 * 7 * 7, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(torch.relu(self.conv1(x)))  # 3x28x28 -> 32x14x14
        x = self.pool(torch.relu(self.conv2(x)))  # 32x14x14 -> 64x7x7
        return self.output(x.flatten(start_dim=1))
