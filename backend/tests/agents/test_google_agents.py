import json

import pytest

from app.agents.contracts import AgentOutcome, SecurityProposal
from app.agents.definitions import build_agent_fleet
from app.agents.gateway import AgentGateway, AgentProposalValidator
from app.agents.service import GoogleAdkMissionAgentService
from app.agents.tools import MissionToolbox
from app.demo.runtime_fixture import seed_runtime_demo
from app.runtime.errors import RuntimeDomainError


def test_agent_fleet_uses_adk_gemini_and_structured_outputs() -> None:
    snapshot = seed_runtime_demo("agent-fleet")
    fleet = build_agent_fleet(MissionToolbox(snapshot), model="gemini-3.6-flash")

    assert set(fleet) == {"vendor-agent", "security-agent", "procurement-agent"}
    assert all(agent.model == "gemini-3.6-flash" for agent in fleet.values())
    assert fleet["security-agent"].output_schema is SecurityProposal
    assert len(fleet["security-agent"].tools) == 3


def test_security_toolbox_exposes_canonical_read_only_context() -> None:
    snapshot = seed_runtime_demo("agent-tools")
    toolbox = MissionToolbox(snapshot)

    assert toolbox.get_security_policy()["version"] == "v12"
    assert toolbox.get_vendor_data_classification() == {
        "vendor_id": "ACME",
        "handles_customer_pii": True,
    }
    assert toolbox.get_document("soc2-A31")["document_type"] == "SOC2"


def test_runtime_rejects_agent_dependency_hallucinations() -> None:
    proposal = SecurityProposal(
        outcome=AgentOutcome.APPROVED,
        dependency_refs=["policy-v13", "invented-document"],
        explanation="Approved using an unknown reference.",
    )

    with pytest.raises(RuntimeDomainError) as raised:
        AgentProposalValidator.validate_refs(
            proposal,
            allowed_refs={"policy-v13", "soc2-A31", "pen-test-P9"},
        )

    assert raised.value.code == "AGENT_REFERENCE_INVALID"


def test_google_agent_service_runs_all_three_bounded_agents() -> None:
    snapshot = seed_runtime_demo("agent-service")
    executor = FakeExecutor()
    service = GoogleAdkMissionAgentService(
        AgentGateway(executor),
        model="gemini-3.6-flash",
    )

    vendor = service.review_vendor(snapshot, "vendor-work")
    security = service.review_security(snapshot, "security-work")
    procurement = service.review_procurement(snapshot, "procurement-work")

    assert vendor.outcome is AgentOutcome.COMPLETE
    assert security.outcome is AgentOutcome.APPROVED
    assert procurement.outcome is AgentOutcome.APPROVED
    assert executor.calls == ["vendor_agent", "security_agent", "procurement_agent"]


def test_google_mode_fails_fast_without_credentials(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeDomainError) as raised:
        GoogleAdkMissionAgentService.from_environment()

    assert raised.value.code == "AGENT_CREDENTIALS_MISSING"


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def execute(self, agent, prompt, *, user_id, session_id):  # type: ignore[no-untyped-def]
        self.calls.append(agent.name)
        payloads = {
            "vendor_agent": {
                "outcome": "COMPLETE",
                "dependency_refs": ["vendor-profile-r7", "soc2-A31"],
                "explanation": "Intake is complete.",
            },
            "security_agent": {
                "outcome": "APPROVED",
                "dependency_refs": ["policy-v12", "soc2-A31"],
                "explanation": "Policy v12 accepts SOC2.",
            },
            "procurement_agent": {
                "outcome": "APPROVED",
                "dependency_refs": ["D42", "D43"],
                "explanation": "Both upstream decisions are valid.",
                "requested_action": "ACTIVATE_VENDOR",
            },
        }
        return json.dumps(payloads[agent.name])
