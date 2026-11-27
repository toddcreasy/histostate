// Copy the README's diagrams (docs/, drawn by scripts/make_diagrams.py) into public/diagrams/, so
// the site serves them at /diagrams/*.svg, where their hover notes and links work. docs/ stays the
// only source; the copies are gitignored. Runs before `next dev` and `next build`.
import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("public/diagrams", { recursive: true });
for (const name of ["architecture.svg", "model.svg"]) {
  copyFileSync(`../docs/${name}`, `public/diagrams/${name}`);
}
