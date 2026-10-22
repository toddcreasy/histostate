import torch

from histostate.splits import split_test


def test_halves_are_disjoint_cover_everything_and_keep_the_class_mix():
    labels = torch.randint(0, 9, (1001,), generator=torch.Generator().manual_seed(0))
    shift_val, final_test = split_test(labels)

    assert len(set(shift_val.tolist()) & set(final_test.tolist())) == 0
    assert sorted(shift_val.tolist() + final_test.tolist()) == list(range(1001))
    for c in range(9):
        n_val = (labels[shift_val] == c).sum().item()
        n_test = (labels[final_test] == c).sum().item()
        assert abs(n_val - n_test) <= 1


def test_split_is_the_same_every_time():
    labels = torch.arange(100) % 9
    a, b = split_test(labels), split_test(labels)
    assert torch.equal(a[0], b[0]) and torch.equal(a[1], b[1])
