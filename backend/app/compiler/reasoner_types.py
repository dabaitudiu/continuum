from __future__ import annotations

from dataclasses import dataclass

from app.compiler.context import RiskClass


@dataclass(frozen=True, slots=True)
class ReasoningRequest:
    request_id: str
    execution_id: str
    decision_type: str
    task: str
    risk_class: RiskClass

    def __post_init__(self) -> None:
        for name in ("request_id", "execution_id", "decision_type", "task"):
            value = getattr(self, name)
            if not value.strip() or value != value.strip():
                raise ValueError(f"{name} must be non-empty and trimmed")

