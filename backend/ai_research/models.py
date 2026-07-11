from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


Direction = Literal["positive", "neutral", "negative"]


@dataclass
class AgentOpinion:
    agent_id: str
    name: str
    role: str
    score: float
    direction: Direction
    summary: str
    evidence: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

