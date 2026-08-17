from app.domain.models import GraphSnapshot


class InMemoryGraphRepository:
    def __init__(self) -> None:
        self._snapshots: dict[str, GraphSnapshot] = {}
        self._processed_events: dict[str, set[str]] = {}
        self._processed_requests: dict[str, set[str]] = {}

    def create_snapshot(self, snapshot: GraphSnapshot) -> None:
        if snapshot.mission_id in self._snapshots:
            raise ValueError(f"mission already exists: {snapshot.mission_id}")
        self._snapshots[snapshot.mission_id] = snapshot.model_copy(deep=True)
        self._processed_events[snapshot.mission_id] = set()
        self._processed_requests[snapshot.mission_id] = set()

    def get_snapshot(self, mission_id: str) -> GraphSnapshot:
        try:
            return self._snapshots[mission_id].model_copy(deep=True)
        except KeyError as error:
            raise KeyError(f"unknown mission: {mission_id}") from error

    def save_snapshot(self, snapshot: GraphSnapshot) -> None:
        if snapshot.mission_id not in self._snapshots:
            raise KeyError(f"unknown mission: {snapshot.mission_id}")
        self._snapshots[snapshot.mission_id] = snapshot.model_copy(deep=True)

    def has_processed_event(self, mission_id: str, event_id: str) -> bool:
        self._require_mission(mission_id)
        return event_id in self._processed_events[mission_id]

    def mark_event_processed(self, mission_id: str, event_id: str) -> None:
        self._require_mission(mission_id)
        self._processed_events[mission_id].add(event_id)

    def has_processed_request(self, mission_id: str, request_id: str) -> bool:
        self._require_mission(mission_id)
        return request_id in self._processed_requests[mission_id]

    def mark_request_processed(self, mission_id: str, request_id: str) -> None:
        self._require_mission(mission_id)
        self._processed_requests[mission_id].add(request_id)

    def _require_mission(self, mission_id: str) -> None:
        if mission_id not in self._snapshots:
            raise KeyError(f"unknown mission: {mission_id}")

