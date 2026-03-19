export default function AboutPage() {
  return (
    <div className="max-w-3xl">
      <h1 className="text-3xl font-bold mb-2">About</h1>
      <p className="text-[var(--muted)] mb-10 text-base leading-relaxed">
        AI Policy Intelligence is an open research platform built by{" "}
        <a href="https://freesystems.substack.com/" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
          Free Systems Lab
        </a>{" "}
        to bring transparency to AI safety policies and model behavior.
      </p>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">What We Do</h2>
        <div className="space-y-4 text-sm text-[var(--muted)] leading-relaxed">
          <p>
            We systematically collect, analyze, and compare the safety policies published by
            major AI laboratories. Then we test whether their AI models actually behave
            consistently with those policies, focusing on political neutrality as a measurable proxy.
          </p>
          <p>
            Our platform tracks two things: what AI companies <em>say</em> (their published policies,
            model cards, usage guidelines) and what their models <em>do</em> (how they respond to
            politically sensitive questions).
          </p>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Methodology</h2>

        <div className="space-y-8">
          <div className="p-5 rounded-xl border border-[var(--border)] bg-surface-1">
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

          <div className="p-5 rounded-xl border border-[var(--border)] bg-surface-1">
            <h3 className="font-semibold mb-2">Political Bias Measurement</h3>
            <p className="text-sm text-[var(--muted)] leading-relaxed mb-3">
              We ask each AI model the same 25 politically sensitive questions spanning 11 categories
              (elections, immigration, guns, economics, social policy, climate, foreign policy, tech
              policy, criminal justice, healthcare, and free speech) and compute a composite bias score.
            </p>
            <ul className="text-sm text-[var(--muted)] space-y-2">
              <li className="flex gap-2">
                <span className="text-accent shrink-0">50%</span>
                <span><strong className="text-white">Embedding Distance</strong> : Response embeddings compared against liberal, conservative, and neutral anchor texts</span>
              </li>
              <li className="flex gap-2">
                <span className="text-accent shrink-0">30%</span>
                <span><strong className="text-white">Political Valence Lexicon</strong> : ~70 politically charged terms scored on a liberal-to-conservative scale</span>
              </li>
              <li className="flex gap-2">
                <span className="text-accent shrink-0">20%</span>
                <span><strong className="text-white">Moral Foundations</strong> : Scoring across Care, Fairness, Loyalty, Authority, and Purity dimensions</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Data Sources</h2>
        <p className="text-sm text-[var(--muted)] leading-relaxed mb-4">
          We track 9 AI laboratories and collect their publicly available policy documentation:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            "Anthropic", "OpenAI", "Google DeepMind",
            "Meta AI", "Mistral AI", "xAI",
            "Cohere", "Amazon (AWS)", "AI21 Labs",
          ].map(lab => (
            <div key={lab} className="px-4 py-2.5 rounded-lg border border-[var(--border)] bg-surface-1 text-sm">
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
            <span>Bias measurement currently covers Meta Llama models via Groq. Expansion to GPT, Claude, and Gemini is planned.</span>
          </li>
          <li className="flex gap-2">
            <span className="text-[var(--muted)] shrink-0">2.</span>
            <span>The composite score weights (50/30/20) are manually calibrated. Different weightings would shift absolute values.</span>
          </li>
          <li className="flex gap-2">
            <span className="text-[var(--muted)] shrink-0">3.</span>
            <span>Document-level embeddings may dilute brief mentions of a topic within longer documents.</span>
          </li>
          <li className="flex gap-2">
            <span className="text-[var(--muted)] shrink-0">4.</span>
            <span>The 0.35 cosine similarity threshold for coverage is a judgment call based on empirical validation.</span>
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
