from __future__ import annotations

from datetime import datetime
from threading import RLock
from typing import Protocol

from pydantic import BaseModel, ConfigDict, field_validator

from app.sources.identity import Artifact, Fragment, Revision, SourceRef


class SourceRegistryError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class WorldSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    world_snapshot_id: str
    owner_scope: str
    current_revisions: dict[str, str]
    created_at: datetime

    @field_validator("world_snapshot_id", "owner_scope")
    @classmethod
    def _require_nonempty(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("world snapshot identity fields must be non-empty")
        return value


class ResolvedSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ref: SourceRef
    artifact: Artifact
    revision: Revision
    fragment: Fragment
    world_snapshot_id: str
    is_historical: bool


class SourceRegistry(Protocol):
    def resolve(
        self,
        ref: SourceRef,
        world_snapshot_id: str,
        *,
        request_scope: str | None = None,
        allow_historical: bool = False,
    ) -> ResolvedSource: ...

    def allowed_refs(
        self,
        scope: str,
        world_snapshot_id: str,
    ) -> list[SourceRef]: ...


class InMemorySourceRegistry:
    """Thread-safe local registry with immutable, non-overwriting identities."""

    store_kind = "memory"

    def __init__(self) -> None:
        self._artifacts: dict[str, Artifact] = {}
        self._revisions: dict[str, Revision] = {}
        self._revision_ids_by_label: dict[tuple[str, str], str] = {}
        self._fragments: dict[tuple[str, str], Fragment] = {}
        self._snapshots: dict[str, WorldSnapshot] = {}
        self._lock = RLock()

    def add_artifact(self, artifact: Artifact) -> None:
        with self._lock:
            if artifact.artifact_id in self._artifacts:
                raise SourceRegistryError(
                    "ARTIFACT_ALREADY_EXISTS",
                    f"artifact already exists: {artifact.artifact_id}",
                )
            self._artifacts[artifact.artifact_id] = artifact

    def add_revision(
        self,
        revision: Revision,
        fragments: tuple[Fragment, ...] | list[Fragment],
    ) -> None:
        with self._lock:
            artifact = self._artifacts.get(revision.artifact_id)
            if artifact is None:
                raise SourceRegistryError(
                    "UNKNOWN_SOURCE_ARTIFACT",
                    f"artifact does not exist: {revision.artifact_id}",
                )
            label_key = (revision.artifact_id, revision.revision_label)
            if (
                revision.revision_id in self._revisions
                or label_key in self._revision_ids_by_label
            ):
                raise SourceRegistryError(
                    "REVISION_ALREADY_EXISTS",
                    "revision identity or label already exists: "
                    f"{revision.artifact_id}@{revision.revision_label}",
                )
            fragment_map: dict[tuple[str, str], Fragment] = {}
            for fragment in fragments:
                self._validate_fragment(artifact, revision, fragment)
                key = (revision.revision_id, fragment.logical_path)
                if key in fragment_map:
                    raise SourceRegistryError(
                        "FRAGMENT_ALREADY_EXISTS",
                        f"fragment path is duplicated: {fragment.logical_path}",
                    )
                fragment_map[key] = fragment

            self._revisions[revision.revision_id] = revision
            self._revision_ids_by_label[label_key] = revision.revision_id
            self._fragments.update(fragment_map)

    def add_world_snapshot(self, snapshot: WorldSnapshot) -> None:
        with self._lock:
            if snapshot.world_snapshot_id in self._snapshots:
                raise SourceRegistryError(
                    "WORLD_SNAPSHOT_ALREADY_EXISTS",
                    f"world snapshot already exists: {snapshot.world_snapshot_id}",
                )
            for artifact_id, revision_id in snapshot.current_revisions.items():
                artifact = self._artifacts.get(artifact_id)
                revision = self._revisions.get(revision_id)
                if (
                    artifact is None
                    or revision is None
                    or revision.artifact_id != artifact_id
                    or artifact.owner_scope != snapshot.owner_scope
                    or snapshot.created_at < revision.valid_from
                    or (
                        revision.valid_until is not None
                        and snapshot.created_at > revision.valid_until
                    )
                ):
                    raise SourceRegistryError(
                        "WORLD_SNAPSHOT_INVALID",
                        f"invalid snapshot binding: {artifact_id} -> {revision_id}",
                    )
            self._snapshots[snapshot.world_snapshot_id] = snapshot.model_copy(
                deep=True
            )

    def revision_id_for(self, artifact_id: str, revision_label: str) -> str:
        with self._lock:
            try:
                return self._revision_ids_by_label[(artifact_id, revision_label)]
            except KeyError as error:
                raise SourceRegistryError(
                    "UNKNOWN_SOURCE_REVISION",
                    f"revision does not exist: {artifact_id}@{revision_label}",
                ) from error

    def resolve(
        self,
        ref: SourceRef,
        world_snapshot_id: str,
        *,
        request_scope: str | None = None,
        allow_historical: bool = False,
    ) -> ResolvedSource:
        with self._lock:
            snapshot = self._require_snapshot(world_snapshot_id)
            artifact = self._artifacts.get(ref.artifact_id)
            if artifact is None:
                raise SourceRegistryError(
                    "UNKNOWN_SOURCE_ARTIFACT",
                    f"artifact does not exist: {ref.artifact_id}",
                )
            effective_scope = request_scope or snapshot.owner_scope
            if (
                effective_scope != snapshot.owner_scope
                or artifact.owner_scope != effective_scope
            ):
                raise SourceRegistryError(
                    "UNAUTHORIZED_SOURCE_REFERENCE",
                    f"source is not allowed in scope: {effective_scope}",
                )
            revision_id = self.revision_id_for(
                ref.artifact_id,
                ref.revision_label,
            )
            revision = self._revisions[revision_id]
            fragment = self._fragments.get((revision_id, ref.logical_path))
            if fragment is None:
                raise SourceRegistryError(
                    "UNKNOWN_SOURCE_FRAGMENT",
                    f"fragment does not exist: {ref}",
                )
            current_revision_id = snapshot.current_revisions.get(ref.artifact_id)
            historical = current_revision_id != revision_id
            if historical and not allow_historical:
                raise SourceRegistryError(
                    "STALE_SOURCE_REFERENCE",
                    f"revision is not current in {world_snapshot_id}: {ref}",
                )
            return ResolvedSource(
                ref=ref,
                artifact=artifact,
                revision=revision,
                fragment=fragment,
                world_snapshot_id=world_snapshot_id,
                is_historical=historical,
            )

    def allowed_refs(
        self,
        scope: str,
        world_snapshot_id: str,
    ) -> list[SourceRef]:
        with self._lock:
            snapshot = self._require_snapshot(world_snapshot_id)
            if snapshot.owner_scope != scope:
                return []
            refs: list[SourceRef] = []
            for artifact_id, revision_id in snapshot.current_revisions.items():
                artifact = self._artifacts[artifact_id]
                if artifact.owner_scope != scope:
                    continue
                revision = self._revisions[revision_id]
                refs.extend(
                    SourceRef(
                        artifact_id=artifact_id,
                        revision_label=revision.revision_label,
                        logical_path=logical_path,
                    )
                    for candidate_revision_id, logical_path in self._fragments
                    if candidate_revision_id == revision_id
                )
            return sorted(refs, key=str)

    def _require_snapshot(self, world_snapshot_id: str) -> WorldSnapshot:
        try:
            return self._snapshots[world_snapshot_id]
        except KeyError as error:
            raise SourceRegistryError(
                "UNKNOWN_WORLD_SNAPSHOT",
                f"world snapshot does not exist: {world_snapshot_id}",
            ) from error

    @staticmethod
    def _validate_fragment(
        artifact: Artifact,
        revision: Revision,
        fragment: Fragment,
    ) -> None:
        if fragment.revision_id != revision.revision_id:
            raise SourceRegistryError(
                "FRAGMENT_REVISION_MISMATCH",
                f"fragment belongs to another revision: {fragment.fragment_id}",
            )
        try:
            ref = fragment.source_ref(revision.revision_label)
        except ValueError as error:
            raise SourceRegistryError(
                "FRAGMENT_REFERENCE_INVALID",
                f"fragment id is not canonical: {fragment.fragment_id}",
            ) from error
        if ref.artifact_id != artifact.artifact_id:
            raise SourceRegistryError(
                "FRAGMENT_REFERENCE_INVALID",
                f"fragment belongs to another artifact: {fragment.fragment_id}",
            )
