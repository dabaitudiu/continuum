from __future__ import annotations

from typing import Protocol, TypeVar

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from app.agents.contracts import AgentProposal
from app.runtime.errors import RuntimeDomainError


Proposal = TypeVar("Proposal", bound=AgentProposal)


class AgentExecutor(Protocol):
    async def execute(
        self,
        agent: Agent,
        prompt: str,
        *,
        user_id: str,
        session_id: str,
    ) -> str: ...


class AdkGeminiExecutor:
    async def execute(
        self,
        agent: Agent,
        prompt: str,
        *,
        user_id: str,
        session_id: str,
    ) -> str:
        events = await InMemoryRunner(agent=agent).run_debug(
            prompt,
            user_id=user_id,
            session_id=session_id,
            quiet=True,
        )
        for event in reversed(events):
            content = getattr(event, "content", None)
            if content is None:
                continue
            text = "".join(
                part.text or ""
                for part in content.parts or []
                if getattr(part, "text", None)
            )
            if text:
                return text
        raise RuntimeDomainError(
            "AGENT_OUTPUT_MISSING",
            f"ADK agent {agent.name} returned no structured output",
        )


class AgentGateway:
    def __init__(self, executor: AgentExecutor | None = None) -> None:
        self._executor = executor or AdkGeminiExecutor()

    async def run(
        self,
        agent: Agent,
        proposal_type: type[Proposal],
        prompt: str,
        *,
        mission_id: str,
        work_item_id: str,
        allowed_refs: set[str],
    ) -> Proposal:
        raw = await self._executor.execute(
            agent,
            prompt,
            user_id=mission_id,
            session_id=work_item_id,
        )
        proposal = proposal_type.model_validate_json(raw)
        AgentProposalValidator.validate_refs(proposal, allowed_refs=allowed_refs)
        return proposal


class AgentProposalValidator:
    @staticmethod
    def validate_refs(
        proposal: AgentProposal,
        *,
        allowed_refs: set[str],
    ) -> None:
        invalid = sorted(set(proposal.dependency_refs) - allowed_refs)
        if invalid:
            raise RuntimeDomainError(
                "AGENT_REFERENCE_INVALID",
                f"agent proposed unknown dependency refs: {', '.join(invalid)}",
            )
