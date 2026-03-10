# constants.py
import enum


class TaskType(enum.Enum):
    FAST = "fast"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"
