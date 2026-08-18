from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field, ValidationError

from app.runtime.coordinator import CommandResult, RuntimeCoordinator
from app.runtime.entities import RuntimeEvent, RuntimeSnapshot
from app.runtime.errors import RuntimeDomainError
from app.api.read_models import control_read_model


class CreateMissionRequest(BaseModel):
    request_id: str = Field(min_length=1)


class StartMissionRequest(BaseModel):
    request_id: str = Field(min_length=1)


class EventEnvelopeRequest(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    producer: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    trace_id: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, str]

    def to_runtime_event(self) -> RuntimeEvent:
        required_by_type = {
            "vendor.document.uploaded": {
                "vendor_id",
                "document_id",
                "document_type",
            }
        }
        missing = required_by_type.get(self.event_type, set()).difference(
            self.payload
        )
        if missing:
            raise RuntimeDomainError(
                "EVENT_SCHEMA_INVALID",
                f"missing payload fields: {', '.join(sorted(missing))}",
            )
        return RuntimeEvent.model_validate(self.model_dump())


def build_runtime_router(coordinator: RuntimeCoordinator) -> APIRouter:
    router = APIRouter()

    @router.post("/api/missions/demo")
    def create_demo(request: CreateMissionRequest) -> dict[str, Any]:
        return _command_response(coordinator.create_demo(request.request_id))

    @router.post("/api/missions/{mission_id}/start")
    def start_mission(
        mission_id: str,
        request: StartMissionRequest,
    ) -> dict[str, Any]:
        return _command_response(
            coordinator.start(mission_id, request.request_id)
        )

    @router.get("/api/missions/{mission_id}")
    def get_mission(mission_id: str) -> dict[str, Any]:
        return _mission_summary(coordinator.get(mission_id))

    @router.get("/api/missions/{mission_id}/timeline")
    def get_timeline(mission_id: str) -> list[dict[str, Any]]:
        return [
            event.model_dump(mode="json")
            for event in coordinator.timeline(mission_id)
        ]

    @router.get("/api/missions/{mission_id}/commitments")
    def get_commitments(mission_id: str) -> list[dict[str, Any]]:
        return [
            commitment.model_dump(mode="json")
            for commitment in coordinator.commitments(mission_id)
        ]

    @router.get("/api/missions/{mission_id}/control")
    def get_control(mission_id: str) -> dict[str, Any]:
        return control_read_model(coordinator.get(mission_id))

    @router.post("/api/events")
    def process_event(
        body: dict[str, Any] = Body(...),
    ) -> dict[str, Any]:
        try:
            request = EventEnvelopeRequest.model_validate(body)
        except ValidationError as error:
            raise RuntimeDomainError(
                "EVENT_SCHEMA_INVALID",
                error.errors(include_url=False)[0]["msg"],
            ) from error
        return _command_response(
            coordinator.process_event(request.to_runtime_event())
        )

    return router


def _command_response(command: CommandResult) -> dict[str, Any]:
    return {
        **_mission_summary(command.snapshot),
        "duplicate": command.duplicate,
        "result": command.result,
    }


def _mission_summary(snapshot: RuntimeSnapshot) -> dict[str, Any]:
    return {
        "mission_id": snapshot.mission.mission_id,
        "mission_type": snapshot.mission.mission_type,
        "subject_id": snapshot.mission.subject_id,
        "status": snapshot.mission.status.value,
        "revision": snapshot.mission.revision,
        "event_sequence": snapshot.mission.event_sequence,
        "created_at": snapshot.mission.created_at.isoformat(),
        "updated_at": snapshot.mission.updated_at.isoformat(),
        "counts": {
            "work_items": len(snapshot.work_items),
            "open_commitments": sum(
                commitment.status.value == "OPEN"
                for commitment in snapshot.commitments
            ),
            "side_effects": len(snapshot.side_effects),
        },
    }
