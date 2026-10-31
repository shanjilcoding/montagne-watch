import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { SiteHeader } from "@/components/site-header";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Montagne Watch", template: "%s | Montagne Watch" },
  description: "Unofficial live availability, restock history, and catalog statistics for Montagne Parfums.",
  metadataBase: new URL("https://montagne-watch.vercel.app"),
  openGraph: {
    title: "Montagne Watch",
    description: "Live availability and restock history for the Montagne Parfums catalog.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <a className="skip-link" href="#main-content">Skip to content</a>
        <SiteHeader />
        <div id="main-content">{children}</div>
        <footer className="site-footer"><div><strong>Montagne Watch</strong><span>Unofficial and not affiliated with Montagne Parfums.</span></div><a href="/about">About the data</a></footer>
      </body>
    </html>
  );
}
