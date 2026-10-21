"""Structured, auditable opinions from trading research specialists."""
from dataclasses import asdict, dataclass, field
from typing import Literal

Action = Literal["LONG", "SHORT", "NO_TRADE"]

@dataclass(frozen=True)
class ExpertOpinion:
    agent_id: str
    specialty: str
    market_context: str
    action: Action = "NO_TRADE"
    time_horizon: str = "unspecified"
    evidence: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    invalidation: list[str] = field(default_factory=list)
    confidence: float = 0.0
    missing_data: list[str] = field(default_factory=list)
    proposed_test: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.action == "NO_TRADE" and not self.missing_data and not self.evidence:
            object.__setattr__(self, "missing_data", ["Insufficient evidence for a directional opinion"])

    def to_dict(self) -> dict:
        return asdict(self)
