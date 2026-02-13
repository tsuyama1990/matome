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

# Cycle 02: DIKW Prompt Templates

WISDOM_TEMPLATE = """
You are a philosopher. Read the text and output ONE sentence capturing the deepest truth or "One Big Idea".

Distill it into a single, punchy aphorism (20-40 chars). Do not use specific names or dates.

Text:
{context}

Output ONLY the aphorism.
"""

KNOWLEDGE_TEMPLATE = """
You are a professor. Explain the mental models, frameworks, or causal relationships ('Why' and 'How') in the text.

Structure the output as key concepts.

Text:
{context}

Output the structured explanation.
"""

INFORMATION_TEMPLATE = """
You are a tactical advisor. Extract actionable advice, checklists, or procedures ('What to do').

Format as a markdown checklist (e.g., - [ ] Do X).

Text:
{context}

Output the markdown checklist.
"""
