from dataclasses import dataclass
from typing import Literal

Boundary = Literal["paragraph", "sentence", "comma", "other"]


@dataclass(frozen=True)
class Chapter:
    title: str
    body: str


@dataclass(frozen=True)
class Chunk:
    text: str
    boundary: Boundary
