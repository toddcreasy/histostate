# frontend

The website at https://histostate.pilotbio.io: a Next.js static export that runs the trained CNN
(convolutional neural network) in the visitor's browser with ONNX (Open Neural Network Exchange)
Runtime Web. Nothing is uploaded; there is no server.

```sh
npm ci           # Node.js 24 or newer (CI uses 24)
npm run dev      # http://localhost:3000
npm test         # the browser's resize against Pillow, byte for byte
npm run lint
npm run build    # writes out/
```

## How an answer stays the same as `histostate ask`

- `public/model/stage3_cnn.onnx` comes from `scripts/export_onnx.py`, which checks it against
  PyTorch on all 7,180 test tiles. The graph does the scaling, mean and spread, and softmax.
- `src/lib/resize.ts` is a port of Pillow's bicubic resize. `src/lib/resize.test.ts` checks it
  against `src/lib/resize.fixtures.json.gz`, written by `scripts/make_resize_fixtures.py`.
- `src/lib/model.ts` reads pixels at the file's own size with no color profile and no EXIF
  rotation, as Pillow does, and in strips, so phone photos bigger than Safari's canvas limit work.

After retraining, rerun
`uv run --group site python scripts/export_onnx.py --out frontend/public/model/stage3_cnn.onnx`.
It refuses a checkpoint not trained at 64 pixels: `SIZE` in `src/lib/model.ts` and
`src/app/classifier.tsx` would have to change with it.

## What's where

| File | What it does |
|---|---|
| `src/app/page.tsx` | The page: header section with stat cards, the classifier, the three findings, the footer |
| `src/app/classifier.tsx` | The drop box (files, or images dragged from a web page), the example tiles, the answer |
| `src/app/header.tsx` | The header, as on rwe-workbench: mark, name, PilotBio, GitHub, help, theme |
| `src/app/help.tsx` | Help on the page, rwe-workbench's without the glossary; `home-help.tsx` holds the notes |
| `src/app/released.tsx` | The footer's release line, from `version` and `released` in `package.json` |
| `public/examples/` | The first tile of each class in the PathMNIST test split, not hand-picked |
| `public/images/` | Figures from `docs/images/` |

## Deploy

A merge to `main` that touches `frontend/` runs `.github/workflows/deploy.yml`: it tests and
builds the site and uploads `out/` to Amplify. To deploy by hand, run that workflow from the
Actions tab. The Amplify app, its domain, and its headers are in `infra/terraform/site/`.

The site sends a Content-Security-Policy (`infra/terraform/site/amplify.tf`). It allows only this
site's own scripts, styles, fonts, and images, plus fetches over HTTPS for images dragged in from
other sites. Anything new from outside, such as a font or script from a CDN (content delivery
network), has to be added there first, or browsers will block it. A release sets `version` and
`released` in `package.json` together.
