from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PRDiff:
    id: int
    diff: str
