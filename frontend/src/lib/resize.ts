// Resize RGB pixels exactly as Pillow's Image.resize(size, Image.Resampling.BICUBIC) does, so
// the browser feeds the model the same 64x64 tile as `histostate ask` (src/histostate/ask.py).
// A port of Pillow's libImaging/Resample.c (8 bits per channel): bicubic filter with a = -0.5,
// widened when shrinking so every input pixel counts (antialiasing), weights in fixed point with
// 22 fractional bits, horizontal pass first, each pass rounded and clipped to 0-255.
// resize.test.ts checks it byte for byte against Pillow.

const PRECISION_BITS = 32 - 8 - 2;
const SUPPORT = 2;
const A = -0.5;

function bicubic(x: number): number {
  x = Math.abs(x);
  if (x < 1) return ((A + 2) * x - (A + 3)) * x * x + 1;
  if (x < 2) return (((x - 5) * x + 8) * x - 4) * A;
  return 0;
}

type Coefficients = { bounds: Int32Array; weights: Int32Array; ksize: number };

// For each output position: the first input index, how many inputs, and their integer weights.
function coefficients(inSize: number, outSize: number): Coefficients {
  const scale = inSize / outSize;
  const filterscale = Math.max(scale, 1);
  const support = SUPPORT * filterscale;
  const ksize = Math.ceil(support) * 2 + 1;
  const bounds = new Int32Array(outSize * 2);
  const weights = new Int32Array(outSize * ksize);
  const k = new Float64Array(ksize);
  for (let xx = 0; xx < outSize; xx++) {
    const center = (xx + 0.5) * scale;
    const ss = 1 / filterscale;
    // Math.trunc matches C's (int) cast, which rounds toward zero.
    const xmin = Math.max(Math.trunc(center - support + 0.5), 0);
    const xmax = Math.min(Math.trunc(center + support + 0.5), inSize) - xmin;
    let ww = 0;
    for (let x = 0; x < xmax; x++) {
      const w = bicubic((x + xmin - center + 0.5) * ss);
      k[x] = w;
      ww += w;
    }
    for (let x = 0; x < ksize; x++) {
      const w = x < xmax && ww !== 0 ? k[x] / ww : 0;
      // Pillow's normalize_coeffs_8bpc: round half away from zero.
      weights[xx * ksize + x] = Math.trunc(w < 0 ? -0.5 + w * (1 << PRECISION_BITS) : 0.5 + w * (1 << PRECISION_BITS));
    }
    bounds[xx * 2] = xmin;
    bounds[xx * 2 + 1] = xmax;
  }
  return { bounds, weights, ksize };
}

function clip8(value: number): number {
  if (value >= 255 * (1 << PRECISION_BITS) + (1 << PRECISION_BITS)) return 255;
  if (value <= 0) return 0;
  return Math.floor(value / (1 << PRECISION_BITS));
}

function horizontal(src: Uint8Array, width: number, height: number, outWidth: number): Uint8Array {
  const { bounds, weights, ksize } = coefficients(width, outWidth);
  const out = new Uint8Array(outWidth * height * 3);
  for (let y = 0; y < height; y++) {
    for (let xx = 0; xx < outWidth; xx++) {
      const xmin = bounds[xx * 2];
      const xmax = bounds[xx * 2 + 1];
      for (let c = 0; c < 3; c++) {
        let ss = 1 << (PRECISION_BITS - 1);
        for (let x = 0; x < xmax; x++) {
          ss += src[(y * width + x + xmin) * 3 + c] * weights[xx * ksize + x];
        }
        out[(y * outWidth + xx) * 3 + c] = clip8(ss);
      }
    }
  }
  return out;
}

function vertical(src: Uint8Array, width: number, height: number, outHeight: number): Uint8Array {
  const { bounds, weights, ksize } = coefficients(height, outHeight);
  const out = new Uint8Array(width * outHeight * 3);
  for (let yy = 0; yy < outHeight; yy++) {
    const ymin = bounds[yy * 2];
    const ymax = bounds[yy * 2 + 1];
    for (let x = 0; x < width; x++) {
      for (let c = 0; c < 3; c++) {
        let ss = 1 << (PRECISION_BITS - 1);
        for (let y = 0; y < ymax; y++) {
          ss += src[((y + ymin) * width + x) * 3 + c] * weights[yy * ksize + y];
        }
        out[(yy * width + x) * 3 + c] = clip8(ss);
      }
    }
  }
  return out;
}

// rgb is width x height x 3, row by row. Returns outWidth x outHeight x 3.
export function resizeBicubic(
  rgb: Uint8Array,
  width: number,
  height: number,
  outWidth: number,
  outHeight: number,
): Uint8Array {
  let pixels = rgb;
  if (outWidth !== width) pixels = horizontal(pixels, width, height, outWidth);
  if (outHeight !== height) pixels = vertical(pixels, outWidth, height, outHeight);
  return pixels === rgb ? rgb.slice() : pixels;
}
