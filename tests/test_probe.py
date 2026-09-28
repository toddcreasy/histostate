import torch

from histostate.probe import LinearProbe, ProbeConfig, predict, train_probe


def test_probe_output_shape() -> None:
    model = LinearProbe(in_dim=1024, n_classes=9)
    assert model(torch.randn(4, 1024)).shape == (4, 9)


def test_probe_learns_separable_data() -> None:
    torch.manual_seed(0)
    n, dim = 200, 16
    y = torch.randint(0, 2, (n,))
    x = torch.randn(n, dim) + y.unsqueeze(1).float() * 4.0
    config = ProbeConfig(epochs=20, batch_size=32, lr=1e-2)
    device = torch.device("cpu")

    model = train_probe(LinearProbe(dim, 2), x, y, config, device)
    acc = (predict(model, x, device) == y).float().mean().item()
    assert acc > 0.95
