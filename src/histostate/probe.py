"""A linear probe: the simplest model that sits on top of frozen features.

If a single linear layer can classify tissue types from Phikon-v2
embeddings, the backbone has already learned the biology. This is the
standard first test of any foundation model.
"""

import torch
from pydantic import BaseModel, Field
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class ProbeConfig(BaseModel):
    """Training hyperparameters, validated by Pydantic."""

    epochs: int = Field(default=30, ge=1)
    batch_size: int = Field(default=64, ge=1)
    lr: float = Field(default=1e-3, gt=0)
    weight_decay: float = Field(default=1e-4, ge=0)
    seed: int = 0


class LinearProbe(nn.Module):
    """Standardize each feature, then one linear layer to class logits.

    BatchNorm1d standardizes each of the in_dim features using statistics
    across the batch (and running averages at eval time). LayerNorm would
    instead normalize each sample across its own features, which can erase
    signal that lives in a feature's absolute level.
    """

    def __init__(self, in_dim: int, n_classes: int) -> None:
        super().__init__()
        self.norm = nn.BatchNorm1d(in_dim, affine=False)
        self.head = nn.Linear(in_dim, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.norm(x))


def train_probe(
    model: nn.Module,
    features: torch.Tensor,
    labels: torch.Tensor,
    config: ProbeConfig,
    device: torch.device,
    on_epoch=None,
) -> nn.Module:
    """Standard PyTorch training loop with cross-entropy loss."""
    torch.manual_seed(config.seed)
    loader = DataLoader(
        TensorDataset(features, labels),
        batch_size=config.batch_size,
        shuffle=True,
    )
    model = model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.lr, weight_decay=config.weight_decay
    )
    loss_fn = nn.CrossEntropyLoss()

    for epoch in range(config.epochs):
        model.train()
        total, n = 0.0, 0
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            optimizer.step()
            total += loss.item() * len(y)
            n += len(y)
        if on_epoch is not None:
            on_epoch(epoch, total / n)
    return model


@torch.inference_mode()
def predict(
    model: nn.Module,
    features: torch.Tensor,
    device: torch.device,
    batch_size: int = 512,
) -> torch.Tensor:
    """Return predicted class indices for every row."""
    model.eval()
    preds = []
    for start in range(0, len(features), batch_size):
        logits = model(features[start : start + batch_size].to(device))
        preds.append(logits.argmax(dim=1).cpu())
    return torch.cat(preds)
