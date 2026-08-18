from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.models import GraphSnapshot
from app.runtime.entities import (
    AuditEvent,
    InboxRecord,
    Mission,
    MissionStatus,
    OutboxMessage,
    RuntimeSnapshot,
    SideEffectRecord,
    WorkItem,
)
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation


def runtime_snapshot(mission_id: str = "m-1") -> RuntimeSnapshot:
    return RuntimeSnapshot(
        mission=Mission(mission_id=mission_id),
        graph=GraphSnapshot(mission_id=mission_id),
    )


def transition_mutation(
    snapshot: RuntimeSnapshot,
    *,
    message_id: str,
    status: MissionStatus = MissionStatus.RUNNING,
    side_effects: list[SideEffectRecord] | None = None,
    event_sequence: int | None = None,
) -> RuntimeMutation:
    sequence = event_sequence or snapshot.mission.event_sequence + 1
    mission = snapshot.mission.model_copy(update={"status": status}, deep=True)
    return RuntimeMutation(
        mission=mission,
        side_effect_upserts=side_effects or [],
        audit_appends=[
            AuditEvent(
                audit_event_id=f"audit:{message_id}",
                mission_id=mission.mission_id,
                event_sequence=sequence,
                event_type="mission.status.changed",
                payload={"status": status.value},
                correlation_id=message_id,
                causation_id=message_id,
            )
        ],
        inbox_completion=InboxRecord(
            mission_id=mission.mission_id,
            message_id=message_id,
            message_type="command",
            result={"status": status.value},
        ),
        outbox_appends=[
            OutboxMessage(
                outbox_message_id=f"outbox:{message_id}",
                mission_id=mission.mission_id,
                event_type="mission.status.changed",
                payload={"status": status.value},
                correlation_id=message_id,
                causation_id=message_id,
            )
        ],
    )


def activation_effect(
    *,
    side_effect_id: str,
    idempotency_key: str = "activate:ACME",
) -> SideEffectRecord:
    return SideEffectRecord(
        side_effect_id=side_effect_id,
        mission_id="m-1",
        effect_type="ACTIVATE_VENDOR",
        idempotency_key=idempotency_key,
        authorization_decision_id="D50",
    )


class RuntimeRepositoryContract:
    def make_repo(self, tmp_path: Path):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def test_create_and_load_are_deep_copy_isolated(self, tmp_path: Path) -> None:
        repo = self.make_repo(tmp_path)
        original = runtime_snapshot()

        repo.create(original)
        original.mission.status = MissionStatus.CANCELLED
        first = repo.load("m-1")
        first.mission.status = MissionStatus.FAILED
        second = repo.load("m-1")

        assert second.mission.status is MissionStatus.CREATED

    def test_duplicate_create_is_rejected(self, tmp_path: Path) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())

        with pytest.raises(RuntimeDomainError) as raised:
            repo.create(runtime_snapshot())

        assert raised.value.code == "MISSION_ALREADY_EXISTS"

    def test_unknown_mission_is_rejected(self, tmp_path: Path) -> None:
        repo = self.make_repo(tmp_path)

        with pytest.raises(RuntimeDomainError) as raised:
            repo.load("missing")

        assert raised.value.code == "MISSION_NOT_FOUND"

    def test_list_recent_is_ordered_limited_and_copy_isolated(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        timestamps = [
            datetime(2026, 8, 18, 8, 0, tzinfo=UTC),
            datetime(2026, 8, 18, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 18, 9, 0, tzinfo=UTC),
        ]
        for mission_id, updated_at in zip(
            ("m-oldest", "m-newest", "m-middle"),
            timestamps,
            strict=True,
        ):
            snapshot = runtime_snapshot(mission_id)
            snapshot.mission.updated_at = updated_at
            repo.create(snapshot)

        recent = repo.list_recent(2)
        recent[0].mission.status = MissionStatus.FAILED

        assert [item.mission.mission_id for item in recent] == [
            "m-newest",
            "m-middle",
        ]
        assert repo.load("m-newest").mission.status is MissionStatus.CREATED

    def test_find_inbox_rejects_unknown_mission(self, tmp_path: Path) -> None:
        repo = self.make_repo(tmp_path)

        with pytest.raises(RuntimeDomainError) as raised:
            repo.find_inbox("missing", "request-1")

        assert raised.value.code == "MISSION_NOT_FOUND"

    def test_initial_entities_must_belong_to_mission(self, tmp_path: Path) -> None:
        repo = self.make_repo(tmp_path)
        snapshot = runtime_snapshot()
        snapshot.work_items.append(
            WorkItem(
                work_item_id="work-1",
                mission_id="other",
                work_type="SECURITY_REVIEW",
            )
        )

        with pytest.raises(RuntimeDomainError) as raised:
            repo.create(snapshot)

        assert raised.value.code == "MISSION_ID_CONFLICT"

    def test_initial_outbox_ids_must_be_unique(self, tmp_path: Path) -> None:
        repo = self.make_repo(tmp_path)
        snapshot = runtime_snapshot()
        message = OutboxMessage(
            outbox_message_id="outbox-1",
            mission_id="m-1",
            event_type="mission.created",
            correlation_id="create-1",
            causation_id="create-1",
        )
        snapshot.outbox = [message, message.model_copy(deep=True)]

        with pytest.raises(RuntimeDomainError) as raised:
            repo.create(snapshot)

        assert raised.value.code == "OUTBOX_MESSAGE_CONFLICT"

    def test_initial_audit_sequence_must_start_at_one(self, tmp_path: Path) -> None:
        repo = self.make_repo(tmp_path)
        snapshot = runtime_snapshot()
        snapshot.mission.event_sequence = 1
        snapshot.audit_events = [
            AuditEvent(
                audit_event_id="audit-2",
                mission_id="m-1",
                event_sequence=2,
                event_type="mission.created",
                correlation_id="create-1",
                causation_id="create-1",
            )
        ]

        with pytest.raises(RuntimeDomainError) as raised:
            repo.create(snapshot)

        assert raised.value.code == "AUDIT_SEQUENCE_CONFLICT"

    def test_initial_mission_sequence_must_match_audit_history(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        snapshot = runtime_snapshot()
        snapshot.mission.event_sequence = 1

        with pytest.raises(RuntimeDomainError) as raised:
            repo.create(snapshot)

        assert raised.value.code == "AUDIT_SEQUENCE_CONFLICT"

    def test_commit_updates_state_revision_audit_inbox_and_outbox_atomically(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        initial = repo.load("m-1")

        committed = repo.commit(
            "m-1",
            initial.mission.revision,
            transition_mutation(initial, message_id="request-1"),
        )

        assert committed.mission.status is MissionStatus.RUNNING
        assert committed.mission.revision == 1
        assert committed.mission.event_sequence == 1
        assert [event.event_sequence for event in committed.audit_events] == [1]
        assert [message.event_type for message in committed.outbox] == [
            "mission.status.changed"
        ]
        inbox = repo.find_inbox("m-1", "request-1")
        assert inbox is not None
        assert inbox.result == {"status": "RUNNING"}

    def test_stale_revision_cannot_overwrite_committed_state(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        base = repo.load("m-1")
        repo.commit(
            "m-1",
            base.mission.revision,
            transition_mutation(base, message_id="request-1"),
        )

        with pytest.raises(RuntimeDomainError) as raised:
            repo.commit(
                "m-1",
                base.mission.revision,
                transition_mutation(base, message_id="request-2"),
            )

        assert raised.value.code == "REVISION_CONFLICT"
        assert repo.load("m-1").mission.status is MissionStatus.RUNNING

    def test_duplicate_inbox_message_rolls_back_every_change(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        first = repo.commit(
            "m-1",
            0,
            transition_mutation(repo.load("m-1"), message_id="request-1"),
        )

        with pytest.raises(RuntimeDomainError) as raised:
            repo.commit(
                "m-1",
                first.mission.revision,
                transition_mutation(
                    first,
                    message_id="request-1",
                    status=MissionStatus.WAITING,
                ),
            )

        assert raised.value.code == "MESSAGE_ALREADY_PROCESSED"
        assert repo.load("m-1") == first

    def test_duplicate_side_effect_idempotency_rolls_back_every_change(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        before = repo.load("m-1")
        mutation = transition_mutation(
            before,
            message_id="request-1",
            side_effects=[
                activation_effect(side_effect_id="effect-1"),
                activation_effect(side_effect_id="effect-2"),
            ],
        )

        with pytest.raises(RuntimeDomainError) as raised:
            repo.commit("m-1", 0, mutation)

        assert raised.value.code == "SIDE_EFFECT_IDEMPOTENCY_CONFLICT"
        assert repo.load("m-1") == before
        assert repo.find_inbox("m-1", "request-1") is None

    def test_noncontiguous_audit_sequence_is_rejected_without_mutation(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        before = repo.load("m-1")

        with pytest.raises(RuntimeDomainError) as raised:
            repo.commit(
                "m-1",
                0,
                transition_mutation(
                    before,
                    message_id="request-1",
                    event_sequence=2,
                ),
            )

        assert raised.value.code == "AUDIT_SEQUENCE_CONFLICT"
        assert repo.load("m-1") == before

    def test_mutation_without_audit_is_rejected_without_mutation(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        before = repo.load("m-1")
        mutation = transition_mutation(before, message_id="request-1")
        mutation.audit_appends = []

        with pytest.raises(RuntimeDomainError) as raised:
            repo.commit("m-1", 0, mutation)

        assert raised.value.code == "AUDIT_SEQUENCE_CONFLICT"
        assert repo.load("m-1") == before

    def test_duplicate_audit_identity_is_rejected_without_mutation(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        first = repo.commit(
            "m-1",
            0,
            transition_mutation(repo.load("m-1"), message_id="request-1"),
        )
        mutation = transition_mutation(
            first,
            message_id="request-2",
            status=MissionStatus.WAITING,
        )
        mutation.audit_appends[0].audit_event_id = "audit:request-1"

        with pytest.raises(RuntimeDomainError) as raised:
            repo.commit("m-1", first.mission.revision, mutation)

        assert raised.value.code == "AUDIT_EVENT_CONFLICT"
        assert repo.load("m-1") == first

    def test_duplicate_outbox_identity_rolls_back_every_change(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        first = repo.commit(
            "m-1",
            0,
            transition_mutation(repo.load("m-1"), message_id="request-1"),
        )
        mutation = transition_mutation(
            first,
            message_id="request-2",
            status=MissionStatus.WAITING,
        )
        mutation.outbox_appends[0].outbox_message_id = "outbox:request-1"

        with pytest.raises(RuntimeDomainError) as raised:
            repo.commit("m-1", first.mission.revision, mutation)

        assert raised.value.code == "OUTBOX_MESSAGE_CONFLICT"
        assert repo.load("m-1") == first

    def test_find_inbox_returns_isolated_copy(self, tmp_path: Path) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        repo.commit(
            "m-1",
            0,
            transition_mutation(repo.load("m-1"), message_id="request-1"),
        )

        first = repo.find_inbox("m-1", "request-1")
        assert first is not None
        first.result["status"] = "CORRUPTED"

        second = repo.find_inbox("m-1", "request-1")
        assert second is not None
        assert second.result == {"status": "RUNNING"}

    def test_mark_outbox_published_is_idempotent_and_preserves_revision(
        self,
        tmp_path: Path,
    ) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())
        committed = repo.commit(
            "m-1",
            0,
            transition_mutation(repo.load("m-1"), message_id="request-1"),
        )
        published_at = datetime(2026, 8, 18, 9, 30, tzinfo=UTC)

        first = repo.mark_outbox_published(
            "m-1",
            "outbox:request-1",
            published_at,
        )
        second = repo.mark_outbox_published(
            "m-1",
            "outbox:request-1",
            datetime(2026, 8, 18, 10, 0, tzinfo=UTC),
        )

        assert first.published_at == published_at
        assert second.published_at == published_at
        recovered = repo.load("m-1")
        assert recovered.mission.revision == committed.mission.revision
        assert recovered.outbox[0].published_at == published_at

    def test_mark_unknown_outbox_message_is_rejected(self, tmp_path: Path) -> None:
        repo = self.make_repo(tmp_path)
        repo.create(runtime_snapshot())

        with pytest.raises(RuntimeDomainError) as raised:
            repo.mark_outbox_published(
                "m-1",
                "missing",
                datetime.now(UTC),
            )

        assert raised.value.code == "OUTBOX_MESSAGE_NOT_FOUND"
