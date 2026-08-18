import pytest

from app.agents.contracts import AgentOutcome, SecurityProposal
from app.agents.definitions import build_agent_fleet
from app.agents.gateway import AgentProposalValidator
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
