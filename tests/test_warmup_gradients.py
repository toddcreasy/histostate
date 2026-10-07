import pytest
import torch


@pytest.mark.parametrize("w_start, b_start", [(0.0, 0.0), (1.5, -2.0), (2.0, 1.0), (-3.0, 4.0)])
def test_autograd_matches_hand_derived_gradients(w_start, b_start):
    torch.manual_seed(0)
    x = torch.rand(100) * 10
    y = 2.0 * x + 1.0 + torch.randn(100)

    w = torch.tensor(w_start, requires_grad=True)
    b = torch.tensor(b_start, requires_grad=True)
    loss = ((w * x + b - y) ** 2).mean()
    loss.backward()

    # Calculus on mean((w*x + b - y)^2), done by hand.
    error = (w_start * x + b_start) - y
    hand_grad_w = (2 * error * x).mean()
    hand_grad_b = (2 * error).mean()

    torch.testing.assert_close(w.grad, hand_grad_w)
    torch.testing.assert_close(b.grad, hand_grad_b)


def test_sgd_matches_hand_written_update():
    torch.manual_seed(0)
    x = torch.rand(100) * 10
    y = 2.0 * x + 1.0 + torch.randn(100)
    lr = 0.01

    w_hand = torch.tensor(0.0, requires_grad=True)
    b_hand = torch.tensor(0.0, requires_grad=True)
    for _ in range(200):
        ((w_hand * x + b_hand - y) ** 2).mean().backward()
        with torch.no_grad():
            w_hand -= lr * w_hand.grad
            b_hand -= lr * b_hand.grad
        w_hand.grad.zero_()
        b_hand.grad.zero_()

    w_sgd = torch.tensor(0.0, requires_grad=True)
    b_sgd = torch.tensor(0.0, requires_grad=True)
    optimizer = torch.optim.SGD([w_sgd, b_sgd], lr=lr)
    for _ in range(200):
        ((w_sgd * x + b_sgd - y) ** 2).mean().backward()
        optimizer.step()
        optimizer.zero_grad()

    torch.testing.assert_close(w_sgd, w_hand)
    torch.testing.assert_close(b_sgd, b_hand)
