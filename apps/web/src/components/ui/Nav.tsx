"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

type NavLink = { href: string; label: string };
type NavItem = NavLink | { label: string; children: NavLink[] };

// Broad → niche progression: Home (the finding), Safety topics + Trends (analyses),
// Sources (the underlying corpus: Evals → Families → Cards), About (methodology).
const navItems: NavItem[] = [
  { href: "/", label: "Home" },
  { href: "/analysis", label: "Safety topics" },
  { href: "/trends", label: "Trends" },
  {
    label: "Sources",
    children: [
      { href: "/evals", label: "Evals" },
      { href: "/families", label: "Families" },
      { href: "/documents", label: "Cards" },
    ],
  },
  { href: "/about", label: "About" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(href + "/");
}

function isGroupActive(pathname: string, children: NavLink[]): boolean {
  return children.some(c => isActive(pathname, c.href));
}

export function Nav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  // Close dropdown on outside click or Escape
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpenDropdown(null);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpenDropdown(null);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  // Close dropdown when route changes
  useEffect(() => {
    setOpenDropdown(null);
    setMobileOpen(false);
  }, [pathname]);

  return (
    <header className="border-b border-[var(--border)] bg-[var(--bg)]/95 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-serif font-semibold text-[var(--text)] tracking-tight text-lg">
            Model Card Explorer
          </Link>
          <nav className="hidden md:flex gap-0.5" ref={dropdownRef}>
            {navItems.map((item) => {
              if ("children" in item) {
                const active = isGroupActive(pathname, item.children);
                const open = openDropdown === item.label;
                return (
                  <div
                    key={item.label}
                    className="relative"
                    onMouseEnter={() => setOpenDropdown(item.label)}
                    onMouseLeave={() => setOpenDropdown(null)}
                  >
                    <button
                      onClick={() => setOpenDropdown(open ? null : item.label)}
                      className={`px-3 py-1.5 rounded-md text-sm transition-colors flex items-center gap-1 ${
                        active || open
                          ? "text-[var(--text)] bg-[var(--surface-2)]"
                          : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]"
                      }`}
                      aria-expanded={open}
                      aria-haspopup="true"
                    >
                      {item.label}
                      <svg
                        width="10"
                        height="10"
                        viewBox="0 0 12 12"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        className={`transition-transform ${open ? "rotate-180" : ""}`}
                      >
                        <path d="M3 4.5l3 3 3-3" />
                      </svg>
                    </button>
                    {open && (
                      <div className="absolute left-0 top-full pt-1 min-w-[180px]">
                        <div className="rounded-lg border border-[var(--border)] bg-white shadow-md py-1.5">
                          {item.children.map((child) => {
                            const childActive = isActive(pathname, child.href);
                            return (
                              <Link
                                key={child.href}
                                href={child.href}
                                className={`block px-3 py-2 text-sm transition-colors ${
                                  childActive
                                    ? "text-[var(--text)] bg-[var(--surface-2)] font-medium"
                                    : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-1)]"
                                }`}
                              >
                                {child.label}
                              </Link>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              }

              const active = isActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                    active
                      ? "text-[var(--text)] bg-[var(--surface-2)]"
                      : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="hidden sm:block" />
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
          {navItems.map((item) => {
            if ("children" in item) {
              return (
                <div key={item.label} className="pt-2">
                  <div className="px-3 py-1 text-xs uppercase tracking-wide text-[var(--muted)]">
                    {item.label}
                  </div>
                  {item.children.map((child) => {
                    const childActive = isActive(pathname, child.href);
                    return (
                      <Link
                        key={child.href}
                        href={child.href}
                        className={`block px-3 py-2 rounded-md text-sm ${
                          childActive
                            ? "text-[var(--text)] bg-[var(--surface-2)]"
                            : "text-[var(--muted)] hover:text-[var(--text)]"
                        }`}
                      >
                        {child.label}
                      </Link>
                    );
                  })}
                </div>
              );
            }
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block px-3 py-2 rounded-md text-sm ${
                  active ? "text-[var(--text)] bg-[var(--surface-2)]" : "text-[var(--muted)] hover:text-[var(--text)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
