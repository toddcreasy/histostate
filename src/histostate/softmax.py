import torch


def log_softmax(logits: torch.Tensor) -> torch.Tensor:
    # Subtracting the row max leaves the result unchanged but stops exp() from overflowing.
    shifted = logits - logits.max(dim=1, keepdim=True).values
    return shifted - shifted.exp().sum(dim=1, keepdim=True).log()


def softmax(logits: torch.Tensor) -> torch.Tensor:
    return log_softmax(logits).exp()


def cross_entropy(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    # For each row, take -log(probability assigned to the correct class), then average.
    correct_log_probs = log_softmax(logits)[torch.arange(len(labels)), labels]
    return -correct_log_probs.mean()
