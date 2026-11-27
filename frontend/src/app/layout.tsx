import type { Metadata } from "next";
import { Public_Sans, Source_Serif_4 } from "next/font/google";

import "./globals.css";
import Header from "./header";
import { HelpProvider } from "./help";

const publicSans = Public_Sans({ variable: "--font-public-sans", subsets: ["latin"] });

// The header's name, as on rwe-workbench.
const serif = Source_Serif_4({ variable: "--font-serif-display", subsets: ["latin"], weight: ["600"] });

export const metadata: Metadata = {
  title: "histostate: name the tissue in an H&E tile",
  description:
    "A small CNN, trained from scratch in PyTorch, that names the tissue type in a colorectal H&E tile. It runs in your browser.",
};

// Runs before first paint, as on rwe-workbench: the saved theme, else the system setting. Help on
// the page is on unless the visitor turned it off, and its buttons pulse until the first note is
// opened. With help on and a wide enough screen, the help panel opens unless it was closed earlier
// in this session (help.tsx, opensAtLaunch), and the page makes room for it now so nothing shifts.
const THEME = `try{var t=localStorage.getItem("theme");if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))document.documentElement.classList.add("dark");var h=document.documentElement;if(localStorage.getItem("docs")==="off")h.classList.add("docs-off");else if(sessionStorage.getItem("help-panel")!=="closed"&&matchMedia("(min-width: 1100px)").matches)h.classList.add("help-panel-open");if(!localStorage.getItem("help-seen"))document.documentElement.classList.add("help-new")}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning className={`${publicSans.variable} ${serif.variable} h-full antialiased`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME }} />
      </head>
      <body className="min-h-full font-sans">
        <HelpProvider>
          <Header />
          {children}
        </HelpProvider>
      </body>
    </html>
  );
}
