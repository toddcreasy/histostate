// Runs the trained CNN (convolutional neural network) in the visitor's browser with ONNX
// Runtime Web. Same steps as `histostate ask`: decode, resize to 64x64 with Pillow's bicubic
// filter (resize.ts), then the model. The ONNX graph does the scaling, the training mean and
// spread, and softmax itself (scripts/export_onnx.py).

import * as ort from "onnxruntime-web/wasm";

import { resizeBicubic } from "./resize.ts";

// Output order of the model: histostate.ask.TISSUES, from MedMNIST's PathMNIST labels.
export const TISSUES = [
  "adipose",
  "background",
  "debris",
  "lymphocytes",
  "mucus",
  "smooth muscle",
  "normal colon mucosa",
  "cancer-associated stroma",
  "colorectal adenocarcinoma epithelium",
] as const;

export const SIZE = 64;

export type Prediction = { tissue: (typeof TISSUES)[number]; probability: number };

// Which step failed, so the page can say "couldn't load the model" or "couldn't read that file".
export class ModelLoadError extends Error {}
export class ImageReadError extends Error {}

let session: Promise<ort.InferenceSession> | null = null;

function load(): Promise<ort.InferenceSession> {
  if (!session) {
    // The bundler serves ONNX Runtime's WebAssembly engine from this site, not a CDN. One
    // thread: more need cross-origin isolation headers, and this model is small.
    ort.env.wasm.numThreads = 1;
    session = ort.InferenceSession.create("/model/stage3_cnn.onnx").catch((error) => {
      session = null; // a network blip shouldn't break the page until a reload
      throw new ModelLoadError(String(error));
    });
  }
  return session;
}

// Safari refuses canvases over 16,777,216 pixels, and a phone photo can be bigger, so the
// pixels are read in horizontal strips under that size.
const MAX_CANVAS_PIXELS = 16_000_000;

// Pixels at the file's own size, as Pillow reads them in ask.py: no color profile applied, no
// EXIF rotation (Image.open doesn't rotate either), and like Image.convert("RGB"),
// transparency dropped rather than blended.
async function decode(blob: Blob): Promise<{ rgb: Uint8Array; width: number; height: number }> {
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(blob, {
      colorSpaceConversion: "none",
      premultiplyAlpha: "none",
      imageOrientation: "none",
    });
  } catch (error) {
    throw new ImageReadError(String(error));
  }
  const { width, height } = bitmap;
  const rgb = new Uint8Array(width * height * 3);
  const stripRows = Math.max(1, Math.floor(MAX_CANVAS_PIXELS / width));
  const canvas = new OffscreenCanvas(width, Math.min(stripRows, height));
  const context = canvas.getContext("2d");
  if (!context) throw new ImageReadError("This browser cannot read image pixels.");
  for (let top = 0; top < height; top += stripRows) {
    const rows = Math.min(stripRows, height - top);
    context.clearRect(0, 0, width, rows);
    context.drawImage(bitmap, 0, top, width, rows, 0, 0, width, rows);
    const rgba = context.getImageData(0, 0, width, rows).data;
    for (let i = 0, j = top * width * 3; i < rgba.length; i += 4, j += 3) {
      rgb[j] = rgba[i];
      rgb[j + 1] = rgba[i + 1];
      rgb[j + 2] = rgba[i + 2];
    }
  }
  bitmap.close();
  return { rgb, width, height };
}

// The 64x64 tile the model sees, and its probabilities for the nine tissues, highest first.
export async function classify(blob: Blob): Promise<{ tile: Uint8Array; predictions: Prediction[] }> {
  const { rgb, width, height } = await decode(blob);
  const tile = resizeBicubic(rgb, width, height, SIZE, SIZE);
  const model = await load();
  const pixels = new ort.Tensor("float32", Float32Array.from(tile), [1, SIZE, SIZE, 3]);
  const output = await model.run({ pixels });
  const probabilities = output.probabilities.data as Float32Array;
  const predictions = TISSUES.map((tissue, i) => ({ tissue, probability: probabilities[i] }));
  predictions.sort((a, b) => b.probability - a.probability);
  return { tile, predictions };
}
