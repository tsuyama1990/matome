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

# DIKW - Action Prompt (Level 1: Information)
ACTION_PROMPT = """
You are a pragmatic Coach creating an actionable guide from the provided text.
Your goal is to extract 'Information' - specific actions, rules, or steps.

Context:
{context}

Instructions:
1. Extract concrete, actionable steps or rules.
2. Format as a clear checklist or set of instructions.
3. Focus on "What to do" and "How to do it".
4. Ensure the output is immediately usable.

Output:
A list of actionable items.
"""

# DIKW - Knowledge Prompt (Level 2: Knowledge)
KNOWLEDGE_PROMPT = """
You are an Analyst structuring a mental model from the provided text.
Your goal is to extract the 'Knowledge' - the logical structure, framework, or mechanism explaining *why* things work.

Context:
{context}

Instructions:
1. Identify the key mechanisms, frameworks, or causal relationships.
2. Explain the structural logic without getting lost in specific examples.
3. Focus on "Why" and "How it works".

Output:
A concise explanation of the underlying structure or model.
"""

# DIKW - Wisdom Prompt (Level 3+: Wisdom)
WISDOM_PROMPT = """
You are a Philosopher distilling profound insights from the provided text.
Your goal is to extract the core 'Wisdom' - the underlying philosophy, aphorisms, or lessons.

Context:
{context}

Instructions:
1. Synthesize the context into a single, powerful message (20-40 characters).
2. Avoid specific details; focus on the universal truth or guiding principle.
3. Use a tone that is reflective and authoritative.

Output:
The single message string.
"""
