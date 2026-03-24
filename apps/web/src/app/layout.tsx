import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Nav } from "@/components/ui/Nav";

export const metadata: Metadata = {
  title: "Model Card Explorer",
  description: "Explore and compare AI model cards, safety evaluations, and governance data across major AI labs",
  openGraph: {
    title: "Model Card Explorer",
    description: "Explore and compare AI model cards, safety evaluations, and governance data across major AI labs",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[var(--bg)] text-[var(--text)] antialiased">
        <Providers>
          <Nav />
          <main className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 py-12 sm:py-16">
            {children}
          </main>
          <footer className="border-t border-[var(--border)] mt-24">
            <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 py-10">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[var(--muted)]">
                <div className="flex items-center gap-4">
                  <span className="font-semibold text-[var(--text)]">Model Card Explorer</span>
                  <span>
                    Built by{" "}
                    <a href="https://freesystems.substack.com/" target="_blank" rel="noopener noreferrer" className="text-accent hover:text-[var(--text)] transition-colors">
                      Free Systems Lab
                    </a>
                  </span>
                </div>
                <div className="flex items-center gap-6">
                  <a href="/about" className="hover:text-[var(--text)] transition-colors">About</a>
                  <a href="https://github.com/owizdom/ai-research-model-cards" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--text)] transition-colors">
                    GitHub
                  </a>
                  <a href="https://freesystems.substack.com/" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--text)] transition-colors">
                    Substack
                  </a>
                </div>
              </div>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
