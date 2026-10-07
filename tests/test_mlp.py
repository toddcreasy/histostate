import torch

from histostate.mlp import MLP
from histostate.softmax import cross_entropy


def test_mlp_matches_hand_written_layers():
    torch.manual_seed(0)
    x = torch.randn(32, 20)
    labels = torch.randint(0, 9, (32,))

    W1 = torch.randn(20, 16, requires_grad=True)
    b1 = torch.randn(16, requires_grad=True)
    W2 = torch.randn(16, 9, requires_grad=True)
    b2 = torch.randn(9, requires_grad=True)
    hand_logits = (x @ W1 + b1).clamp(min=0) @ W2 + b2
    cross_entropy(hand_logits, labels).backward()

    model = MLP(20, 16, 9)
    with torch.no_grad():
        model.hidden.weight.copy_(W1.T)
        model.hidden.bias.copy_(b1)
        model.output.weight.copy_(W2.T)
        model.output.bias.copy_(b2)
    module_logits = model(x)
    cross_entropy(module_logits, labels).backward()

    torch.testing.assert_close(module_logits, hand_logits)
    torch.testing.assert_close(model.hidden.weight.grad, W1.grad.T)
    torch.testing.assert_close(model.hidden.bias.grad, b1.grad)
    torch.testing.assert_close(model.output.weight.grad, W2.grad.T)
    torch.testing.assert_close(model.output.bias.grad, b2.grad)
