"""
Shared constants for the Matome system.
"""

# Regex patterns for detecting potential prompt injection attacks
PROMPT_INJECTION_PATTERNS: list[str] = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)ignore\s+all\s+instructions",
    r"(?i)system\s+override",
    r"(?i)execute\s+command",
    r"(?i)reveal\s+system\s+prompt",
    r"(?i)bypass\s+security",
    r"(?i)output\s+as\s+json",
]
