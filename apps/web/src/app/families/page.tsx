import { api } from "@/lib/api";
import Link from "next/link";

export const revalidate = 300;

export default async function FamiliesPage() {
  const families = await api.families.list().catch(() => []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold font-serif mb-2">Model Families</h1>
        <p className="text-sm text-[var(--muted)]">
          Compare evaluations across model generations within each AI lab&apos;s model family.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {families.map(fam => (
          <Link
            key={fam.slug}
            href={`/families/${fam.slug}`}
            className="block p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors group"
          >
            <h3 className="font-semibold text-lg group-hover:text-accent transition-colors mb-1">
              {fam.name}
            </h3>
            <p className="text-sm text-[var(--muted)] mb-3">{fam.lab_slug}</p>
            <div className="flex items-center gap-4 text-xs text-[var(--muted)]">
              <span>{fam.generation_count} generation{fam.generation_count !== 1 ? "s" : ""}</span>
            </div>
          </Link>
        ))}
      </div>

      {families.length === 0 && (
        <div className="p-8 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
          No model families seeded yet. Run <code className="text-accent">make seed</code> to populate.
        </div>
      )}
    </div>
  );
}
