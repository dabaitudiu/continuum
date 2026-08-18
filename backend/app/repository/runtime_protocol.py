from typing import Protocol

from app.runtime.entities import InboxRecord, RuntimeSnapshot
from app.runtime.mutations import RuntimeMutation


class RuntimeRepository(Protocol):
    def create(self, snapshot: RuntimeSnapshot) -> None: ...

    def load(self, mission_id: str) -> RuntimeSnapshot: ...

    def find_inbox(
        self,
        mission_id: str,
        message_id: str,
    ) -> InboxRecord | None: ...

    def commit(
        self,
        mission_id: str,
        expected_revision: int,
        mutation: RuntimeMutation,
    ) -> RuntimeSnapshot: ...
