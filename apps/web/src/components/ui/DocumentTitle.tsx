// Highlight the model-tier word inside a document title so cards from the
// same family don't all visually collapse together. "Claude Haiku 4.5 System
// Card" / "Claude Sonnet 4.5 System Card" / "Claude Opus 4.5 System Card"
// look near-identical at a glance because they only differ in one word — this
// pulls that word out into the brand accent color so the row reads as
// "Claude *Haiku* 4.5" rather than four indistinguishable words.
const TIER_WORDS = [
  "Haiku", "Sonnet", "Opus",
  "Flash", "Pro", "Mini", "Lite", "Plus", "Turbo",
  "Preview", "Instruct", "Base",
  "Mythos", "Deep Think",
];

export function DocumentTitle({ title, className = "" }: { title: string; className?: string }) {
  const re = new RegExp(`\\b(${TIER_WORDS.join("|")})\\b`, "i");
  const match = title.match(re);
  if (!match || match.index === undefined) {
    return <span className={className}>{title}</span>;
  }
  const idx = match.index;
  const word = match[0];
  return (
    <span className={className}>
      {title.slice(0, idx)}
      <span className="text-accent font-semibold">{word}</span>
      {title.slice(idx + word.length)}
    </span>
  );
}
