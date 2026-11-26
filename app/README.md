# Demo app

A Gradio web page around `histostate.ask.predict`: upload an H&E tile, get the top three tissue
types. It runs the same preprocessing as `histostate ask`.

From the repo root, with the model in `models/stage3_cnn.pt` (see Setup in the main README):

```bash
uv run --group app python app/app.py
```

Then open http://127.0.0.1:7860.

`examples/` holds the first tile of each class in the PathMNIST test split at 64 pixels, in
dataset order, not hand-picked. PathMNIST is CC BY 4.0; see the main README for citations.
