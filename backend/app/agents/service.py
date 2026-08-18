from __future__ import annotations

import asyncio
import os
from typing import Protocol

from app.agents.contracts import (
    ProcurementProposal,
    SecurityProposal,
    VendorProposal,
)
from app.agents.definitions import build_agent_fleet
from app.agents.gateway import AgentGateway
from app.agents.tools import MissionToolbox
from app.runtime.entities import RuntimeSnapshot
from app.runtime.errors import RuntimeDomainError


class MissionAgentReasoner(Protocol):
    execution_mode: str

    def review_vendor(self, snapshot: RuntimeSnapshot, work_item_id: str) -> VendorProposal: ...

    def review_security(self, snapshot: RuntimeSnapshot, work_item_id: str) -> SecurityProposal: ...

    def review_procurement(
        self,
        snapshot: RuntimeSnapshot,
        work_item_id: str,
    ) -> ProcurementProposal: ...


class GoogleAdkMissionAgentService:
    execution_mode = "GOOGLE_ADK_GEMINI"

    def __init__(
        self,
        gateway: AgentGateway | None = None,
        *,
        model: str | None = None,
    ) -> None:
        self._gateway = gateway or AgentGateway()
        self._model = model

    @classmethod
    def from_environment(cls) -> "GoogleAdkMissionAgentService":
        using_api_key = bool(
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        )
        using_vertex = (
            os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE"
            and bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))
            and bool(os.environ.get("GOOGLE_CLOUD_LOCATION"))
        )
        if not (using_api_key or using_vertex):
            raise RuntimeDomainError(
                "AGENT_CREDENTIALS_MISSING",
                "Google agent mode requires GEMINI_API_KEY or configured Vertex AI credentials",
            )
        return cls(model=os.environ.get("CONTINUUM_GEMINI_MODEL"))

    def review_vendor(
        self,
        snapshot: RuntimeSnapshot,
        work_item_id: str,
    ) -> VendorProposal:
        return self._run(
            snapshot,
            work_item_id,
            "vendor-agent",
            VendorProposal,
            "Validate Acme Analytics intake completeness. Cite all artifacts used.",
        )

    def review_security(
        self,
        snapshot: RuntimeSnapshot,
        work_item_id: str,
    ) -> SecurityProposal:
        world = snapshot.world
        assert world is not None
        prompt = (
            "Review Acme Analytics against the current security policy. "
            f"Available document IDs: {', '.join(world.documents)}. "
            "Return explicit dependency_refs and a structured verdict."
        )
        return self._run(
            snapshot,
            work_item_id,
            "security-agent",
            SecurityProposal,
            prompt,
        )

    def review_procurement(
        self,
        snapshot: RuntimeSnapshot,
        work_item_id: str,
    ) -> ProcurementProposal:
        return self._run(
            snapshot,
            work_item_id,
            "procurement-agent",
            ProcurementProposal,
            "Review current VALID decisions and propose whether ACTIVATE_VENDOR is authorized.",
        )

    def _run(self, snapshot, work_item_id, agent_id, proposal_type, prompt):  # type: ignore[no-untyped-def]
        fleet = build_agent_fleet(MissionToolbox(snapshot), model=self._model)
        return asyncio.run(
            self._gateway.run(
                fleet[agent_id],
                proposal_type,
                prompt,
                mission_id=snapshot.mission.mission_id,
                work_item_id=work_item_id,
                allowed_refs=self._allowed_refs(snapshot),
            )
        )

    @staticmethod
    def _allowed_refs(snapshot: RuntimeSnapshot) -> set[str]:
        world_refs = set(snapshot.world.artifacts) if snapshot.world else set()
        graph = snapshot.graph
        return (
            world_refs
            | set(graph.artifacts)
            | set(graph.evidences)
            | set(graph.decisions)
        )
