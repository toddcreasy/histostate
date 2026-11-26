"use client";

import { useEffect, useRef, useState } from "react";

import type { Prediction } from "@/lib/model.ts";

// The model's tile size. model.ts itself is imported on first use (below): ONNX Runtime only
// works in a browser, and loading it lazily keeps it out of the first page load.
const SIZE = 64;

// First tile of each class in the PathMNIST test split, in dataset order, not hand-picked.
const EXAMPLES = [
  { file: "0_adipose.png", label: "Adipose" },
  { file: "1_background.png", label: "Background" },
  { file: "2_debris.png", label: "Debris" },
  { file: "3_lymphocytes.png", label: "Lymphocytes" },
  { file: "4_mucus.png", label: "Mucus" },
  { file: "5_smooth_muscle.png", label: "Smooth muscle" },
  { file: "6_normal_mucosa.png", label: "Normal mucosa" },
  { file: "7_stroma.png", label: "Stroma" },
  { file: "8_tumor.png", label: "Tumor" },
];

type Result = { source: string; tile: Uint8Array; predictions: Prediction[] };

const LOAD_FAILED = "Could not load the model. Check your connection and try again.";
const READ_FAILED = "Could not read that file as an image. Try a PNG or JPEG.";
const EXAMPLE_FAILED = "Could not load that example tile. Try again.";

export default function Classifier() {
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  // Each request gets a number; only the latest may change the page, so a slow photo can't
  // overwrite the answer for a tile picked after it.
  const latest = useRef(0);

  async function run(getBlob: () => Promise<Blob>, source: string) {
    const id = ++latest.current;
    setBusy(true);
    setError(null);
    let message: string | null = null;
    try {
      const blob = await getBlob();
      const model = await import("@/lib/model.ts").catch(() => null);
      if (!model) {
        message = LOAD_FAILED;
      } else {
        try {
          const answer = await model.classify(blob);
          if (id === latest.current) setResult({ source, ...answer });
        } catch (e) {
          message = e instanceof model.ModelLoadError ? LOAD_FAILED : READ_FAILED;
        }
      }
    } catch {
      message = EXAMPLE_FAILED;
    }
    if (id === latest.current) {
      setError(message);
      setBusy(false);
    }
  }

  function runExample(file: string, label: string) {
    return run(async () => {
      const response = await fetch(`/examples/${file}`);
      if (!response.ok) throw new Error(`${response.status}`);
      return response.blob();
    }, `Example: ${label.toLowerCase()}`);
  }

  function runFile(file: File) {
    return run(async () => file, file.name);
  }

  return (
    <div className="rounded-xl bg-card p-5 text-text shadow-xl ring-1 ring-black/5">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload an H&E tile"
        onClick={() => input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) runFile(file);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-5 text-center text-sm transition-colors ${
          dragging ? "border-accent bg-accent/5" : "border-line hover:border-accent/60"
        }`}
      >
        <span className="font-semibold text-ink">Drop an H&amp;E tile here, or click to choose one</span>
        <span className="mt-1 text-muted">PNG or JPEG. It stays in your browser; nothing is uploaded.</span>
        <input
          ref={input}
          type="file"
          accept="image/png,image/jpeg"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) runFile(file);
            e.target.value = "";
          }}
        />
      </div>

      <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted">Or try a test tile</p>
      <div className="mt-2 grid grid-cols-5 gap-2">
        {EXAMPLES.map(({ file, label }) => (
          <button
            key={file}
            type="button"
            onClick={() => runExample(file, label)}
            title={label}
            className="group flex flex-col items-center gap-1"
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- 64px static tiles, no optimizer in a static export */}
            <img
              src={`/examples/${file}`}
              alt={label}
              width={SIZE}
              height={SIZE}
              className="pixelated aspect-square w-full rounded ring-1 ring-line transition group-hover:ring-2 group-hover:ring-accent"
            />
            <span className="w-full text-center text-[11px] leading-tight text-muted">{label}</span>
          </button>
        ))}
      </div>

      <div className="mt-5 min-h-40 border-t border-line pt-4" aria-live="polite">
        {error && <p className="text-sm text-red-700">{error}</p>}
        {!error && !result && (
          <p className="text-sm text-muted">{busy ? "Loading the model…" : "The answer appears here."}</p>
        )}
        {!error && result && <Answer result={result} busy={busy} />}
      </div>
    </div>
  );
}

function Answer({ result, busy }: { result: Result; busy: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const top = result.predictions.slice(0, 3);

  useEffect(() => {
    const context = canvas.current?.getContext("2d");
    if (!context) return;
    const image = context.createImageData(SIZE, SIZE);
    for (let i = 0, j = 0; i < result.tile.length; i += 3, j += 4) {
      image.data[j] = result.tile[i];
      image.data[j + 1] = result.tile[i + 1];
      image.data[j + 2] = result.tile[i + 2];
      image.data[j + 3] = 255;
    }
    context.putImageData(image, 0, 0);
  }, [result]);

  return (
    <div className={`flex gap-4 ${busy ? "opacity-50" : ""}`}>
      <figure className="shrink-0">
        <canvas ref={canvas} width={SIZE} height={SIZE} className="pixelated size-28 rounded ring-1 ring-line" />
        <figcaption className="mt-1 w-28 text-[10px] leading-tight text-muted">What the model sees: 64x64</figcaption>
      </figure>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs text-muted">{result.source}</p>
        <ol className="mt-2 space-y-2">
          {top.map(({ tissue, probability }, i) => (
            <li key={tissue}>
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span className={i === 0 ? "font-semibold text-ink" : "text-text"}>{tissue}</span>
                <span className="tabular-nums text-muted">{(100 * probability).toFixed(probability < 0.01 ? 1 : 0)}%</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-line">
                <div
                  className={`h-1.5 rounded-full ${i === 0 ? "bg-accent" : "bg-muted/50"}`}
                  style={{ width: `${Math.max(1, 100 * probability)}%` }}
                />
              </div>
            </li>
          ))}
        </ol>
        <p className="mt-3 text-[11px] leading-snug text-muted">
          It always names one of nine tissues, even for a photo of a cat. Stroma and smooth muscle
          are its weakest classes.
        </p>
      </div>
    </div>
  );
}
