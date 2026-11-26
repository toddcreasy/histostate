# frontend

The website at histostate.pilotbio.io: a Next.js static export that runs the trained CNN
(convolutional neural network) in the visitor's browser with ONNX Runtime Web. Nothing is uploaded;
there is no server.

```sh
npm ci
npm run dev      # http://localhost:3000
npm test         # the browser's resize against Pillow, byte for byte
npm run lint
npm run build    # writes out/
```

How an answer stays the same as `histostate ask`:

- `public/model/stage3_cnn.onnx` comes from `scripts/export_onnx.py`, which checks it against
  PyTorch on all 7,180 test tiles. The graph does the scaling, mean and spread, and softmax.
- `src/lib/resize.ts` is a port of Pillow's bicubic resize. `src/lib/resize.test.ts` checks it
  against `src/lib/resize.fixtures.json.gz`, written by `scripts/make_resize_fixtures.py`.

After retraining, rerun `uv run --group site python scripts/export_onnx.py --out frontend/public/model/stage3_cnn.onnx`.

`public/examples/` is the first tile of each class in the PathMNIST test split, not hand-picked.
`public/images/` are figures from `docs/images/`.
