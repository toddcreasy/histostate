import math

import torch
import torch.nn.functional as F

from histostate.softmax import cross_entropy, softmax


def test_softmax_matches_torch_and_sums_to_one():
    torch.manual_seed(0)
    logits = torch.randn(16, 9)
    probs = softmax(logits)
    torch.testing.assert_close(probs, F.softmax(logits, dim=1))
    torch.testing.assert_close(probs.sum(dim=1), torch.ones(16))


def test_softmax_survives_huge_logits():
    logits = torch.tensor([[1000.0, 999.0, 0.0]])
    probs = softmax(logits)
    assert torch.isfinite(probs).all()
    torch.testing.assert_close(probs, F.softmax(logits, dim=1))


def test_cross_entropy_matches_torch():
    torch.manual_seed(0)
    logits = torch.randn(16, 9)
    labels = torch.randint(0, 9, (16,))
    torch.testing.assert_close(cross_entropy(logits, labels), F.cross_entropy(logits, labels))


def test_cross_entropy_of_uniform_guess_is_ln_9():
    logits = torch.zeros(4, 9)
    labels = torch.tensor([0, 3, 5, 8])
    torch.testing.assert_close(cross_entropy(logits, labels), torch.tensor(math.log(9)))
