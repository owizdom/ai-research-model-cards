"use client";
import { useState } from "react";
import type { Document } from "@/lib/types";
import Link from "next/link";

export function CompareDropdown({
  currentDocId, allDocs,
}: {
  currentDocId: number;
  allDocs: Document[];
}) {
  const [open, setOpen] = useState(false);
  const others = allDocs.filter(d => d.id !== currentDocId && d.doc_type === "model_card");

  // Group by lab for readability
  const byLab = new Map<string, Document[]>();
  for (const d of others) {
    const key = d.lab_name ?? "Other";
    if (!byLab.has(key)) byLab.set(key, []);
    byLab.get(key)!.push(d);
  }

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="text-sm px-3 py-1.5 rounded-lg border border-[var(--border)] text-[var(--muted)] hover:text-[var(--text)] hover:border-[var(--border-light)] transition-colors flex items-center gap-1.5"
      >
        Compare to…
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full mt-1 z-20 w-80 max-h-[24rem] overflow-y-auto border border-[var(--border)] rounded-lg bg-white shadow-lg">
            {Array.from(byLab.entries()).map(([labName, docs]) => (
              <div key={labName} className="border-b border-[var(--border)] last:border-b-0">
                <div className="px-3 py-2 text-[11px] uppercase tracking-wide text-[var(--muted)] bg-[var(--surface-2)]/50 sticky top-0">
                  {labName}
                </div>
                {docs.map(d => (
                  <Link
                    key={d.id}
                    href={`/compare?a=${currentDocId}&b=${d.id}`}
                    className="block px-3 py-2 text-sm hover:bg-[var(--surface-1)] transition-colors"
                    onClick={() => setOpen(false)}
                  >
                    {d.title}
                  </Link>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
