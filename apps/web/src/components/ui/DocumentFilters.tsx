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
  labs: { slug: string; name: string }[];
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

  const pillActive = "bg-accent text-white shadow-sm";
  const pillInactive = "bg-white border border-[var(--border)] text-[var(--muted)] hover:text-[var(--text)] hover:border-[var(--border-light)]";

  return (
    <div className="mb-8 space-y-5">
      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search documents..."
          className="flex-1 px-4 py-2.5 rounded-xl border border-[var(--border)] bg-white text-sm text-[var(--text)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent transition-all"
        />
        <button
          type="submit"
          className="px-5 py-2.5 rounded-xl bg-accent text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          Search
        </button>
      </form>

      {/* Lab filter */}
      <div>
        <div className="text-[11px] uppercase tracking-wider text-[var(--muted)] font-medium mb-2">Lab</div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => updateFilter("lab", undefined)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
              !currentLab ? pillActive : pillInactive
            }`}
          >
            All
          </button>
          {labs.map(lab => (
            <button
              key={lab.slug}
              onClick={() => updateFilter("lab", lab.slug === currentLab ? undefined : lab.slug)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
                lab.slug === currentLab ? pillActive : pillInactive
              }`}
            >
              {lab.name}
            </button>
          ))}
        </div>
      </div>

      {/* Type filter */}
      <div>
        <div className="text-[11px] uppercase tracking-wider text-[var(--muted)] font-medium mb-2">Document Type</div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => updateFilter("doc_type", undefined)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
              !currentType ? pillActive : pillInactive
            }`}
          >
            All
          </button>
          {docTypes.map(dt => (
            <button
              key={dt}
              onClick={() => updateFilter("doc_type", dt === currentType ? undefined : dt)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
                dt === currentType ? pillActive : pillInactive
              }`}
            >
              {dt.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Clear all */}
      {hasFilters && (
        <div>
          <a href="/documents" className="text-xs text-accent hover:underline font-medium">
            Clear all filters
          </a>
        </div>
      )}
    </div>
  );
}
