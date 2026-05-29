"use client";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Benchmark } from "@/lib/types";

const SOURCE_LABELS: Record<string, string> = {
  paper: "Paper",
  dataset: "Dataset",
  source: "Source",
  github: "GitHub",
  homepage: "Homepage",
};

function PolicyNoteField({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "warning" }) {
  return (
    <div className="space-y-1">
      <div className="text-[10px] uppercase tracking-wider font-semibold text-[var(--muted)]">
        {label}
      </div>
      <p className={`text-sm leading-snug ${tone === "warning" ? "text-amber-900" : "text-[var(--text)]"}`}>
        {value}
      </p>
    </div>
  );
}

/**
 * Hover-or-click explainer for a benchmark. Implements the EvalCards paper
 * Policy Note layout (Figure 3): measures / caveat / intended_for /
 * how_to_read + topic tags + source links. Falls back to the plain benchmark
 * name (no underline) when no policy_note is attached, to avoid promising
 * content we don't have.
 */
export function BenchmarkPopover({ benchmark }: { benchmark: Benchmark }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // No policy note → render plain text. No trigger affordance, no false promise.
  if (!benchmark.policy_note) {
    return <span className="font-medium">{benchmark.name}</span>;
  }

  // Position the popover under the trigger, clamped to the viewport.
  useLayoutEffect(() => {
    if (!open || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const popWidth = 384; // matches w-96
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - popWidth - 8));
    setPos({ top: rect.bottom + 6, left });
  }, [open]);

  // Outside-click + Escape to close.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target)) return;
      if (popoverRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const pn = benchmark.policy_note;
  const sourceEntries = Object.entries(pn.sources || {});

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen(v => !v)}
        className="font-medium text-left underline decoration-dotted decoration-[var(--muted)] underline-offset-4 hover:decoration-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-sm"
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        {benchmark.name}
      </button>

      {open && pos && typeof document !== "undefined" && createPortal(
        <div
          ref={popoverRef}
          role="dialog"
          aria-label={`Policy note for ${benchmark.name}`}
          style={{ top: pos.top, left: pos.left }}
          className="fixed z-50 w-96 max-w-[calc(100vw-16px)] p-5 space-y-3 bg-[var(--surface-0,white)] border border-[var(--border)] rounded-xl shadow-xl text-[var(--text)]"
        >
          <div className="flex items-baseline justify-between gap-3 pb-1 border-b border-[var(--border)]">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Policy Note</div>
              <h3 className="font-serif text-base font-semibold">{benchmark.name}</h3>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-[var(--muted)] hover:text-[var(--text)] text-xs"
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          {pn.measures && <PolicyNoteField label="Measures" value={pn.measures} />}
          {pn.caveat && <PolicyNoteField label="Caveat" value={pn.caveat} tone="warning" />}
          {pn.intended_for && <PolicyNoteField label="Intended for" value={pn.intended_for} />}
          {pn.how_to_read && <PolicyNoteField label="How to read" value={pn.how_to_read} />}

          {pn.topic_tags && pn.topic_tags.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {pn.topic_tags.map(tag => (
                <span
                  key={tag}
                  className="text-[10px] px-2 py-0.5 rounded bg-[var(--surface-2)] text-[var(--muted)] uppercase tracking-wide"
                >
                  {tag.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          )}

          {sourceEntries.length > 0 && (
            <div className="flex flex-wrap gap-3 pt-2 border-t border-[var(--border)]">
              {sourceEntries.map(([key, url]) => (
                <a
                  key={key}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-[var(--accent)] hover:underline"
                >
                  {SOURCE_LABELS[key] ?? key} →
                </a>
              ))}
            </div>
          )}
        </div>,
        document.body
      )}
    </>
  );
}
