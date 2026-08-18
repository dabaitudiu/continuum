from app.agents.contracts import (
    AgentOutcome,
    ProcurementProposal,
    SecurityProposal,
    VendorProposal,
)
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.runtime.coordinator import RuntimeCoordinator
from app.runtime.entities import ExecutionMode, MissionStatus


def test_google_agent_proposals_drive_bounded_full_story() -> None:
    reasoner = StubGoogleReasoner()
    coordinator = RuntimeCoordinator(InMemoryRuntimeRepository(), reasoner)
    created = coordinator.create_demo("agent-integrated")
    mission_id = created.snapshot.mission.mission_id

    started = coordinator.start(mission_id, "agent-start")
    coordinator.upgrade_policy(mission_id, "agent-policy")
    waiting = coordinator.revalidate_affected_branch(mission_id, "agent-revalidate")
    completed = coordinator.upload_pen_test(mission_id, "agent-pen-test")

    assert started.snapshot.world is not None
    assert started.snapshot.world.execution_mode is ExecutionMode.GOOGLE_ADK_GEMINI
    assert waiting.result["execution_mode"] == "GOOGLE_ADK_GEMINI"
    assert completed.snapshot.mission.status is MissionStatus.COMPLETED
    assert reasoner.calls == [
        "vendor:v12",
        "security:v12:no-pen-test",
        "procurement:v12",
        "security:v13:no-pen-test",
        "security:v13:pen-test",
        "procurement:v13",
    ]
    accepted = [
        event for event in completed.snapshot.audit_events
        if event.event_type == "agent.result.accepted"
    ]
    assert len(accepted) == 6
    assert all(
        event.payload["execution_mode"] == "GOOGLE_ADK_GEMINI"
        for event in accepted
    )


class StubGoogleReasoner:
    execution_mode = "GOOGLE_ADK_GEMINI"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def review_vendor(self, snapshot, work_item_id):  # type: ignore[no-untyped-def]
        self.calls.append("vendor:v12")
        return VendorProposal(
            outcome=AgentOutcome.COMPLETE,
            dependency_refs=["vendor-profile-r7", "soc2-A31"],
            explanation="Vendor profile and SOC2 are present.",
        )

    def review_security(self, snapshot, work_item_id):  # type: ignore[no-untyped-def]
        world = snapshot.world
        assert world is not None
        policy = world.artifacts[world.current_policy_id].version
        has_pen_test = "pen-test-P9" in world.documents
        self.calls.append(
            f"security:{policy}:{'pen-test' if has_pen_test else 'no-pen-test'}"
        )
        if policy == "v13" and not has_pen_test:
            return SecurityProposal(
                outcome=AgentOutcome.MISSING_EVIDENCE,
                dependency_refs=["policy-v13", "vendor-profile-r7"],
                missing_document_type="PEN_TEST",
                explanation="Policy v13 requires a penetration test.",
            )
        return SecurityProposal(
            outcome=AgentOutcome.APPROVED,
            dependency_refs=[
                world.current_policy_id,
                "pen-test-P9" if has_pen_test else "soc2-A31",
            ],
            explanation="Current policy requirements are satisfied.",
        )

    def review_procurement(self, snapshot, work_item_id):  # type: ignore[no-untyped-def]
        world = snapshot.world
        assert world is not None
        policy = world.artifacts[world.current_policy_id].version
        self.calls.append(f"procurement:{policy}")
        return ProcurementProposal(
            outcome=AgentOutcome.APPROVED,
            dependency_refs=["D57", "D43"] if policy == "v13" else ["D42", "D43"],
            requested_action="ACTIVATE_VENDOR",
            explanation="Current upstream decisions authorize activation.",
        )
