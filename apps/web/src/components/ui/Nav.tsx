"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const links = [
  { href: "/", label: "Home" },
  { href: "/documents", label: "Model Cards" },
  { href: "/evals", label: "Eval Explorer" },
  { href: "/families", label: "Families" },
  { href: "/analysis", label: "Coverage" },
  { href: "/about", label: "About" },
];

export function Nav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="border-b border-[var(--border)] bg-[var(--bg)]/95 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-serif font-semibold text-[var(--text)] tracking-tight text-lg">
            Model Card Explorer
          </Link>
          <nav className="hidden md:flex gap-0.5">
            {links.map((l) => {
              const active = pathname === l.href || (l.href !== "/" && pathname.startsWith(l.href));
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                    active
                      ? "text-[var(--text)] bg-[var(--surface-2)]"
                      : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <a
          href="https://freesystems.substack.com/"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden sm:block text-xs text-[var(--muted)] hover:text-[var(--text)] transition-colors"
        >
          by Free Systems Lab
        </a>
        {/* Mobile menu button */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden p-2 text-[var(--muted)] hover:text-[var(--text)]"
          aria-label="Toggle menu"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
            {mobileOpen ? (
              <path d="M5 5l10 10M15 5L5 15" />
            ) : (
              <path d="M3 6h14M3 10h14M3 14h14" />
            )}
          </svg>
        </button>
      </div>
      {/* Mobile menu */}
      {mobileOpen && (
        <nav className="md:hidden border-t border-[var(--border)] bg-[var(--bg)] px-6 py-4 space-y-1">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setMobileOpen(false)}
                className={`block px-3 py-2 rounded-md text-sm ${
                  active ? "text-[var(--text)] bg-[var(--surface-2)]" : "text-[var(--muted)] hover:text-[var(--text)]"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
