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
    outcome_options: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("request_id", "execution_id", "decision_type", "task"):
            value = getattr(self, name)
            if not value.strip() or value != value.strip():
                raise ValueError(f"{name} must be non-empty and trimmed")
        if not self.outcome_options:
            raise ValueError("outcome_options must be non-empty")
        if any(
            not outcome.strip() or outcome != outcome.strip()
            for outcome in self.outcome_options
        ):
            raise ValueError("outcome_options must contain trimmed non-empty values")
        if len(self.outcome_options) != len(set(self.outcome_options)):
            raise ValueError("outcome_options must be unique")
