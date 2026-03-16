import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Nav } from "@/components/ui/Nav";

export const metadata: Metadata = {
  title: "AI Policy Intelligence",
  description: "Track AI lab policy documents and model political behavior over time",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface-0 text-white">
        <Providers>
          <Nav />
          <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
