"use client";

import { usePathname } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { createPortal } from "react-dom";

// Help on the page, from rwe-workbench (ehr-rwe-eln frontend/app/help.tsx) without its glossary:
// a switch in the header shows or hides every "?" button. Each button shows a note about one
// region of the page (the nearest element marked data-help) in a panel docked at the right edge,
// which the page makes room for. The panel opens on the page's own note when a visit starts with
// help on, and closes only from its X or the header switch.

const PANEL_WIDTH = 380;
// The narrowest screen where the page makes room for the panel (globals.css, .help-panel-open).
const WIDE = 1100;
// The id of each page's own note (the one marked <Help page>).
const PAGE = "page";

// Which note the panel shows, and on which page it was picked. null: the panel is closed.
type Active = { path: string; id: string } | null;

const HelpContext = createContext<{
  shown: string | null;
  show: (id: string) => void;
  close: () => void;
  register: (id: string, title: string) => () => void;
  panelEl: HTMLElement | null;
}>({ shown: null, show: () => {}, close: () => {}, register: () => () => {}, panelEl: null });

// The panel's launch state, also read by the script in layout.tsx before first paint: open when
// help is on and the screen is wide enough for the page to make room for it, unless the visitor
// closed it earlier in this browser session. Narrower, it waits for a "?".
const noChange = () => () => {};
function opensAtLaunch() {
  if (document.documentElement.classList.contains("docs-off")) return false;
  if (!matchMedia(`(min-width: ${WIDE}px)`).matches) return false;
  try {
    return sessionStorage.getItem("help-panel") !== "closed";
  } catch {
    return true;
  }
}
function hintUnseen() {
  try {
    // Someone who has opened a "?" note before already knows where help is.
    return !localStorage.getItem("hint-seen") && !localStorage.getItem("help-seen");
  } catch {
    return false;
  }
}
function rememberClosed(closed: boolean) {
  try {
    if (closed) sessionStorage.setItem("help-panel", "closed");
    else sessionStorage.removeItem("help-panel");
  } catch {}
}

export function HelpProvider({ children }: { children: ReactNode }) {
  const path = usePathname() ?? "/";
  // undefined until the visitor opens or closes anything: the launch state decides.
  const [active, setActive] = useState<Active | undefined>(undefined);
  const launch = useSyncExternalStore(noChange, opensAtLaunch, () => false);
  const [panelEl, setPanelEl] = useState<HTMLElement | null>(null);
  // The notes on the page now, by id, with their titles.
  const [notes, setNotes] = useState<ReadonlyMap<string, string>>(new Map());
  const register = useCallback((id: string, title: string) => {
    setNotes((m) => new Map(m).set(id, title));
    return () =>
      setNotes((m) => {
        const next = new Map(m);
        next.delete(id);
        return next;
      });
  }, []);

  const open = active === undefined ? launch : active !== null;
  const wanted = !open ? null : active && active.path === path ? active.id : PAGE;
  const shown = wanted === null ? null : notes.has(wanted) ? wanted : notes.has(PAGE) ? PAGE : null;

  const show = (id: string) => {
    setActive({ path, id });
    rememberClosed(false);
  };
  const close = () => {
    setActive(null);
    rememberClosed(true);
  };

  // The page makes room for the panel (globals.css, .help-panel-open).
  useEffect(() => {
    if (!open) return;
    const html = document.documentElement;
    html.classList.add("help-panel-open");
    return () => html.classList.remove("help-panel-open");
  }, [open]);

  return (
    <HelpContext.Provider value={{ shown, show, close, register, panelEl }}>
      {children}
      {open && (
        <aside
          aria-label="Help"
          style={{ width: PANEL_WIDTH }}
          className="fixed top-0 right-0 z-40 flex h-dvh max-w-full flex-col border-l border-grid bg-card font-sans text-sm shadow-lg"
        >
          <div className="flex items-start justify-between gap-2 border-b border-line px-5 py-4">
            <div className="text-base font-semibold text-ink">{shown ? notes.get(shown) : "Help"}</div>
            <button
              type="button"
              onClick={close}
              aria-label="Close help"
              className="-mt-1 -mr-2 rounded-full p-1 text-muted hover:bg-accent-soft hover:text-ink"
            >
              <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          <div ref={setPanelEl} className="flex-1 overflow-y-auto overscroll-contain">
            {shown === null && <p className="px-5 py-4 text-muted">There is no help for this page.</p>}
          </div>
        </aside>
      )}
    </HelpContext.Provider>
  );
}

// Same pattern as the theme: a class on <html>, saved in localStorage, set before first paint by
// the script in layout.tsx so the buttons never flash in for someone who turned them off.
const watchHtmlClass = (change: () => void) => {
  const observer = new MutationObserver(change);
  observer.observe(document.documentElement, { attributeFilter: ["class"] });
  return () => observer.disconnect();
};

export function DocsToggle() {
  const { show, close } = useContext(HelpContext);
  const on = useSyncExternalStore(
    watchHtmlClass,
    () => !document.documentElement.classList.contains("docs-off"),
    () => true,
  );
  // A first visit with help on gets a one-time pointer to this switch.
  const unseen = useSyncExternalStore(noChange, hintUnseen, () => false);
  const [dismissed, setDismissed] = useState(false);
  const hint = on && unseen && !dismissed;
  function dismiss() {
    setDismissed(true);
    try {
      localStorage.setItem("hint-seen", "1");
    } catch {}
  }
  function toggle() {
    dismiss();
    const off = document.documentElement.classList.toggle("docs-off");
    if (off) close();
    else show(PAGE);
    try {
      localStorage.setItem("docs", off ? "off" : "on");
    } catch {}
  }
  return (
    <span className="relative inline-flex">
      <button
        onClick={toggle}
        aria-pressed={on}
        aria-label={on ? "Hide help on the page" : "Show help on the page"}
        data-tip={hint ? undefined : on ? "Hide help on the page" : "Show help on the page"}
        className={`tip rounded-full p-2 hover:text-ink ${on ? "bg-accent-soft text-ink" : "text-muted hover:bg-accent-soft"}`}
      >
        {on ? (
          // On: a solid circle with the question mark cut out of it.
          <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
            <circle cx="12" cy="12" r="10" fill="currentColor" />
            <path d="M9.5 9.3a2.6 2.6 0 0 1 5 .9c0 1.7-2.5 2.2-2.5 3.8" fill="none" stroke="var(--card)" strokeWidth="2" strokeLinecap="round" />
            <circle cx="12" cy="17.2" r="1.1" fill="var(--card)" />
          </svg>
        ) : (
          // Off: the outline, struck through.
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path d="M9.5 9.3a2.6 2.6 0 0 1 5 .9c0 1.7-2.5 2.2-2.5 3.8" strokeLinecap="round" />
            <circle cx="12" cy="17" r="0.6" fill="currentColor" />
            <path d="M4 4l16 16" strokeLinecap="round" />
          </svg>
        )}
      </button>
      {hint && (
        <div role="status" className="absolute top-full right-0 z-50 mt-3 w-64 rounded-lg bg-ink p-3 font-sans text-sm leading-relaxed text-card shadow-lg">
          <span aria-hidden="true" className="absolute -top-1.5 right-3 h-3 w-3 rotate-45 bg-ink" />
          <p>
            New here? Each <strong>?</strong> on the page explains the part next to it. This button turns help on and
            off.
          </p>
          <button
            type="button"
            onClick={dismiss}
            className="mt-2 rounded-full bg-card px-3 py-1 text-xs font-semibold text-ink hover:opacity-90"
          >
            Got it
          </button>
        </div>
      )}
    </span>
  );
}

// page: this is the page's own note, the one the panel opens on.
export function Help({
  title,
  children,
  page = false,
  className = "",
}: {
  title: string;
  children: ReactNode;
  page?: boolean;
  className?: string;
}) {
  const uid = useId();
  const id = page ? PAGE : uid;
  const { shown: current, show, register, panelEl } = useContext(HelpContext);
  const shown = current === id;
  const button = useRef<HTMLButtonElement>(null);
  const note = useRef<HTMLDivElement>(null);

  // Before paint, so the panel never shows "no help" for a page that has some.
  useLayoutEffect(() => register(id, title), [register, id, title]);

  // Outline the region this note is about while the panel shows it.
  useLayoutEffect(() => {
    if (!shown) return;
    const region = (button.current?.closest("[data-help]") as HTMLElement | null) ?? button.current?.parentElement;
    region?.setAttribute("data-help-active", "");
    return () => region?.removeAttribute("data-help-active");
  }, [shown]);

  return (
    <>
      <button
        ref={button}
        type="button"
        onClick={() => {
          // Clicking the "?" whose note is showing leaves it showing.
          show(id);
          requestAnimationFrame(() => note.current?.focus({ preventScroll: true }));
          // The first note opened stops the pulse on every "?" for good.
          document.documentElement.classList.remove("help-new");
          try {
            localStorage.setItem("help-seen", "1");
          } catch {}
        }}
        aria-expanded={shown}
        aria-controls={shown ? `${id}-note` : undefined}
        aria-label={`About: ${title}`}
        data-tip="What's this?"
        className={`help-button tip inline-flex h-[1.3em] w-[1.3em] shrink-0 items-center justify-center rounded-full bg-accent align-middle font-sans text-[min(0.75em,16px)] leading-none font-bold text-card before:absolute before:top-1/2 before:left-1/2 before:h-6 before:w-6 before:-translate-x-1/2 before:-translate-y-1/2 before:content-[''] shadow-sm hover:opacity-85 ${
          shown ? "ring-2 ring-accent ring-offset-2 ring-offset-card" : ""
        } ${className}`}
      >
        ?
      </button>
      {shown &&
        panelEl &&
        createPortal(
          <div
            ref={note}
            id={`${id}-note`}
            role="region"
            aria-label={title}
            tabIndex={-1}
            className="px-5 py-4 leading-relaxed font-normal tracking-normal normal-case outline-none"
          >
            <div className="flex flex-col gap-2 text-muted [&_strong]:font-medium [&_strong]:text-ink">{children}</div>
          </div>,
          panelEl,
        )}
    </>
  );
}
