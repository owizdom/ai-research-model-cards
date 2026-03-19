import Link from "next/link";

const links = [
  { href: "/", label: "Home" },
  { href: "/documents", label: "Documents" },
  { href: "/analysis", label: "Safety Coverage" },
  { href: "/probes", label: "Model Bias Tracker" },
];

export function Nav() {
  return (
    <header className="border-b border-[var(--border)] bg-surface-1 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-semibold text-white tracking-tight">
            AI Policy Intel
          </Link>
          <nav className="flex gap-6">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="text-sm text-[var(--muted)] hover:text-white transition-colors"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
        <a
          href="https://freesystems.substack.com/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-[var(--muted)] hover:text-white transition-colors"
        >
          by Free Systems Lab
        </a>
      </div>
    </header>
  );
}
