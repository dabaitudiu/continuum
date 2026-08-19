from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import RLock
from typing import Any, Mapping, Protocol

from pydantic import BaseModel, ConfigDict, field_validator

from app.sources.identity import (
    Artifact,
    Fragment,
    ParsedRepresentation,
    Revision,
    SourceRef,
    content_hash,
    derive_representation_id,
    derive_revision_id,
)


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
    current_representations: dict[str, str]
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
    representation: ParsedRepresentation
    fragment: Fragment
    world_snapshot_id: str
    is_historical_revision: bool
    is_historical_representation: bool
    is_historical: bool
    content: Any | None = None


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

    def catalog(
        self,
        scope: str,
        world_snapshot_id: str,
    ) -> list[ResolvedSource]: ...


class InMemorySourceRegistry:
    """Thread-safe local registry with immutable, non-overwriting identities."""

    store_kind = "memory"

    def __init__(self) -> None:
        self._artifacts: dict[str, Artifact] = {}
        self._revisions: dict[str, Revision] = {}
        self._revision_ids_by_label: dict[tuple[str, str], str] = {}
        self._representations: dict[str, ParsedRepresentation] = {}
        self._fragments: dict[tuple[str, str], Fragment] = {}
        self._fragment_values: dict[tuple[str, str], Any] = {}
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

    def add_revision(self, revision: Revision) -> None:
        with self._lock:
            if revision.revision_id != derive_revision_id(
                revision.artifact_id,
                revision.revision_label,
            ):
                raise SourceRegistryError(
                    "REVISION_ID_INVALID",
                    "revision identity is not canonically derived",
                )
            if revision.artifact_id not in self._artifacts:
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
            self._revisions[revision.revision_id] = revision
            self._revision_ids_by_label[label_key] = revision.revision_id

    def add_representation(
        self,
        representation: ParsedRepresentation,
        fragments: tuple[Fragment, ...] | list[Fragment],
        *,
        fragment_values: Mapping[str, Any] | None = None,
    ) -> None:
        with self._lock:
            if representation.representation_id != derive_representation_id(
                representation.revision_id,
                representation.parser_version,
                representation.parser_config_hash,
            ):
                raise SourceRegistryError(
                    "REPRESENTATION_ID_INVALID",
                    "parsed representation identity is not canonically derived",
                )
            revision = self._revisions.get(representation.revision_id)
            if revision is None:
                raise SourceRegistryError(
                    "UNKNOWN_SOURCE_REVISION",
                    f"revision does not exist: {representation.revision_id}",
                )
            if representation.representation_id in self._representations:
                raise SourceRegistryError(
                    "REPRESENTATION_ALREADY_EXISTS",
                    "parsed representation already exists: "
                    f"{representation.representation_id}",
                )
            artifact = self._artifacts[revision.artifact_id]
            fragment_map: dict[tuple[str, str], Fragment] = {}
            for fragment in fragments:
                self._validate_fragment(
                    artifact,
                    revision,
                    representation,
                    fragment,
                )
                key = (representation.representation_id, fragment.logical_path)
                if key in fragment_map:
                    raise SourceRegistryError(
                        "FRAGMENT_ALREADY_EXISTS",
                        f"fragment path is duplicated: {fragment.logical_path}",
                    )
                fragment_map[key] = fragment

            value_map: dict[tuple[str, str], Any] = {}
            for logical_path, value in (fragment_values or {}).items():
                key = (representation.representation_id, logical_path)
                fragment = fragment_map.get(key)
                if fragment is None:
                    raise SourceRegistryError(
                        "FRAGMENT_CONTENT_INVALID",
                        f"content does not identify a fragment: {logical_path}",
                    )
                if content_hash(value) != fragment.text_hash:
                    raise SourceRegistryError(
                        "FRAGMENT_CONTENT_HASH_MISMATCH",
                        f"content hash does not match fragment: {logical_path}",
                    )
                value_map[key] = deepcopy(value)

            self._representations[representation.representation_id] = (
                representation
            )
            self._fragments.update(fragment_map)
            self._fragment_values.update(value_map)

    def add_world_snapshot(self, snapshot: WorldSnapshot) -> None:
        with self._lock:
            if snapshot.world_snapshot_id in self._snapshots:
                raise SourceRegistryError(
                    "WORLD_SNAPSHOT_ALREADY_EXISTS",
                    f"world snapshot already exists: {snapshot.world_snapshot_id}",
                )
            revision_ids = set(snapshot.current_revisions.values())
            if set(snapshot.current_representations) != revision_ids:
                raise SourceRegistryError(
                    "WORLD_SNAPSHOT_INVALID",
                    "every current revision must have exactly one active "
                    "parsed representation",
                )
            for artifact_id, revision_id in snapshot.current_revisions.items():
                artifact = self._artifacts.get(artifact_id)
                revision = self._revisions.get(revision_id)
                representation = self._representations.get(
                    snapshot.current_representations[revision_id]
                )
                if (
                    artifact is None
                    or revision is None
                    or revision.artifact_id != artifact_id
                    or representation is None
                    or representation.revision_id != revision_id
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
            current_revision_id = snapshot.current_revisions.get(ref.artifact_id)
            historical_revision = current_revision_id != revision_id
            if historical_revision and not allow_historical:
                raise SourceRegistryError(
                    "STALE_SOURCE_REFERENCE",
                    f"revision is not current in {world_snapshot_id}: {ref}",
                )

            representation_id = ref.representation_id
            if representation_id is None:
                if historical_revision:
                    raise SourceRegistryError(
                        "UNQUALIFIED_HISTORICAL_REFERENCE",
                        "historical refs must identify a parsed representation",
                    )
                representation_id = snapshot.current_representations.get(
                    revision_id
                )
            representation = self._representations.get(
                representation_id or ""
            )
            if (
                representation is None
                or representation.revision_id != revision_id
            ):
                raise SourceRegistryError(
                    "UNKNOWN_PARSED_REPRESENTATION",
                    f"parsed representation does not exist for revision: {ref}",
                )

            current_representation_id = snapshot.current_representations.get(
                revision_id
            )
            historical_representation = (
                current_representation_id != representation_id
            )
            if historical_representation and not allow_historical:
                raise SourceRegistryError(
                    "STALE_PARSED_REPRESENTATION",
                    "parsed representation is not active in "
                    f"{world_snapshot_id}: {ref}",
                )

            canonical_ref = ref.model_copy(
                update={"representation_id": representation_id},
                deep=True,
            )
            fragment = self._fragments.get(
                (representation_id, ref.logical_path)
            )
            if fragment is None:
                raise SourceRegistryError(
                    "UNKNOWN_SOURCE_FRAGMENT",
                    f"fragment does not exist: {canonical_ref}",
                )
            return ResolvedSource(
                ref=canonical_ref,
                artifact=artifact,
                revision=revision,
                representation=representation,
                fragment=fragment,
                world_snapshot_id=world_snapshot_id,
                is_historical_revision=historical_revision,
                is_historical_representation=historical_representation,
                is_historical=(
                    historical_revision or historical_representation
                ),
                content=deepcopy(
                    self._fragment_values.get(
                        (representation_id, ref.logical_path)
                    )
                ),
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
                representation_id = snapshot.current_representations[revision_id]
                refs.extend(
                    fragment.source_ref()
                    for (candidate_id, _), fragment in self._fragments.items()
                    if candidate_id == representation_id
                )
            return sorted(refs, key=str)

    def catalog(
        self,
        scope: str,
        world_snapshot_id: str,
    ) -> list[ResolvedSource]:
        with self._lock:
            return [
                self.resolve(
                    ref,
                    world_snapshot_id,
                    request_scope=scope,
                )
                for ref in self.allowed_refs(scope, world_snapshot_id)
            ]

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
        representation: ParsedRepresentation,
        fragment: Fragment,
    ) -> None:
        if fragment.representation_id != representation.representation_id:
            raise SourceRegistryError(
                "FRAGMENT_REPRESENTATION_MISMATCH",
                f"fragment belongs to another representation: {fragment.fragment_id}",
            )
        try:
            ref = fragment.source_ref()
        except ValueError as error:
            raise SourceRegistryError(
                "FRAGMENT_REFERENCE_INVALID",
                f"fragment id is not canonical: {fragment.fragment_id}",
            ) from error
        if (
            ref.artifact_id != artifact.artifact_id
            or ref.revision_label != revision.revision_label
            or ref.representation_id != representation.representation_id
        ):
            raise SourceRegistryError(
                "FRAGMENT_REFERENCE_INVALID",
                f"fragment provenance is inconsistent: {fragment.fragment_id}",
            )
