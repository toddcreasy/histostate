import torch
from torch import nn

from histostate.cnn import CNN


def test_conv_output_is_patch_times_filter_plus_bias():
    torch.manual_seed(0)
    conv = nn.Conv2d(3, 4, kernel_size=3, padding=1)
    image = torch.randn(1, 3, 6, 6)
    out = conv(image)

    f, row, col = 2, 3, 4
    patch = image[0, :, row - 1 : row + 2, col - 1 : col + 2]  # 3 channels x 3 x 3
    by_hand = (patch * conv.weight[f]).sum() + conv.bias[f]
    torch.testing.assert_close(out[0, f, row, col], by_hand)


def test_max_pool_keeps_largest_of_each_2x2_block():
    x = torch.tensor([[[[1.0, 5.0, 2.0, 0.0], [3.0, 2.0, 8.0, 1.0]]]])
    torch.testing.assert_close(nn.MaxPool2d(2)(x), torch.tensor([[[[5.0, 8.0]]]]))


def test_cnn_gives_nine_scores_per_image():
    assert CNN(n_classes=9)(torch.randn(4, 3, 28, 28)).shape == (4, 9)


def test_64_pixel_cnn_adds_a_block_and_gives_nine_scores():
    model = CNN(n_classes=9, size=64)
    assert model(torch.randn(2, 3, 64, 64)).shape == (2, 9)
    assert model.output.in_features == 64 * 8 * 8
    assert CNN(n_classes=9).conv3 is None
