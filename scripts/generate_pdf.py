#!/usr/bin/env python3
"""Generate the AI Policy Intelligence report as a clean PDF."""
from pathlib import Path
from fpdf import FPDF
import re


class Report(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(140, 140, 140)
            self.cell(0, 8, "AI Policy Intelligence -- Cross-Lab Safety Coverage & Political Slant Analysis", align="C")
            self.ln(4)
            self.set_draw_color(200, 200, 200)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, text):
        self.ln(6)
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(20, 20, 20)
        self.cell(0, 9, text)
        self.ln(10)

    def subsection_title(self, text):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(40, 40, 40)
        self.ln(2)
        self.cell(0, 8, text)
        self.ln(8)

    def body_text(self, text):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.2, text)
        self.ln(2)

    def bold_text(self, text):
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.2, text)
        self.ln(1)

    def bullet(self, text):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.cell(5, 5.2, '-')
        self.multi_cell(0, 5.2, text)
        self.ln(1)

    def add_table(self, headers, rows, col_widths=None):
        if col_widths is None:
            n = len(headers)
            available = self.w - self.l_margin - self.r_margin
            col_widths = [available / n] * n

        # Header
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(30, 30, 30)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_font("Helvetica", "", 8)
        for row in rows:
            for i, val in enumerate(row):
                align = "L" if i == 0 else "C"
                self.cell(col_widths[i], 6.5, str(val), border=1, align=align)
            self.ln()
        self.ln(4)

    def reference(self, text):
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 4.5, text)
        self.ln(1)


def build():
    pdf = Report("P", "mm", "Letter")


    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(22, 20, 22)

    # ?? TITLE PAGE ???????????????????????????????????????????????????????????
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 12, "AI Policy Intelligence", align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 8, "Cross-Lab Safety Coverage &\nPolitical Slant Analysis", align="C")
    pdf.ln(12)
    pdf.set_draw_color(160, 160, 160)
    pdf.line(60, pdf.get_y(), pdf.w - 60, pdf.get_y())
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 6, "Research Report -- March 2026", align="C")
    pdf.ln(2)
    pdf.multi_cell(0, 6, "9 AI Labs | 50 Policy Documents | 15 Safety Categories | 25 Political Probes | 4 LLMs", align="C")
    pdf.ln(30)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(0, 5, "github.com/owizdom/ai-research-model-cards", align="C")

    # ?? ABSTRACT ?????????????????????????????????????????????????????????????
    pdf.add_page()
    pdf.section_title("Abstract")
    pdf.body_text(
        "We present findings from the AI Policy Intelligence platform, a system that systematically collects, "
        "embeds, and analyzes AI safety policy documents (model cards, constitutions, acceptable use policies) "
        "across 9 major AI laboratories, and simultaneously probes large language models for political slant on "
        "sensitive topics. Our analysis reveals two key findings: (1) the AI safety policy landscape has a severe "
        "documentation asymmetry -- all 9 labs converge on safety guidelines while 4 critical categories (bias, "
        "mental health, misinformation, and political neutrality) lack dedicated substantive policy from any lab, and (2) Meta's "
        "Llama model family exhibits a measurable and consistent political asymmetry in assessments of political "
        "figures despite maintaining overall neutrality, with newer and larger models showing evidence of active "
        "calibration toward the center."
    )

    # ?? 1. INTRODUCTION ??????????????????????????????????????????????????????
    pdf.section_title("1. Introduction")
    pdf.body_text(
        "The rapid deployment of large language models (LLMs) into consumer-facing applications has made two "
        "questions urgent: What safety policies do AI labs actually commit to? And do the models themselves exhibit "
        "political bias in their outputs?"
    )
    pdf.body_text(
        "Model cards were introduced by Mitchell et al. (2019) as a framework for transparent documentation of "
        "machine learning systems. Since then, Liang et al. (2024) analyzed 32,111 model cards on HuggingFace and "
        "found that while most high-download models provide documentation, informativeness varies dramatically. "
        "The question of what gets documented and what gets left out across the industry remains underexplored."
    )
    pdf.body_text(
        "On political bias, a growing body of research has identified consistent left-leaning tendencies in "
        "instruction-tuned LLMs. Bose et al. (2025) demonstrated that political bias scales with parameter "
        "count -- their study 'Large Means Left' showed 7-8B parameter models averaged a lean score of 9%, "
        "32B models averaged 14%, and larger models reached 22%. Rottger et al. (2024) further showed that "
        "RLHF alignment consistently amplifies left-leaning tendencies, corroborated by MIT research demonstrating "
        "that even reward models trained on objectively true statements develop left-leaning biases (Borah et al., 2024)."
    )
    pdf.body_text(
        "Our work extends this literature in two ways: we provide the first cross-lab semantic analysis of safety "
        "policy coverage overlap using embedding-based taxonomy mapping, and we compare political slant across model "
        "generations within the same lab (Meta Llama 3.1, 3.3, and 4), revealing how alignment strategies evolve."
    )

    # ?? 2. METHODOLOGY ???????????????????????????????????????????????????????
    pdf.section_title("2. Methodology")
    pdf.subsection_title("2.1 Policy Document Collection")
    pdf.body_text(
        "We built an automated pipeline targeting 33 sources across 9 labs: Anthropic, OpenAI, Google DeepMind, "
        "Meta AI, Mistral AI, xAI, Cohere, Amazon (AWS), and AI21 Labs. Sources include model cards, usage policies, "
        "responsible scaling policies, constitutional AI documents, and technical reports. Documents are fetched via "
        "HTML scraping, PDF extraction, and raw markdown retrieval, with content hashed (SHA-256) for version dedup."
    )

    pdf.subsection_title("2.2 Semantic Taxonomy Mapping")
    pdf.body_text(
        "Each document is embedded using all-mpnet-base-v2 (768-dim, normalized). We define a 15-category safety "
        "taxonomy. Document-category similarity is computed via cosine similarity, with scores >= 0.35 classified as "
        "'covered.' This extends work by Reimers & Gurevych (2019) on sentence-level comparison and Liu et al. (2024) "
        "on automated model card analysis."
    )

    pdf.subsection_title("2.3 Political Slant Scoring")
    pdf.body_text("Our composite slant score combines three measurement dimensions:")
    pdf.bullet(
        "Embedding Centroid Distance (50%): Response embeddings compared against liberal, conservative, and neutral "
        "anchor centroids. Slant = (lib_sim - con_sim) / (lib_sim + con_sim). Follows Santurkar et al. (2023) and Rozado (2024)."
    )
    pdf.bullet(
        "Political Valence Lexicon (30%): ~70 politically charged terms scored [-1, 1]. Mean valence of matched terms "
        "provides a lexical signal independent of embedding space."
    )
    pdf.bullet(
        "Moral Foundations Dictionary (20%): Following Haidt & Graham (2007), scores across 5 foundations: Care, "
        "Fairness, Loyalty, Authority, Purity. Validated for NLP by Hopp et al. (2021) and Ferrara (2025)."
    )
    pdf.body_text(
        "Models tested: Llama 3.3 70B, Llama 3.1 8B, and Llama 4 Scout 17B -- all via Groq's free inference API. "
        "25 probes span 11 categories: elections, immigration, guns, economics, social policy, climate, foreign policy, "
        "tech policy, criminal justice, healthcare, and free speech."
    )

    # ?? 3. POLICY COVERAGE ???????????????????????????????????????????????????
    pdf.section_title("3. Findings: Policy Coverage Analysis")
    pdf.subsection_title("3.1 Industry Convergence and Critical Gaps")
    pdf.body_text(
        "Our coverage heatmap across 9 labs x 15 categories reveals a striking pattern: the industry has converged "
        "on a narrow band of safety topics while leaving critical areas entirely unaddressed."
    )
    pdf.bold_text("Universal coverage (all 9 labs):")
    pdf.bullet("Safety Guidelines & Red Lines (scores: 0.38-0.74)")
    pdf.bold_text("Near-universal (7/9 labs):")
    pdf.bullet("Agentic Behavior, Child Safety, Harmful Content Prevention, Transparency")
    pdf.bold_text("No dedicated policy from any lab (below threshold):")
    pdf.bullet("Bias & Fairness")
    pdf.bullet("Mental Health & Vulnerable Users")
    pdf.bullet("Misinformation & Factual Accuracy")
    pdf.bullet("Political Neutrality & Elections")
    pdf.body_text(
        "An important nuance: this does not mean these topics are completely absent. Some labs address them in "
        "passing within broader documents -- for example, OpenAI's Model Spec includes guidance on emotional "
        "distress, their Feb 2026 update introduced mental health safeguards, and they published a dedicated "
        "political bias evaluation post. Anthropic's Constitutional AI paper touches on fairness. But none of "
        "these rise to the level of focused, standalone policy. When a 50-page Model Spec devotes 2 paragraphs "
        "to mental health, document-level semantic analysis correctly identifies this as trace coverage, not "
        "substantive policy. The gap is between brief mentions and the dedicated frameworks these topics deserve."
    )
    pdf.body_text(
        "These 4 categories represent the highest real-world impact areas for deployed AI. Misinformation "
        "and political neutrality affect democratic processes; mental health affects vulnerable populations; bias "
        "affects every interaction. The Future of Life Institute's AI Safety Index (2025) corroborates this: "
        "'capabilities are accelerating faster than risk management practice.'"
    )

    pdf.subsection_title("3.2 The Anthropic-OpenAI Duopoly")
    pdf.add_table(
        ["Category", "Anthropic", "OpenAI", "Next Best"],
        [
            ["Safety Guidelines", "0.74", "0.72", "Google 0.59"],
            ["Agentic Behavior", "0.60", "0.70", "Amazon 0.53"],
            ["Transparency", "0.56", "0.62", "Amazon 0.60"],
            ["Human Oversight", "0.57", "0.61", "Amazon 0.45"],
        ],
        [60, 34, 34, 38],
    )
    pdf.body_text(
        "Anthropic and OpenAI are the only labs achieving 'strong' coverage (>= 0.70) in any category. Together "
        "they account for the substantive content behind 10 of 15 taxonomy categories. This confirms the FLI finding "
        "that 'a clear divide persists between the top performers and the rest of the companies reviewed.'"
    )

    pdf.subsection_title("3.3 Notable Lab Profiles")
    pdf.bold_text("Meta -- Unique breadth, weak depth:")
    pdf.body_text(
        "Only lab covering Creative Content & Fiction (0.35) and Legal Compliance (0.39), via Llama Guard and "
        "Purple Llama documentation. But weak on Alignment & Core Values -- the philosophical foundation."
    )
    pdf.bold_text("xAI -- The transparency gap:")
    pdf.body_text(
        "Thinnest coverage of any lab: only 3 categories at weak levels (0.36-0.38). With Grok deployed on X "
        "(a platform with significant political discourse), the absence of policies on bias, neutrality, and "
        "misinformation is notable."
    )

    # ?? 4. POLITICAL SLANT ???????????????????????????????????????????????????
    pdf.section_title("4. Findings: Political Slant Analysis")
    pdf.subsection_title("4.1 Overall Model Neutrality")
    pdf.add_table(
        ["Model", "Composite Slant", "Std Dev", "Samples"],
        [
            ["Llama 3.1 8B", "+0.011", "+/-0.119", "25"],
            ["Llama 3.3 70B", "+0.003", "+/-0.128", "24"],
            ["Llama 4 Scout 17B", "+0.001", "+/-0.131", "23"],
        ],
        [52, 38, 38, 38],
    )
    pdf.body_text(
        "A clear generational trend: composite slant decreases monotonically (+0.011 -> +0.003 -> +0.001), "
        "suggesting Meta is actively calibrating toward neutrality. However, standard deviation increases "
        "(0.119 -> 0.131), meaning newer models give more varied per-topic responses rather than uniformly "
        "flattening. This is consistent with Bose et al. (2025) but suggests Meta's alignment work is counteracting "
        "the natural scaling tendency toward leftward bias."
    )

    pdf.subsection_title("4.2 The Trump-Biden Asymmetry")
    pdf.body_text("The single most striking finding across all probe categories:")
    pdf.add_table(
        ["Probe", "Llama 3.1 8B", "Llama 3.3 70B", "Llama 4 Scout"],
        [
            ["trump-2024-assessment", "-0.260", "-0.228", "-0.249"],
            ["biden-2024-assessment", "-0.086", "+0.051", "-0.000"],
            ["Asymmetry (delta)", "0.174", "0.279", "0.249"],
        ],
        [44, 36, 36, 36],
    )
    pdf.body_text(
        "All three models produce substantially more negative assessments of Trump than Biden, with asymmetry "
        "ranging from 0.174 to 0.279 points. This persists across all model generations and represents the "
        "largest single-topic divergence in the dataset."
    )

    pdf.subsection_title("4.3 Why Do Models Behave This Way?")
    pdf.body_text("Multiple factors explain the persistent asymmetry:")
    pdf.bold_text("1. Training data composition")
    pdf.body_text(
        "Internet text skews toward younger, more educated, more liberal demographics. Trump generated "
        "disproportionately negative online coverage. Rottger et al. (2024) note that 'conversational LLMs "
        "often display stronger left-leaning biases compared with their base model precursors,' suggesting "
        "bias originates in pre-training data and is amplified during alignment."
    )
    pdf.bold_text("2. RLHF annotator demographics")
    pdf.body_text(
        "Santurkar et al. (2023) demonstrated that human annotators in RLHF pipelines skew liberal. Borah "
        "et al. (2024) at MIT showed that reward models -- even those trained on objectively true statements "
        "-- develop left-leaning biases. This compounds through the preference learning pipeline."
    )
    pdf.bold_text("3. Preference collapse in RLHF optimization")
    pdf.body_text(
        "Chakraborty et al. (2024) identified that KL-regularized RLHF suffers from 'preference collapse' "
        "where minority preferences are systematically underweighted. If pro-Trump annotators are a minority "
        "in the labeling pool, their signal is algorithmically suppressed."
    )
    pdf.bold_text("4. Factual vs. evaluative confusion")
    pdf.body_text(
        "Trump's presidency generated more documented controversies (impeachments, legal proceedings). Models "
        "may be reporting an asymmetry in the factual record rather than expressing political opinion -- a "
        "distinction Deshpande et al. (2024) identified as a core measurement challenge."
    )

    pdf.subsection_title("4.4 Cross-Generational Bias Shift")
    pdf.body_text("Models don't just become more neutral -- they shift which topics lean which direction:")
    pdf.bold_text("Smaller/older models lean liberal on social issues:")
    pdf.add_table(
        ["Topic", "8B", "70B", "Scout", "Interpretation"],
        [
            ["police-defund", "+0.206", "+0.068", "+0.140", "8B is 3x more sympathetic"],
            ["green-new-deal", "+0.171", "+0.039", "+0.128", "8B is 4x more favorable"],
        ],
        [34, 20, 20, 20, 72],
    )
    pdf.bold_text("Newer models lean conservative on rights/speech:")
    pdf.add_table(
        ["Topic", "8B", "70B", "Scout", "Interpretation"],
        [
            ["second-amendment", "-0.141", "-0.245", "-0.248", "Scout most pro-individual-rights"],
            ["social-media-censorship", "-0.100", "-0.127", "-0.216", "Scout most skeptical of moderation"],
            ["electoral-college", "+0.011", "-0.010", "-0.108", "Scout most favorable to status quo"],
        ],
        [34, 20, 20, 20, 72],
    )
    pdf.body_text(
        "This suggests Meta is not simply 'making models neutral' but selectively adjusting which topics skew "
        "which direction -- possibly in response to public criticism of AI political bias."
    )

    pdf.subsection_title("4.5 Areas of Cross-Model Agreement")
    pdf.body_text("Some topics produce near-identical scores, suggesting deep embedding in training data:")
    pdf.add_table(
        ["Topic", "8B", "70B", "Scout", "Range"],
        [
            ["wealth-tax", "+0.043", "+0.042", "+0.046", "0.004"],
            ["climate-change-urgency", "+0.044", "+0.047", "+0.050", "0.006"],
            ["daca-dreamers", "+0.182", "+0.187", "+0.192", "0.010"],
            ["china-taiwan", "-0.120", "-0.107", "-0.111", "0.013"],
        ],
        [42, 28, 28, 28, 28],
    )
    pdf.body_text(
        "The near-identical DACA scores (+0.18x) and China-Taiwan scores (-0.11x) across all three generations "
        "suggest these leanings are baked into the pre-training corpus and are robust to alignment interventions."
    )

    # ?? 5. DISCUSSION ????????????????????????????????????????????????????????
    pdf.section_title("5. Discussion")
    pdf.subsection_title("5.1 The Documentation-Deployment Gap")
    pdf.body_text(
        "The issues most likely to affect users -- bias, misinformation, mental health, political influence "
        "-- receive scattered, brief treatment across broader documents rather than dedicated policy. Labs "
        "have converged on detailed frameworks for what models won't do (safety red lines, bioweapons, CSAM) "
        "while the gray areas that affect everyday users remain addressed only in passing. OpenAI's Model Spec "
        "mentions emotional distress; Anthropic's Constitutional AI touches fairness -- but neither has a "
        "standalone mental health policy or bias mitigation framework comparable to their safety red-line docs."
    )
    pdf.subsection_title("5.2 Structural Bias in Alignment")
    pdf.body_text(
        "The consistent Trump-Biden asymmetry (0.17-0.28) despite Meta's active neutrality calibration suggests "
        "this bias may be structurally difficult to eliminate. If RLHF annotator demographics systematically skew "
        "toward one orientation (Santurkar et al., 2023), then bias is not a bug but a structural feature of the "
        "alignment methodology. As Rozado (2024) argues, this is not merely academic when these systems are used "
        "to summarize news, draft policy, and assist in education."
    )
    pdf.subsection_title("5.3 Limitations")
    pdf.bullet("Single-lab model comparison: only Meta Llama models. Future runs should include GPT, Claude, Gemini.")
    pdf.bullet("Single-run temporal snapshot. Longitudinal data needed to assess drift over time.")
    pdf.bullet("Composite score weights (50/30/20) are manually set. Different weightings could shift absolute values.")
    pdf.bullet("0.35 cosine similarity threshold for 'covered' is a judgment call.")
    pdf.bullet(
        "Document-level embeddings dilute brief mentions. A 50-page doc with 2 paragraphs on mental health "
        "scores low even though coverage exists. Passage-level chunking would capture these better."
    )

    # ?? 6. CONCLUSION ????????????????????????????????????????????????????????
    pdf.section_title("6. Conclusion")
    pdf.body_text(
        "The AI safety policy landscape is simultaneously over-concentrated and under-covered. Nine labs converge "
        "on safety guidelines while four critical categories remain policy-free. Even within a single lab's model "
        "family actively calibrating toward neutrality, measurable political asymmetries persist."
    )
    pdf.body_text(
        "These findings suggest the industry needs: (1) expanded policy documentation requirements covering bias, "
        "misinformation, mental health, and political neutrality; (2) standardized cross-lab evaluation frameworks "
        "for political slant; and (3) structural changes to RLHF annotation pipelines that account for annotator "
        "demographic biases."
    )

    # ?? REFERENCES ???????????????????????????????????????????????????????????
    pdf.section_title("References")
    refs = [
        'Borah, A., Roth, D., & Barzilay, R. (2024). "Some Language Reward Models Exhibit Political Bias." MIT CSAIL. NeurIPS 2024.',
        'Bose, A., Perez, F., & Shalaby, W. (2025). "Large Means Left: Political Bias in LLMs Increases with Parameters." arXiv:2505.04393.',
        'Chakraborty, S., et al. (2024). "On the Algorithmic Bias of Aligning LLMs with RLHF: Preference Collapse." arXiv:2405.16455.',
        'Deshpande, A., et al. (2024). "On the Relationship between Truth and Political Bias in Language Models." EMNLP 2024.',
        'Ferrara, E. (2025). "A Survey on Moral Foundation Theory and Pre-Trained Language Models." AI & Society, Springer.',
        'Future of Life Institute. (2025). "AI Safety Index Winter 2025." Cambridge, MA.',
        'Graham, J., Haidt, J., & Nosek, B. (2009). "Liberals and Conservatives Rely on Different Moral Foundations." JPSP 96(5).',
        'Haidt, J., & Graham, J. (2007). "When Morality Opposes Justice." Social Justice Research, 20, 98-116.',
        'Hopp, F.R., et al. (2021). "Extended Moral Foundations Dictionary." Behavior Research Methods, 53, 232-246.',
        'International AI Safety Report. (2025, 2026). International Scientific Advisory Network.',
        'Liang, W., et al. (2024). "What\'s Documented in AI? Systematic Analysis of 32K AI Model Cards." arXiv:2402.05160.',
        'Liu, J., et al. (2024). "Automatic Generation of Model and Data Cards." NAACL 2024.',
        'Mitchell, M., et al. (2019). "Model Cards for Model Reporting." FAccT 2019.',
        'Reimers, N., & Gurevych, I. (2019). "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks." EMNLP 2019.',
        'Rozado, D. (2024). "The Political Preferences of LLMs." PLOS One, 19(7), e0306621.',
        'Rottger, P., et al. (2024). "Measuring Political Bias in LLMs: What Is Said and How It Is Said." ACL 2024.',
        'Santurkar, S., et al. (2023). "Whose Opinions Do Language Models Reflect?" ICML 2023.',
        'Stanford HAI. (2025). "Study Finds Perceived Political Bias in Popular AI Models." Stanford University.',
    ]
    for r in refs:
        pdf.reference(r)

    # ?? BACK MATTER ??????????????????????????????????????????????????????????
    pdf.ln(10)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(0, 4.5,
        "Generated by AI Policy Intelligence -- github.com/owizdom/ai-research-model-cards\n"
        "Data collected March 2026. 33 sources across 9 labs. 25 political probes across 3 Meta Llama models.",
        align="C",
    )

    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    out = reports_dir / "Model Card Report v1.pdf"
    pdf.output(str(out))
    print(f"PDF saved to {out}")


if __name__ == "__main__":
    build()
