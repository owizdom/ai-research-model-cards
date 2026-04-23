"use client";
import { useState } from "react";
import type { DocumentContent, EvalResult } from "@/lib/types";
import { formatDate } from "@/lib/utils";

type ReaderMode = "overview" | "researcher" | "safety" | "journalist";

interface Props {
  content: DocumentContent;
  docTitle: string;
  labName: string | null;
  docType: string;
  sourceUrl: string | null;
  evals: EvalResult[];
}

// Each mode reorders which sections render first. Same underlying data.
const MODE_ORDER: Record<ReaderMode, string[]> = {
  overview: ["tldr", "evals", "capability", "safety", "deployment", "limitations", "whats_new"],
  researcher: ["tldr", "capability", "evals", "safety", "mitigations", "limitations", "whats_new"],
  safety: ["safety", "mitigations", "limitations", "tldr", "evals", "whats_new"],
  journalist: ["tldr", "whats_new", "safety", "capability", "evals", "limitations"],
};

const MODE_LABEL: Record<ReaderMode, string> = {
  overview: "Overview",
  researcher: "Researcher",
  safety: "Safety",
  journalist: "Journalist",
};

export function DocumentSummary({
  content, docTitle, labName, docType, sourceUrl, evals,
}: Props) {
  const [mode, setMode] = useState<ReaderMode>("overview");
  const g = content.gist;
  if (!g) return null;

  const hasAnyClaim =
    g.tldr ||
    g.capability_claims.length ||
    g.safety_findings.length ||
    g.mitigations.length ||
    g.deployment_scope.length ||
    g.limitations.length ||
    g.whats_new.length;

  if (!hasAnyClaim) return null;

  const sections: Record<string, { render: () => React.ReactNode; hasContent: boolean }> = {
    tldr: {
      hasContent: !!g.tldr,
      render: () => g.tldr ? (
        <Section key="tldr" label="TL;DR" style="prose">
          <p className="text-[15px] leading-relaxed text-[var(--text)] italic">
            &ldquo;{g.tldr}&rdquo;
          </p>
        </Section>
      ) : null,
    },
    evals: {
      hasContent: evals.length > 0,
      render: () => <EvalsSection key="evals" evals={evals} />,
    },
    capability: {
      hasContent: g.capability_claims.length > 0,
      render: () => (
        <QuoteSection
          key="capability"
          label="Capability claim"
          quotes={g.capability_claims}
        />
      ),
    },
    safety: {
      hasContent: g.safety_findings.length > 0,
      render: () => (
        <QuoteSection
          key="safety"
          label="Safety findings"
          quotes={g.safety_findings}
          accent
        />
      ),
    },
    mitigations: {
      hasContent: g.mitigations.length > 0,
      render: () => (
        <QuoteSection
          key="mitigations"
          label="Mitigations"
          quotes={g.mitigations}
        />
      ),
    },
    deployment: {
      hasContent: g.deployment_scope.length > 0,
      render: () => (
        <QuoteSection
          key="deployment"
          label="Deployment scope"
          quotes={g.deployment_scope}
        />
      ),
    },
    limitations: {
      hasContent: g.limitations.length > 0,
      render: () => (
        <QuoteSection
          key="limitations"
          label="Limitations the lab flags"
          quotes={g.limitations}
        />
      ),
    },
    whats_new: {
      hasContent: g.whats_new.length > 0,
      render: () => (
        <Section key="whats_new" label="What&rsquo;s new">
          <ul className="space-y-1.5">
            {g.whats_new.map((b, i) => (
              <li key={i} className="text-sm text-[var(--text)] flex gap-2">
                <span className="text-[var(--muted)] shrink-0">&bull;</span>
                <span className="italic text-[var(--muted)]">&ldquo;{b}&rdquo;</span>
              </li>
            ))}
          </ul>
        </Section>
      ),
    },
  };

  const ordered = MODE_ORDER[mode]
    .map(key => sections[key])
    .filter(s => s && s.hasContent);

  return (
    <div className="border border-[var(--border)] rounded-xl bg-white p-6 sm:p-8 mb-8">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
        <div>
          <div className="text-xs uppercase tracking-wide text-[var(--muted)] mb-1">
            Research brief
          </div>
          <div className="text-sm text-[var(--muted)]">
            {content.word_count.toLocaleString()}-word card compressed to{" "}
            {estimateBriefWords(g, evals)} words.{" "}
            <span className="text-[var(--text)]">{labName ?? ""}</span>
            {labName && " · "}
            {formatDate(content.version_date)}
          </div>
        </div>
        <div className="inline-flex rounded-full border border-[var(--border)] bg-[var(--surface-2)]/30 p-0.5">
          {(["overview", "researcher", "safety", "journalist"] as ReaderMode[]).map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1 rounded-full text-xs transition-colors ${
                mode === m
                  ? "bg-[var(--accent)] text-white"
                  : "text-[var(--muted)] hover:text-[var(--text)]"
              }`}
            >
              {MODE_LABEL[m]}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-5">
        {ordered.map(s => s.render())}
      </div>

      <p className="text-[11px] text-[var(--muted)] mt-8 pt-4 border-t border-[var(--border)] leading-relaxed">
        Every italicized passage is a <em>verbatim substring</em> of the source document
        (checked deterministically after extraction). Field selection is heuristic — some
        quotes may lack surrounding context and some claims may be absent if no matching
        pattern appeared. For citation, open the source:{" "}
        {sourceUrl ? (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--accent)] underline hover:opacity-80"
          >
            original {docType.replace(/_/g, " ")}
          </a>
        ) : (
          <span>original document</span>
        )}
        {content.source_hash && (
          <> &middot; source SHA <span className="font-mono">{content.source_hash}</span></>
        )}
        {" · "}version dated {formatDate(content.version_date)}.
      </p>
    </div>
  );
}

function Section({
  label, style, children,
}: {
  label: string;
  style?: "prose";
  children: React.ReactNode;
}) {
  return (
    <section className={style === "prose" ? "" : "grid grid-cols-1 md:grid-cols-[160px_1fr] gap-3 md:gap-5"}>
      {style !== "prose" && (
        <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)] md:pt-0.5">
          {label}
        </div>
      )}
      {style === "prose" && (
        <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)] mb-2">
          {label}
        </div>
      )}
      <div>{children}</div>
    </section>
  );
}

function QuoteSection({
  label, quotes, accent,
}: {
  label: string;
  quotes: string[];
  accent?: boolean;
}) {
  return (
    <Section label={label}>
      <ul className="space-y-2.5">
        {quotes.map((q, i) => (
          <li
            key={i}
            className={`text-sm leading-relaxed italic pl-3 border-l-2 ${
              accent ? "border-[var(--accent)]" : "border-[var(--border-light)]"
            } text-[var(--muted)]`}
          >
            &ldquo;{q}&rdquo;
          </li>
        ))}
      </ul>
    </Section>
  );
}

function EvalsSection({ evals }: { evals: EvalResult[] }) {
  // Top 8 scored evals by score, descending
  const top = [...evals]
    .filter(e => e.score != null && e.state !== "cited")
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 8);
  if (top.length === 0) return null;

  return (
    <Section label="Top benchmarks">
      <div className="overflow-hidden rounded-md border border-[var(--border)]">
        <table className="w-full text-sm">
          <thead className="bg-[var(--surface-2)]/40 text-[var(--muted)] text-[11px] uppercase tracking-wide">
            <tr>
              <th className="text-left px-3 py-2 font-medium">Benchmark</th>
              <th className="text-left px-3 py-2 font-medium">Variant</th>
              <th className="text-right px-3 py-2 font-medium">Score</th>
            </tr>
          </thead>
          <tbody>
            {top.map(e => (
              <tr key={e.id} className="border-t border-[var(--border)]">
                <td className="px-3 py-2 text-[var(--text)]">{e.benchmark?.name ?? "—"}</td>
                <td className="px-3 py-2 text-[var(--muted)] text-xs">
                  {e.variant !== "default" ? e.variant : "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums font-medium">
                  {formatScore(e.score, e.benchmark?.metric_unit)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {evals.length > top.length && (
        <p className="text-xs text-[var(--muted)] mt-2">
          Showing top {top.length} of {evals.length}. See full list below.
        </p>
      )}
    </Section>
  );
}

function formatScore(score: number | null, unit: string | null | undefined): string {
  if (score == null) return "—";
  if (unit === "%" || (score <= 100 && score > 1)) return `${score.toFixed(1)}%`;
  if (score <= 1) return `${(score * 100).toFixed(1)}%`;
  return score.toFixed(2);
}

function estimateBriefWords(g: DocumentContent["gist"], evals: EvalResult[]): number {
  if (!g) return 0;
  const text = [
    g.tldr ?? "",
    ...g.capability_claims,
    ...g.safety_findings,
    ...g.mitigations,
    ...g.deployment_scope,
    ...g.limitations,
    ...g.whats_new,
  ].join(" ");
  const evalWords = Math.min(evals.length, 8) * 4;
  return text.split(/\s+/).filter(Boolean).length + evalWords;
}
