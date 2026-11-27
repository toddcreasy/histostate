"use client";

import Link from "next/link";

import { DocsToggle } from "./help";
import PilotBioMark from "./pilotbio-mark";

// The same header as rwe-workbench (ehr-rwe-eln frontend/app/shell.tsx): the app's mark, name,
// and line on the left; PilotBio, the source, help, and the theme on the right.

const REPO = "https://github.com/toddcreasy/histostate";

// A tile cut into four, one of them named: the classifier's job.
export function Mark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <rect x="1.5" y="1.5" width="37" height="37" rx="9" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <rect x="10" y="10" width="9" height="9" rx="1.5" fill="currentColor" />
      <rect x="21" y="10" width="9" height="9" rx="1.5" fill="none" stroke="currentColor" strokeWidth="2" />
      <rect x="10" y="21" width="9" height="9" rx="1.5" fill="none" stroke="currentColor" strokeWidth="2" />
      <rect x="21" y="21" width="9" height="9" rx="1.5" fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function ThemeToggle() {
  function toggle() {
    const dark = document.documentElement.classList.toggle("dark");
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch {}
  }
  return (
    <button
      onClick={toggle}
      aria-label="Switch light or dark mode"
      data-tip="Switch to dark mode"
      data-tip-dark="Switch to light mode"
      className="tip rounded-full p-2 text-muted hover:bg-accent-soft hover:text-ink"
    >
      <svg viewBox="0 0 24 24" className="h-5 w-5 dark:hidden" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" strokeLinejoin="round" />
      </svg>
      <svg viewBox="0 0 24 24" className="hidden h-5 w-5 dark:block" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" strokeLinecap="round" />
      </svg>
    </button>
  );
}

function GitHub() {
  return (
    <a
      href={REPO}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Source on GitHub"
      data-tip="Source code on GitHub"
      className="tip rounded-full p-2 text-muted hover:bg-accent-soft hover:text-ink"
    >
      <svg viewBox="0 0 16 16" className="h-5 w-5" fill="currentColor" aria-hidden="true">
        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
      </svg>
    </a>
  );
}

export default function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-card">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link href="/" className="flex items-center gap-3">
          <Mark className="h-10 w-10 shrink-0 text-ink" />
          <span>
            <span className="block font-serif text-2xl leading-tight font-semibold text-ink">histostate</span>
            <span className="block text-sm text-muted">Tissue types in colorectal H&amp;E, named in your browser</span>
          </span>
        </Link>
        <div className="flex items-center gap-1">
          <a
            href="https://pilotbio.io"
            target="_blank"
            rel="noopener noreferrer"
            title="PilotBio"
            className="mr-2 flex items-center gap-1.5 text-sm font-medium text-ink hover:opacity-80"
          >
            <PilotBioMark />
            <span className="hidden sm:inline">Todd Creasy</span>
          </a>
          <GitHub />
          <DocsToggle />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
