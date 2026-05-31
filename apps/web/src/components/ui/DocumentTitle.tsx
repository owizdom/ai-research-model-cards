// Strips redundant document-type suffixes from titles so the row reads as the
// model's name. The doc_type badge on the right already conveys "system card"
// / "model card" / "technical paper" — repeating it inside the title made the
// three Claude 4.5 rows ("Claude Haiku 4.5 System Card", "Claude Sonnet 4.5
// System Card", "Claude Opus 4.5 System Card") visually collapse into each
// other. After this strip they read as "Claude Haiku 4.5" / "Claude Sonnet 4.5"
// / "Claude Opus 4.5" — the distinguishing word is the trailing word.
const TRAILING_SUFFIXES = [
  / (System|Model)\s+Card$/i,
  / Technical\s+Paper$/i,
  / Card$/i,
  / Paper$/i,
  / Report$/i,
];

export function cleanDocumentTitle(title: string): string {
  let t = title.trim();
  for (const re of TRAILING_SUFFIXES) {
    const stripped = t.replace(re, "");
    if (stripped !== t) return stripped.trim();
  }
  return t;
}

export function DocumentTitle({ title, className = "" }: { title: string; className?: string }) {
  return <span className={className}>{cleanDocumentTitle(title)}</span>;
}
