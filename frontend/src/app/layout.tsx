import type { Metadata } from "next";
import { Public_Sans } from "next/font/google";

import "./globals.css";

const publicSans = Public_Sans({ variable: "--font-public-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "histostate: name the tissue in an H&E tile",
  description:
    "A small CNN, trained from scratch in PyTorch, that names the tissue type in a colorectal H&E tile. It runs in your browser.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${publicSans.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">{children}</body>
    </html>
  );
}
