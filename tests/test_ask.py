import logging

import torch
from PIL import Image

from histostate.ask import TISSUES, main, predict
from histostate.cnn import CNN


def make_checkpoint(path):
    torch.manual_seed(0)
    weights = CNN(len(TISSUES)).state_dict()
    torch.save({"weights": weights, "mean": torch.full((3,), 0.5), "std": torch.ones(3)}, path)


def test_predict_gives_nine_probabilities_that_sum_to_one(tmp_path):
    make_checkpoint(tmp_path / "model.pt")
    Image.new("RGB", (224, 224), (200, 120, 180)).save(tmp_path / "tile.png")

    probabilities = predict(tmp_path / "tile.png", tmp_path / "model.pt")

    assert probabilities.shape == (9,)
    torch.testing.assert_close(probabilities.sum(), torch.tensor(1.0))


def test_ask_reports_top_tissue_and_runners_up(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    make_checkpoint(tmp_path / "model.pt")
    Image.new("RGB", (50, 40), (90, 60, 140)).save(tmp_path / "tile.png")

    main(["ask", str(tmp_path / "tile.png"), "--model", str(tmp_path / "model.pt")])

    lines = caplog.messages
    assert len(lines) == 3
    assert "confident" in lines[0]
    assert any(tissue in lines[0] for tissue in TISSUES)
