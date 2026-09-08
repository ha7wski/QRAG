import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Quran RAG",
  description: "Explore the Quran with retrieval-augmented search and analysis.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
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
