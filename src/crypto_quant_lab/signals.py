"""Typed, auditable outputs for specialist modules."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class Decision(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True, slots=True)
class SpecialistOpinion:
    specialist_id: str
    observed_at: datetime
    symbol: str
    timeframe: str
    direction: Direction
    score: float
    weight: float = 1.0
    data_quality_ok: bool = True
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.specialist_id.strip():
            raise ValueError("specialist_id must not be empty")
        if not self.symbol.strip() or not self.timeframe.strip():
            raise ValueError("symbol and timeframe must not be empty")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")
        if self.weight < 0.0:
            raise ValueError("weight must not be negative")


@dataclass(frozen=True, slots=True)
class EnsembleDecision:
    symbol: str
    timeframe: str
    decision: Decision
    confidence: float
    long_support: float
    short_support: float
    specialists_used: int
    reason: str
