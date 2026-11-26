from pathlib import Path

import gradio as gr

from histostate.ask import TISSUES, predict

MODEL = Path("models/stage3_cnn.pt")
EXAMPLES = sorted(str(p) for p in (Path(__file__).parent / "examples").glob("*.png"))
REPO = "https://github.com/toddcreasy/histostate"

DESCRIPTION = f"""
Upload a colorectal H&E tile, or click an example below, and a small CNN (convolutional neural
network) names the tissue. I built and trained it from scratch in PyTorch: 93,193 weights, no
pretrained model. It scores 94.7% on a held-out test set from a second clinical center.

It only knows nine tissue types from one dataset ([PathMNIST](https://medmnist.com/)), and it
always picks one of them. Upload a photo of a cat and it will still name a tissue, with confidence.
Stroma and smooth muscle are its weakest classes (75% and 83% recall on the test set).

How it was built, what went wrong, and how I checked it:
[the walkthrough]({REPO}/blob/main/docs/walkthrough.md).
Source: [{REPO.removeprefix("https://")}]({REPO}).

A learning project, not a medical device. Not for clinical or diagnostic use.
"""


def classify(image_path: str) -> dict[str, float]:
    probabilities = predict(Path(image_path), MODEL)
    return {tissue: float(p) for tissue, p in zip(TISSUES, probabilities, strict=True)}


demo = gr.Interface(
    fn=classify,
    inputs=gr.Image(type="filepath", label="H&E tile"),
    outputs=gr.Label(num_top_classes=3, label="Tissue type"),
    examples=EXAMPLES,
    title="histostate: name the tissue in an H&E tile",
    description=DESCRIPTION,
    flagging_mode="never",
)

if __name__ == "__main__":
    demo.launch()
