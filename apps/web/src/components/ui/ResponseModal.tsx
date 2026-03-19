"use client";
import { useEffect, useCallback } from "react";
import type { ProbeResponseDetail } from "@/lib/types";
import { slantColor, slantLabel } from "@/lib/utils";

interface ResponseModalProps {
  response: ProbeResponseDetail;
  modelName: string;
  probeTopic: string;
  onClose: () => void;
}

export function ResponseModal({ response, modelName, probeTopic, onClose }: ResponseModalProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  }, [onClose]);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [handleKeyDown]);

  const composite = response.slant_score?.composite ?? 0;
  const pct = ((composite + 1) / 2) * 100;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-surface-1 border border-[var(--border)] rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <div>
            <h2 className="text-base font-semibold text-white">{modelName}</h2>
            <p className="text-xs text-[var(--muted)] mt-0.5">{probeTopic}</p>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--muted)] hover:text-white transition-colors text-xl leading-none p-1"
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Question */}
          <div>
            <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wide mb-1.5">Question</p>
            <blockquote className="border-l-2 border-accent pl-3 text-sm text-[var(--muted)] italic">
              {response.prompt_text}
            </blockquote>
          </div>

          {/* Response */}
          <div>
            <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wide mb-1.5">Response</p>
            <div className="text-sm text-white/90 whitespace-pre-wrap leading-relaxed">
              {response.response_text}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[var(--border)] flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs text-[var(--muted)]">Bias Score:</span>
              <span
                className="font-mono text-sm font-medium"
                style={{ color: slantColor(composite) }}
              >
                {composite >= 0 ? "+" : ""}{composite.toFixed(3)}
              </span>
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{
                  color: slantColor(composite),
                  background: `${slantColor(composite)}15`,
                }}
              >
                {slantLabel(composite)}
              </span>
            </div>
            <div className="relative h-2 w-full rounded-full bg-surface-3 overflow-hidden">
              <div className="absolute inset-0 flex">
                <div className="w-1/2 border-r border-[var(--muted)]/30" />
              </div>
              <div
                className="absolute top-0 h-full w-2.5 rounded-full -translate-x-1/2"
                style={{ left: `${pct}%`, background: slantColor(composite) }}
              />
            </div>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-[var(--border)] text-[var(--muted)] hover:text-white hover:border-white/30 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
