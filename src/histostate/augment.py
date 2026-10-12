import torch


def flip_rotate(x: torch.Tensor, generator: torch.Generator | None = None) -> torch.Tensor:
    # Give each square image in (N, channels, H, W) one of its 8 orientations at random.
    # A left-right mirror plus 0-3 quarter turns covers all 8; an up-down mirror is a
    # left-right mirror turned twice. Pixels only move, so nothing gets blurred.
    flip = torch.rand(len(x), device=x.device, generator=generator) < 0.5
    x = torch.where(flip[:, None, None, None], x.flip(3), x)
    turns = torch.randint(0, 4, (len(x),), device=x.device, generator=generator)
    out = x.clone()
    for k in range(1, 4):
        out[turns == k] = torch.rot90(x[turns == k], k, dims=(2, 3))
    return out
