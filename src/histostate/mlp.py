import torch
from torch import nn


class MLP(nn.Module):
    def __init__(self, n_features: int, n_hidden: int, n_classes: int):
        super().__init__()
        self.hidden = nn.Linear(n_features, n_hidden)
        self.output = nn.Linear(n_hidden, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.output(torch.relu(self.hidden(x)))
