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


def color_jitter(
    x: torch.Tensor, strength: float, generator: torch.Generator | None = None
) -> torch.Tensor:
    # Per image and per color channel, multiply by a random factor in 1 +/- strength and add a
    # random shift in +/- strength. Mimics slides stained darker, paler, or with one stain stronger.
    n, c = x.shape[:2]
    scale = 1 + strength * (2 * torch.rand(n, c, 1, 1, device=x.device, generator=generator) - 1)
    shift = strength * (2 * torch.rand(n, c, 1, 1, device=x.device, generator=generator) - 1)
    return x * scale + shift
