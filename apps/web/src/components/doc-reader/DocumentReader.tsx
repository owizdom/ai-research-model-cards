"use client";
import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import type { DocumentContent } from "@/lib/types";

export function DocumentReader({ content }: { content: DocumentContent }) {
  const [activeAnchor, setActiveAnchor] = useState<string | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);

  // Scroll-spy: mark the outline item whose heading is closest to top of viewport
  useEffect(() => {
    if (!content.has_headers) return;
    const anchors = content.outline.map(o => o.anchor);
    const onScroll = () => {
      let current: string | null = null;
      for (const a of anchors) {
        const el = document.getElementById(a);
        if (!el) continue;
        const top = el.getBoundingClientRect().top;
        if (top < 120) current = a;
        else break;
      }
      setActiveAnchor(current);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [content]);

  return (
    <div className="flex gap-10 items-start">
      {content.has_headers && content.outline.length > 0 && (
        <aside className="hidden lg:block w-60 shrink-0 sticky top-8 max-h-[calc(100vh-6rem)] overflow-y-auto pr-2">
          <div className="text-xs uppercase tracking-wide text-[var(--muted)] mb-3">
            Contents
          </div>
          <nav className="space-y-1 text-sm">
            {content.outline.map(item => (
              <a
                key={item.anchor}
                href={`#${item.anchor}`}
                className={`block leading-snug transition-colors ${
                  activeAnchor === item.anchor
                    ? "text-[var(--accent)] font-medium"
                    : "text-[var(--muted)] hover:text-[var(--text)]"
                }`}
                style={{ paddingLeft: `${(item.level - 1) * 12}px` }}
              >
                {item.title}
              </a>
            ))}
          </nav>
        </aside>
      )}

      <article
        ref={contentRef}
        className="flex-1 min-w-0 max-w-[68ch] prose-container"
      >
        {!content.has_headers && (
          <div className="mb-6 p-3 rounded-lg bg-[var(--surface-2)] text-xs text-[var(--muted)] leading-relaxed">
            This document was extracted from a PDF and lacks native section structure.
            The prose below has been reformatted for readability. For pristine
            formatting, use the source PDF link above.
          </div>
        )}

        <ReactMarkdown
          components={{
            h1: ({ children, ...props }) => {
              const text = String(children);
              const anchor = slugify(text, content.outline);
              return (
                <h2 id={anchor} {...props} className="font-serif font-bold text-2xl mt-10 mb-4 scroll-mt-24">
                  {children}
                </h2>
              );
            },
            h2: ({ children, ...props }) => {
              const text = String(children);
              const anchor = slugify(text, content.outline);
              return (
                <h3 id={anchor} {...props} className="font-serif font-semibold text-xl mt-8 mb-3 scroll-mt-24">
                  {children}
                </h3>
              );
            },
            h3: ({ children, ...props }) => {
              const text = String(children);
              const anchor = slugify(text, content.outline);
              return (
                <h4 id={anchor} {...props} className="font-semibold text-base mt-6 mb-2 scroll-mt-24">
                  {children}
                </h4>
              );
            },
            p: ({ children }) => (
              <p className="text-[15px] leading-[1.75] text-[var(--text)] mb-4">
                {children}
              </p>
            ),
            li: ({ children }) => (
              <li className="text-[15px] leading-[1.7] text-[var(--text)] mb-1">
                {children}
              </li>
            ),
            a: ({ children, href }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent)] underline hover:opacity-80"
              >
                {children}
              </a>
            ),
            strong: ({ children }) => <strong className="font-semibold text-[var(--text)]">{children}</strong>,
            em: ({ children }) => <em className="italic">{children}</em>,
            code: ({ children }) => (
              <code className="px-1.5 py-0.5 rounded bg-[var(--surface-2)] text-xs font-mono">
                {children}
              </code>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-[var(--accent)] pl-4 italic text-[var(--muted)] my-4">
                {children}
              </blockquote>
            ),
          }}
        >
          {content.content_md}
        </ReactMarkdown>
      </article>
    </div>
  );
}

function slugify(text: string, outline: { title: string; anchor: string }[]): string {
  const match = outline.find(o => o.title === text.trim());
  if (match) return match.anchor;
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 64);
}
