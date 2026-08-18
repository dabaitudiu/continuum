from uuid import NAMESPACE_URL, uuid5

from app.demo.fixture import seed_canonical_mission
from app.repository.memory import InMemoryGraphRepository
from app.runtime.entities import (
    AuditEvent,
    InboxRecord,
    Mission,
    OutboxMessage,
    RuntimeSnapshot,
    WorkItem,
)


def demo_mission_id(request_id: str) -> str:
    identity = uuid5(
        NAMESPACE_URL,
        f"https://continuum.local/demo/{request_id}",
    )
    return f"demo-{identity}"


def seed_runtime_demo(request_id: str) -> RuntimeSnapshot:
    mission_id = demo_mission_id(request_id)
    graph_repository = InMemoryGraphRepository()
    seed_canonical_mission(graph_repository, mission_id)
    graph = graph_repository.get_snapshot(mission_id)
    mission = Mission(
        mission_id=mission_id,
        event_sequence=1,
    )
    result = {
        "mission_id": mission_id,
        "status": mission.status.value,
    }
    return RuntimeSnapshot(
        mission=mission,
        graph=graph,
        work_items=[
            WorkItem(
                work_item_id=f"{mission_id}:work:vendor-intake",
                mission_id=mission_id,
                work_type="VENDOR_INTAKE",
                target_agent="vendor-agent",
            )
        ],
        inbox=[
            InboxRecord(
                mission_id=mission_id,
                message_id=request_id,
                message_type="mission.create",
                result=result,
            )
        ],
        outbox=[
            OutboxMessage(
                outbox_message_id=f"outbox:{request_id}:created",
                mission_id=mission_id,
                event_type="mission.created",
                payload=result,
                correlation_id=request_id,
                causation_id=request_id,
            )
        ],
        audit_events=[
            AuditEvent(
                audit_event_id=f"audit:{request_id}:created",
                mission_id=mission_id,
                event_sequence=1,
                event_type="mission.created",
                payload=result,
                correlation_id=request_id,
                causation_id=request_id,
            )
        ],
    )
