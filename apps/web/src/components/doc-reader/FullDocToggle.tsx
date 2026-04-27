"use client";
import { useState } from "react";

export function FullDocToggle({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm text-[var(--muted)] hover:text-[var(--text)] border border-[var(--border)] rounded-lg px-4 py-2 transition-colors mb-6"
      >
        <span>{open ? "Hide" : "Show"} full document</span>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
      {open && children}
    </div>
  );
}
