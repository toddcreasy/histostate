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

let session: Promise<ort.InferenceSession> | null = null;

function load(): Promise<ort.InferenceSession> {
  if (!session) {
    // The bundler serves ONNX Runtime's WebAssembly engine from this site, not a CDN. One
    // thread: more need cross-origin isolation headers, and this model is small.
    ort.env.wasm.numThreads = 1;
    session = ort.InferenceSession.create("/model/stage3_cnn.onnx");
  }
  return session;
}

// Pixels at the file's own size, with no color profile applied, as Pillow reads them. Like
// Image.convert("RGB"), transparency is dropped rather than blended.
async function decode(blob: Blob): Promise<{ rgb: Uint8Array; width: number; height: number }> {
  const bitmap = await createImageBitmap(blob, {
    colorSpaceConversion: "none",
    premultiplyAlpha: "none",
  });
  const { width, height } = bitmap;
  const canvas = new OffscreenCanvas(width, height);
  const context = canvas.getContext("2d");
  if (!context) throw new Error("This browser cannot read image pixels.");
  context.drawImage(bitmap, 0, 0);
  bitmap.close();
  const rgba = context.getImageData(0, 0, width, height).data;
  const rgb = new Uint8Array(width * height * 3);
  for (let i = 0, j = 0; i < rgba.length; i += 4, j += 3) {
    rgb[j] = rgba[i];
    rgb[j + 1] = rgba[i + 1];
    rgb[j + 2] = rgba[i + 2];
  }
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
