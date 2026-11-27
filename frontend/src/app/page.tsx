import Classifier from "./classifier";
import { PageHelp } from "./home-help";
import Released, { Dot } from "./released";

const REPO = "https://github.com/toddcreasy/histostate";
const WALKTHROUGH = `${REPO}/blob/main/docs/walkthrough.md`;

const STATS = [
  { value: "94.7%", label: "accuracy on held-out tiles from a second clinical center" },
  { value: "93,193", label: "weights, trained from scratch in PyTorch" },
  { value: "9", label: "tissue types in colorectal H&E (hematoxylin and eosin) slides" },
  { value: "0", label: "pretrained weights or trainer libraries" },
];

const FINDINGS = [
  {
    image: "staining_shift.png",
    title: "Two clinics, two stains",
    body: "Validation tiles came from the same clinic as training and scored 97.8%. The test tiles come from a second center, where the staining looks different. So I split those into a set to tune on and a set to score once.",
    link: `${WALKTHROUGH}#6-build-a-validation-set-that-can-see-the-shift`,
  },
  {
    image: "shortcut_28px_channel39.png",
    title: "A shortcut at 28 pixels",
    body: "The 28-pixel model's best stroma and muscle feature fired hardest on darkly stained tiles. Stain color helps on the home clinic's slides and breaks on everyone else's.",
    link: `${WALKTHROUGH}#7-look-inside-the-model`,
  },
  {
    image: "fibers_64px_channel62.png",
    title: "Real structure at 64 pixels",
    body: "At 64 pixels the same kind of feature fires on long, parallel, spindle-shaped nuclei, which is what smooth muscle looks like. Final test accuracy rose from 91.4% to 94.7%; more resolution helped more than more depth.",
    link: `${WALKTHROUGH}#8-resolution-or-depth`,
  },
];

export default function Home() {
  return (
    <>
      <header className="bg-hero text-hero-text">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1fr_minmax(0,30rem)] lg:py-16">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-accent">
              A tissue classifier, built from the bottom up
            </p>
            <h1 className="mt-3 text-4xl font-bold leading-tight sm:text-5xl">
              Name the tissue in a colorectal H&amp;E tile
              <PageHelp />
            </h1>
            <p className="mt-4 max-w-xl text-lg text-hero-muted">
              A small CNN (convolutional neural network) I trained myself, from gradient descent on
              two weights up. It runs in your browser: pick a tile and it answers in milliseconds.
            </p>
            <dl className="mt-8 grid max-w-xl grid-cols-2 gap-3">
              {STATS.map(({ value, label }) => (
                <div key={label} className="rounded-lg border border-white/10 bg-white/5 p-4">
                  <dt className="sr-only">{label}</dt>
                  <dd className="text-2xl font-bold">{value}</dd>
                  <dd className="mt-1 text-sm leading-snug text-hero-muted">{label}</dd>
                </div>
              ))}
            </dl>
            <nav className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm font-semibold">
              <a className="underline decoration-accent decoration-2 underline-offset-4" href={REPO}>
                Source on GitHub
              </a>
              <a className="underline decoration-accent decoration-2 underline-offset-4" href={WALKTHROUGH}>
                Walkthrough
              </a>
              <a
                className="underline decoration-accent decoration-2 underline-offset-4"
                href={`${REPO}/blob/main/docs/software.md`}
              >
                Software
              </a>
            </nav>
          </div>
          <Classifier />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <h2 className="text-2xl font-bold text-ink">What it learned, and what fooled it</h2>
        <p className="mt-2 max-w-3xl text-muted">
          A 97% validation score said little about slides from another clinic. Most of the project
          went into finding that out and fixing it honestly.
        </p>
        <div className="mt-8 grid gap-8 md:grid-cols-3">
          {FINDINGS.map(({ image, title, body, link }) => (
            <article key={title} className="flex flex-col rounded-xl bg-card p-5 ring-1 ring-line">
              <a href={`/images/${image}`} title="Open the full-size figure">
                {/* eslint-disable-next-line @next/next/no-img-element -- static PNG figures, no optimizer in a static export */}
                <img src={`/images/${image}`} alt={title} className="w-full rounded ring-1 ring-line" />
              </a>
              <h3 className="mt-4 font-bold text-ink">{title}</h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-text">{body}</p>
              <a className="mt-3 text-sm font-semibold text-accent hover:underline" href={link}>
                Read this step in the walkthrough
              </a>
            </article>
          ))}
        </div>
      </main>

      {/* Same layout as glia-nav's footer: the disclaimer, then license, source, and release. */}
      <footer className="border-t border-line bg-card">
        <div className="mx-auto max-w-6xl space-y-2 px-4 py-4 text-[13px] text-muted sm:px-6">
          <p>
            A learning project, not a medical device. Nothing here is for clinical or diagnostic
            use.
          </p>
          <p>
            Data: PathMNIST from MedMNIST (Yang et al., Scientific Data, 2023), built from
            NCT-CRC-HE-100K and CRC-VAL-HE-7K (Kather et al., PLOS Medicine, 2019), CC BY 4.0.
          </p>
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <a
              href={`${REPO}/blob/main/LICENSE`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-ink underline-offset-4 hover:underline"
            >
              Apache 2.0 license
            </a>
            <Dot />
            <a
              href={REPO}
              target="_blank"
              rel="noopener noreferrer"
              className="text-ink underline-offset-4 hover:underline"
            >
              Source on GitHub
            </a>
            <Released />
          </p>
        </div>
      </footer>
    </>
  );
}
