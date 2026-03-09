from enum import StrEnum


class NodeStatus(StrEnum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    COMPLETED = "COMPLETED"


class PivotAxis(StrEnum):
    ACTOR_STATE = "Actor vs. State Transition"
    OPPORTUNITIES_THREATS = "Opportunities vs Threats"
    TIME = "Time Axis"
    SWOT = "SWOT Analysis"
    PESTLE = "PESTLE Analysis"
    CUSTOM = "Custom Axis"
