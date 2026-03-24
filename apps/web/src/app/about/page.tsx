export default function AboutPage() {
  return (
    <div className="max-w-3xl">
      <h1 className="text-3xl font-bold font-serif mb-2">About</h1>
      <p className="text-[var(--muted)] mb-10 text-base leading-relaxed">
        Model Card Explorer is an open research platform built by{" "}
        <a href="https://freesystems.substack.com/" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
          Free Systems Lab
        </a>{" "}
        to bring transparency to AI model governance and safety documentation.
      </p>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">What We Do</h2>
        <div className="space-y-4 text-sm text-[var(--muted)] leading-relaxed">
          <p>
            We systematically collect, version, and analyze the model cards and safety
            documentation published by major AI laboratories. Our platform extracts structured
            evaluation data from each card and enables cross-lab and cross-generation comparisons.
          </p>
          <p>
            By tracking what AI companies disclose about their models&apos; capabilities,
            limitations, and safety evaluations, we make it easier for researchers, policymakers,
            and the public to understand the state of AI governance.
          </p>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Methodology</h2>

        <div className="space-y-8">
          <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
            <h3 className="font-semibold mb-2">Safety Coverage Analysis</h3>
            <p className="text-sm text-[var(--muted)] leading-relaxed mb-3">
              We collect policy documents from each AI lab (model cards, usage policies, responsible
              scaling frameworks, constitutional AI documents) and measure how well they cover
              15 safety categories using semantic similarity.
            </p>
            <ul className="text-sm text-[var(--muted)] space-y-2">
              <li className="flex gap-2">
                <span className="text-accent shrink-0">1.</span>
                <span>Documents are embedded using all-mpnet-base-v2, a 768-dimensional sentence embedding model</span>
              </li>
              <li className="flex gap-2">
                <span className="text-accent shrink-0">2.</span>
                <span>Each safety category has a description that is also embedded</span>
              </li>
              <li className="flex gap-2">
                <span className="text-accent shrink-0">3.</span>
                <span>Cosine similarity between document and category embeddings determines coverage strength</span>
              </li>
              <li className="flex gap-2">
                <span className="text-accent shrink-0">4.</span>
                <span>Scores above 0.35 indicate meaningful coverage; above 0.70 indicates strong, dedicated policy</span>
              </li>
            </ul>
          </div>

          <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
            <h3 className="font-semibold mb-2">Eval Extraction</h3>
            <p className="text-sm text-[var(--muted)] leading-relaxed mb-3">
              We use LLM-based extraction to identify every benchmark result, safety evaluation,
              and capability assessment reported in each model card. Extracted data is structured
              into a searchable, comparable format.
            </p>
            <ul className="text-sm text-[var(--muted)] space-y-2">
              <li className="flex gap-2">
                <span className="text-accent shrink-0">1.</span>
                <span>Model card content is sent to Claude Sonnet for structured extraction</span>
              </li>
              <li className="flex gap-2">
                <span className="text-accent shrink-0">2.</span>
                <span>Benchmark names, scores, variants, and metrics are normalized against a known benchmark registry</span>
              </li>
              <li className="flex gap-2">
                <span className="text-accent shrink-0">3.</span>
                <span>Results are linked to model families and generations for cross-generation comparison</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Data Sources</h2>
        <p className="text-sm text-[var(--muted)] leading-relaxed mb-4">
          We track 9 AI laboratories and collect their publicly available documentation:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            "Anthropic", "OpenAI", "Google DeepMind",
            "Meta AI", "Mistral AI", "xAI",
            "Cohere", "Amazon (AWS)", "AI21 Labs",
          ].map(lab => (
            <div key={lab} className="px-4 py-2.5 rounded-lg border border-[var(--border)] bg-white shadow-sm text-sm">
              {lab}
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Limitations</h2>
        <ul className="text-sm text-[var(--muted)] space-y-3 leading-relaxed">
          <li className="flex gap-2">
            <span className="text-[var(--muted)] shrink-0">1.</span>
            <span>Document-level embeddings may dilute brief mentions of a topic within longer documents.</span>
          </li>
          <li className="flex gap-2">
            <span className="text-[var(--muted)] shrink-0">2.</span>
            <span>The 0.35 cosine similarity threshold for coverage is a judgment call based on empirical validation.</span>
          </li>
          <li className="flex gap-2">
            <span className="text-[var(--muted)] shrink-0">3.</span>
            <span>LLM-based eval extraction may miss or misinterpret results in unusual card formats.</span>
          </li>
        </ul>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Open Source</h2>
        <p className="text-sm text-[var(--muted)] leading-relaxed">
          This project is fully open source. The code, data pipeline, and analysis methodology are
          available on{" "}
          <a href="https://github.com/owizdom/ai-research-model-cards" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
            GitHub
          </a>.
          Contributions and feedback are welcome.
        </p>
      </section>
    </div>
  );
}
