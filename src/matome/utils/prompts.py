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

# Action / Information Template (L3)
ACTION_TEMPLATE = """
The following text contains detailed information:
{context}

Please extract actionable steps, rules, and procedures.
Format the output as a clear "How-to" guide or a checklist.
Focus on immediate utility and execution.
Avoid abstract theory; focus on "What to do".
"""

# Knowledge Template (L2)
KNOWLEDGE_TEMPLATE = """
The following text contains specific information and actions:
{context}

Please synthesize the underlying logic, frameworks, and mechanisms.
Explain "Why" this works, rather than just "What" happens.
Avoid specific examples unless necessary to illustrate a structural concept.
Focus on the mental model or system dynamics.
"""

# Wisdom Template (L1)
WISDOM_TEMPLATE = """
The following text contains knowledge and frameworks:
{context}

Please distill the core philosophy, lesson, or truth into a SINGLE, profound message.
The message should be extremely concise (ideally 20-40 characters).
Strip away all context and specific details.
Return only the aphorism or key insight.
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
