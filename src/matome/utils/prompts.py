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

# Wisdom Prompt Template (L1)
WISDOM_TEMPLATE = """
Read the following text carefully:
{context}

Your task is to distill the core essence of this text into a single "Wisdom" statement.
- Format: A philosophical aphorism, a profound truth, or a core lesson.
- Constraint: Use exactly 20 to 50 characters.
- Tone: Timeless, abstract, and insightful.
- Do NOT include specific names, dates, or trivial details.

Output ONLY the Wisdom statement.
"""

# Knowledge Prompt Template (L2)
KNOWLEDGE_TEMPLATE = """
Read the following text carefully:
{context}

Your task is to extract the "Knowledge" from this text.
- Focus: The underlying mental models, frameworks, mechanisms, or "Why" logic.
- Format: Explain the structural logic that supports the main idea.
- Avoid: Mere lists of facts or specific anecdotes.
- Goal: Help the reader understand the "System" or "Principles" at work.

Output the explanation clearly and concisely.
"""

# Information Prompt Template (L3)
INFORMATION_TEMPLATE = """
Read the following text carefully:
{context}

Your task is to extract actionable "Information" from this text.
- Focus: Actionable steps, checklists, rules, or "How-to" instructions.
- Format: A bulleted list or a step-by-step guide.
- Goal: Enable the reader to apply this information immediately.
- If no clear actions exist, summarize the key factual takeaways.

Output the actionable information clearly.
"""

# Refinement Prompt Template
REFINE_TEMPLATE = """
You are assisting a user in refining a specific part of a knowledge base.

Original Content:
{original_content}

User Instruction:
{instruction}

Your Task:
Rewrite the Original Content strictly following the User Instruction.
- Do not add conversational filler (e.g., "Here is the rewritten text").
- Maintain the original intent unless the instruction says otherwise.
- Output ONLY the rewritten content.
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
