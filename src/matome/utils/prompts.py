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

# --- DIKW Strategy Templates ---

WISDOM_TEMPLATE = """
You are a philosopher and systems thinker.
The following text represents the distilled knowledge of a document:
{context}

Your task is to synthesize this into "Wisdom" - the core insight, moral, or philosophical essence.
- Be concise (under 50 words).
- Focus on the "Why" and the "Big Idea".
- Use abstract, high-level language but remain clear.
- Do not list facts; provide a unified perspective.

Output ONLY the wisdom statement.
"""

KNOWLEDGE_TEMPLATE = """
You are an expert educator and analyst.
The following text contains detailed information about a specific topic:
{context}

Your task is to synthesize this into "Knowledge" - a structured understanding of the "How" and "What".
- Identify key frameworks, mechanisms, or relationships.
- Explain how concepts connect.
- Use bullet points or a short paragraph.
- Focus on structure and logic.

Output the knowledge summary.
"""

INFORMATION_TEMPLATE = """
You are a pragmatic technical writer.
The following text contains raw data and excerpts:
{context}

Your task is to organize this into "Information" - actionable, specific, and organized facts.
- Create a Markdown checklist or a "How-to" guide if applicable.
- Extract specific dates, names, steps, and rules.
- Be detailed and precise.
- Avoid abstract philosophy.

Output the actionable information.
"""

REFINEMENT_INSTRUCTION_TEMPLATE = """
You are an expert editor refining a summary based on user feedback.

Original Text/Context:
{context}

User Instruction:
{instruction}

Task:
Rewrite the summary to fully incorporate the user's instruction while maintaining accuracy to the original context.
- If the instruction asks to change the tone (e.g., "like a 5-year-old"), adjust the style accordingly.
- If the instruction asks to add/remove details, do so based on the provided context.
- Ensure the result is coherent and standalone.

Output ONLY the refined summary.
"""
