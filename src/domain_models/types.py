from enum import StrEnum


class DIKWLevel(StrEnum):
    DATA = "data"
    INFORMATION = "information"
    KNOWLEDGE = "knowledge"
    WISDOM = "wisdom"


class CanvasNodeType(StrEnum):
    SUMMARY = "summary"
    INSIGHT = "insight"
    EVIDENCE = "evidence"


NodeID = int | str
