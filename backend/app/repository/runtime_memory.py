from threading import RLock

from app.repository.runtime_validation import (
    build_committed_snapshot,
    validate_initial_snapshot,
)
from app.runtime.entities import InboxRecord, RuntimeSnapshot
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation


class InMemoryRuntimeRepository:
    def __init__(self) -> None:
        self._snapshots: dict[str, RuntimeSnapshot] = {}
        self._lock = RLock()

    def create(self, snapshot: RuntimeSnapshot) -> None:
        with self._lock:
            mission_id = snapshot.mission.mission_id
            if mission_id in self._snapshots:
                raise RuntimeDomainError(
                    "MISSION_ALREADY_EXISTS",
                    f"mission already exists: {mission_id}",
                )
            validate_initial_snapshot(snapshot)
            self._snapshots[mission_id] = snapshot.model_copy(deep=True)

    def load(self, mission_id: str) -> RuntimeSnapshot:
        with self._lock:
            return self._require(mission_id).model_copy(deep=True)

    def find_inbox(
        self,
        mission_id: str,
        message_id: str,
    ) -> InboxRecord | None:
        with self._lock:
            snapshot = self._require(mission_id)
            for record in snapshot.inbox:
                if record.message_id == message_id:
                    return record.model_copy(deep=True)
            return None

    def commit(
        self,
        mission_id: str,
        expected_revision: int,
        mutation: RuntimeMutation,
    ) -> RuntimeSnapshot:
        with self._lock:
            current = self._require(mission_id)
            committed = build_committed_snapshot(
                current,
                expected_revision,
                mutation,
            )
            self._snapshots[mission_id] = committed
            return committed.model_copy(deep=True)

    def _require(self, mission_id: str) -> RuntimeSnapshot:
        try:
            return self._snapshots[mission_id]
        except KeyError as error:
            raise RuntimeDomainError(
                "MISSION_NOT_FOUND",
                f"mission does not exist: {mission_id}",
            ) from error
