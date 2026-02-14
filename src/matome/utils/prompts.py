"""
Prompt templates used in the Matome system.
"""

# Chain of Density Prompt Template
COD_TEMPLATE = """
The following are chunks of text from a larger document, grouped by topic:
{context}

Please generate a high-density summary following these steps:
1. Create an initial summary (~400 chars).
2. Identify missing entities (names, numbers, terms) from the source.
3. Rewrite the summary to include these entities without increasing length.
4. Repeat 3 times.
Output ONLY the final, densest summary.
"""

# Verification Prompt Template
VERIFICATION_TEMPLATE = """
You are a meticulous fact-checker. Your task is to verify the following Summary against the provided Source Text.

Source Text:
{source_text}

Summary:
{summary_text}

Instructions:
1. Identify all factual claims, entities (names, dates, numbers), and specific statements in the Summary.
2. For EACH claim, verify if it is directly supported by the Source Text.
3. If a claim is supported, mark it as "Supported".
4. If a claim is contradicted by the Source Text, mark it as "Contradicted".
5. If a claim is not mentioned or cannot be verified from the Source Text, mark it as "Unsupported".
6. Provide a brief reasoning for each verdict, citing the Source Text if possible.

Output Format:
Return a valid JSON object with the following structure:
{{
  "score": <float between 0.0 and 1.0, representing the percentage of supported claims>,
  "details": [
    {{
      "claim": "<claim text>",
      "verdict": "<Supported|Contradicted|Unsupported>",
      "reasoning": "<explanation>"
    }},
    ...
  ],
  "unsupported_claims": [
    "<list of claims that are Unsupported or Contradicted>"
  ]
}}
"""

# DIKW Prompt Templates

# Level 1: Information (Summarizing Chunks)
INFORMATION_TEMPLATE = """
The following are excerpts from a text, grouped by topic:
{context}

Your task is to synthesize this information into a structured, actionable summary.
- Focus on specific actions, steps, or rules mentioned in the text.
- Use a markdown list format (bullet points or checklists).
- Avoid abstract philosophy; be concrete and detailed.
- If the text describes a process, outline the steps clearly.

Output ONLY the summary.
"""

# Level 2+: Knowledge (Summarizing Summaries)
KNOWLEDGE_TEMPLATE = """
The following are detailed summaries of a larger text:
{context}

Your task is to synthesize these points into a coherent "Knowledge" node.
- Identify the underlying frameworks, mechanisms, or mental models connecting these points.
- Explain "how" and "why" things work, not just "what" to do.
- Structure the output as a clear explanation with headings if necessary.
- Connect the dots between isolated pieces of information.

Output ONLY the summary.
"""

# Root: Wisdom (Summarizing Knowledge)
WISDOM_TEMPLATE = """
The following is a high-level overview of a text:
{context}

Your task is to distill the absolute essence of this information into a "Wisdom" node.
- This should be a profound, memorable insight or aphorism (20-50 words max).
- It should capture the "moral" or the core philosophical truth of the text.
- It must be abstract enough to be applied broadly, yet specific enough to be meaningful.
- Do NOT list points. Write a single, powerful statement or paragraph.

Output ONLY the summary.
"""
