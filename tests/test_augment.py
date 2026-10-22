import torch

from histostate.augment import color_jitter, flip_rotate


def orientations(image):
    turns = [torch.rot90(image, k, dims=(1, 2)) for k in range(4)]
    return turns + [t.flip(2) for t in turns]


def test_each_image_becomes_one_of_its_eight_orientations():
    torch.manual_seed(0)
    x = torch.randn(64, 3, 5, 5)
    out = flip_rotate(x)

    assert out.shape == x.shape
    for before, after in zip(x, out, strict=True):
        assert any(torch.equal(after, o) for o in orientations(before))


def test_all_eight_orientations_show_up():
    image = torch.arange(9.0).reshape(1, 1, 3, 3).expand(400, 1, 3, 3)
    out = flip_rotate(image, torch.Generator().manual_seed(0))
    assert len({tuple(o.flatten().tolist()) for o in out}) == 8


def test_color_jitter_scales_and_shifts_each_channel_within_strength():
    x = torch.ones(200, 3, 4, 4)
    out = color_jitter(x, 0.2, torch.Generator().manual_seed(0))

    # Every pixel in one channel of one image moves together, by scale + shift.
    assert torch.equal(out, out[:, :, :1, :1].expand_as(out))
    assert out.min() >= 1 - 0.4 and out.max() <= 1 + 0.4
    assert out.std() > 0


def test_color_jitter_with_zero_strength_changes_nothing():
    x = torch.randn(8, 3, 5, 5)
    torch.testing.assert_close(color_jitter(x, 0.0), x)
