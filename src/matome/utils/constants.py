"""
Shared constants for the Matome system.
"""

# Patterns for detecting potential prompt injection attacks.
# These are used as literal strings for mitigation checks, or careful regex matching.
# We ensure these patterns are safe and do not expose regex injection vulnerabilities
# by treating them as fixed constants.
PROMPT_INJECTION_PATTERNS: list[str] = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)ignore\s+all\s+instructions",
    r"(?i)system\s+override",
    r"(?i)execute\s+command",
    r"(?i)reveal\s+system\s+prompt",
    r"(?i)bypass\s+security",
    r"(?i)output\s+as\s+json",
]
