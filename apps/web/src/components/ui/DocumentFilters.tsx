"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, useCallback } from "react";

export function DocumentFilters({
  labs,
  docTypes,
  currentLab,
  currentType,
  currentSearch,
}: {
  labs: string[];
  docTypes: string[];
  currentLab?: string;
  currentType?: string;
  currentSearch?: string;
}) {
  const router = useRouter();
  const [search, setSearch] = useState(currentSearch ?? "");

  const updateFilter = useCallback((key: string, value: string | undefined) => {
    const params = new URLSearchParams();
    const current: Record<string, string | undefined> = {
      lab: currentLab,
      doc_type: currentType,
      search: currentSearch,
    };
    current[key] = value;
    Object.entries(current).forEach(([k, v]) => {
      if (v) params.set(k, v);
    });
    router.push(`/documents?${params.toString()}`);
  }, [router, currentLab, currentType, currentSearch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilter("search", search || undefined);
  };

  const hasFilters = currentLab || currentType || currentSearch;

  return (
    <div className="mb-6 space-y-3">
      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search documents..."
          className="flex-1 px-4 py-2 rounded-lg border border-[var(--border)] bg-surface-1 text-sm text-white placeholder:text-[var(--muted)] focus:outline-none focus:border-accent transition-colors"
        />
        <button
          type="submit"
          className="px-4 py-2 rounded-lg bg-surface-2 border border-[var(--border)] text-sm text-[var(--muted)] hover:text-white hover:border-[var(--border-light)] transition-colors"
        >
          Search
        </button>
      </form>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-[var(--muted)] mr-1">Lab:</span>
        <button
          onClick={() => updateFilter("lab", undefined)}
          className={`px-2.5 py-1 rounded-md text-xs transition-colors ${
            !currentLab ? "bg-accent text-white" : "bg-surface-2 text-[var(--muted)] hover:text-white"
          }`}
        >
          All
        </button>
        {labs.map(lab => (
          <button
            key={lab}
            onClick={() => updateFilter("lab", lab === currentLab ? undefined : lab)}
            className={`px-2.5 py-1 rounded-md text-xs transition-colors ${
              lab === currentLab ? "bg-accent text-white" : "bg-surface-2 text-[var(--muted)] hover:text-white"
            }`}
          >
            {lab}
          </button>
        ))}

        <span className="text-[var(--border)] mx-2">|</span>

        <span className="text-xs text-[var(--muted)] mr-1">Type:</span>
        <button
          onClick={() => updateFilter("doc_type", undefined)}
          className={`px-2.5 py-1 rounded-md text-xs transition-colors ${
            !currentType ? "bg-accent text-white" : "bg-surface-2 text-[var(--muted)] hover:text-white"
          }`}
        >
          All
        </button>
        {docTypes.map(dt => (
          <button
            key={dt}
            onClick={() => updateFilter("doc_type", dt === currentType ? undefined : dt)}
            className={`px-2.5 py-1 rounded-md text-xs font-mono transition-colors ${
              dt === currentType ? "bg-accent text-white" : "bg-surface-2 text-[var(--muted)] hover:text-white"
            }`}
          >
            {dt}
          </button>
        ))}

        {hasFilters && (
          <>
            <span className="text-[var(--border)] mx-2">|</span>
            <a href="/documents" className="text-xs text-accent hover:underline">
              Clear all
            </a>
          </>
        )}
      </div>
    </div>
  );
}
