import torch


def split_test(labels: torch.Tensor, seed: int = 0) -> tuple[torch.Tensor, torch.Tensor]:
    # Halve the held-out test set into a shifted validation set (tune on it) and a final test
    # set (look once). Each class is halved separately so both halves keep the same tissue mix.
    generator = torch.Generator().manual_seed(seed)
    shift_val, final_test = [], []
    for c in labels.unique():
        idx = (labels == c).nonzero().squeeze(1)
        idx = idx[torch.randperm(len(idx), generator=generator)]
        shift_val.append(idx[: len(idx) // 2])
        final_test.append(idx[len(idx) // 2 :])
    return torch.cat(shift_val).sort().values, torch.cat(final_test).sort().values
