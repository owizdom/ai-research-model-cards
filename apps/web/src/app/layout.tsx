import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Nav } from "@/components/ui/Nav";

export const metadata: Metadata = {
  title: "AI Policy Intelligence",
  description: "Track AI lab safety policies and measure political bias in model outputs",
  openGraph: {
    title: "AI Policy Intelligence",
    description: "Track AI lab safety policies and measure political bias in model outputs",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface-0 text-white antialiased">
        <Providers>
          <Nav />
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
            {children}
          </main>
          <footer className="border-t border-[var(--border)] mt-16">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[var(--muted)]">
                <div className="flex items-center gap-4">
                  <span className="font-medium text-white">AI Policy Intel</span>
                  <span>
                    Built by{" "}
                    <a href="https://freesystems.substack.com/" target="_blank" rel="noopener noreferrer" className="text-accent hover:text-white transition-colors">
                      Free Systems Lab
                    </a>
                  </span>
                </div>
                <div className="flex items-center gap-6">
                  <a href="/about" className="hover:text-white transition-colors">About</a>
                  <a href="https://github.com/owizdom/ai-research-model-cards" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
                    GitHub
                  </a>
                  <a href="https://freesystems.substack.com/" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
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
