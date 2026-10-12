import torch

from histostate.augment import flip_rotate


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
