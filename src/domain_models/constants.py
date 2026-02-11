DEBUG_MSG_CUDA_AVAILABLE = "CUDA available: {}"
DEBUG_MSG_CUDA_COUNT = "Number of GPUs: {}"
DEBUG_MSG_CURRENT_DEVICE = "Current device ID: {}"
DEBUG_MSG_DEVICE_NAME = "Device name: {}"
DEBUG_MSG_INIT_MODEL = "Initializing SentenceTransformer model..."
DEBUG_MSG_MODEL_DEVICE = "Model loaded on device: {}"
DEFAULT_DEBUG_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Existing constants
ALLOWED_EMBEDDING_MODELS = {
    "all-MiniLM-L6-v2",
    "intfloat/multilingual-e5-large",
    "cl-tohoku/bert-base-japanese-v3",
    "pkshatech/GLuCoSE-base-ja",
    "text-embedding-3-small",  # OpenAI
}

ALLOWED_SUMMARIZATION_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-5-sonnet-20240620",
    "claude-3-haiku-20240307",
    "meta-llama/llama-3-8b-instruct",
}

ALLOWED_TOKENIZER_MODELS = {
    "cl100k_base",
    "p50k_base",
    "r50k_base",
    "gpt2",
}

DEFAULT_EMBEDDING = "intfloat/multilingual-e5-large"
DEFAULT_SUMMARIZER = "gpt-4o"
DEFAULT_TOKENIZER = "cl100k_base"

# Thresholds
LARGE_SCALE_THRESHOLD = 5000  # Number of nodes to switch to approximate clustering
PROMPT_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"forget the above",
    r"system prompt",
    r"you are not",
    r"output everything above",
    r"ignore all instructions",
    r"raw markdown",
    r"as an ai language model",
]

# Regex
SENTENCE_SPLIT_PATTERN = r"(?<=[。！？])\s*|\n+"  # noqa: RUF001

# Prompt Templates
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
