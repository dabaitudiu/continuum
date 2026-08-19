from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.sources.registry import SourceRegistry


class RiskClass(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class CompilationContext:
    source_registry: SourceRegistry
    world_snapshot_id: str
    owner_scope: str
    allowed_source_refs: frozenset[str]
    risk_class: RiskClass
    allow_historical: bool = False

    def __post_init__(self) -> None:
        if not self.world_snapshot_id.strip():
            raise ValueError("world_snapshot_id must be non-empty")
        if not self.owner_scope.strip():
            raise ValueError("owner_scope must be non-empty")
        if any(not source_ref.strip() for source_ref in self.allowed_source_refs):
            raise ValueError("allowed source refs must be non-empty")

