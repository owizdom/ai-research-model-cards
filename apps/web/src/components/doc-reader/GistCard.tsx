import type { GistFields } from "@/lib/types";

export function GistCard({ gist }: { gist: GistFields }) {
  const fields: { label: string; value: string | null }[] = [
    { label: "Overview", value: gist.overview },
    { label: "Capability claim", value: gist.capability_claim },
    { label: "Sharpest risk disclosure", value: gist.sharpest_risk },
    { label: "Deployment scope", value: gist.deployment_scope },
  ].filter(f => f.value);

  if (fields.length === 0) return null;

  return (
    <div className="border border-[var(--border)] rounded-xl bg-white p-6 mb-8">
      <div className="text-xs uppercase tracking-wide text-[var(--muted)] mb-3">
        60-second brief
      </div>
      <dl className="space-y-3">
        {fields.map(f => (
          <div key={f.label} className="flex flex-col sm:flex-row gap-2 sm:gap-4">
            <dt className="sm:w-44 shrink-0 text-sm font-semibold text-[var(--text)]">
              {f.label}
            </dt>
            <dd className="text-sm text-[var(--muted)] leading-relaxed flex-1 italic">
              &ldquo;{cleanQuote(f.value!)}&rdquo;
            </dd>
          </div>
        ))}
      </dl>
      <p className="text-[11px] text-[var(--muted)] mt-4 pt-3 border-t border-[var(--border)]">
        Snippets lifted verbatim from the document. Heuristic extraction — may
        miss nuance; always verify against the source.
      </p>
    </div>
  );
}

function cleanQuote(s: string): string {
  // Trim weird trailing punctuation/numbers leaked from page artifacts
  return s.trim().replace(/\s+/g, " ").replace(/^\W+|\W+$/g, m => (m.endsWith(".") ? m : ""));
}
