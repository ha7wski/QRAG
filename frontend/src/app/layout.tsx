import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import { S } from "@/lib/strings";

export const metadata: Metadata = {
  title: S.app.title,
  description: S.app.description,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Direction is declared exactly once, here (design D1). Every component
  // inherits it; from now on an element-level `dir` is only ever an LTR island,
  // or an override re-establishing RTL inside one.
  return (
    <html lang="ar" dir="rtl">
      {/* Both typefaces are self-hosted: vendored woff2 declared in
          globals.css, so there is no runtime request to fonts.googleapis.com
          and no build-time fetch either. See app/fonts/README.md. */}
      <body>
        <Navbar />
        {/* Offset for the fixed sidebar on md+; full width (drawer) on mobile. */}
        <main className="px-4 py-6 md:ml-64 md:px-8">
          <div className="mx-auto max-w-4xl">{children}</div>
        </main>
      </body>
    </html>
  );
}
