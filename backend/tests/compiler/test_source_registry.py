from datetime import UTC, datetime, timedelta

import pytest

from app.sources.identity import (
    Artifact,
    ArtifactType,
    SourceRef,
    SourceType,
    TrustClass,
    ingest_json_revision,
)
from app.sources.registry import (
    InMemorySourceRegistry,
    SourceRegistryError,
    WorldSnapshot,
)


NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)


def artifact(*, scope: str = "tenant:alpha") -> Artifact:
    return Artifact(
        artifact_id="record:release-candidate",
        artifact_type=ArtifactType.RECORD,
        logical_key="release-candidate",
        owner_scope=scope,
        trust_class=TrustClass.AUTHORITATIVE,
        source_type=SourceType.STRUCTURED_RECORD,
        authority_rank=80,
        created_at=NOW,
    )


def add_revision(
    registry: InMemorySourceRegistry,
    source_artifact: Artifact,
    label: str,
    value: dict[str, object],
) -> None:
    ingested = ingest_json_revision(
        source_artifact,
        revision_label=label,
        value=value,
        created_at=NOW,
        valid_from=NOW,
        parser_version="json-v1",
    )
    registry.add_revision(ingested.revision, ingested.fragments)


def populated_registry() -> InMemorySourceRegistry:
    registry = InMemorySourceRegistry()
    source_artifact = artifact()
    registry.add_artifact(source_artifact)
    add_revision(registry, source_artifact, "r1", {"approved": False})
    add_revision(registry, source_artifact, "r2", {"approved": True})
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id="world:release-2",
            owner_scope="tenant:alpha",
            current_revisions={
                "record:release-candidate": registry.revision_id_for(
                    "record:release-candidate", "r2"
                )
            },
            created_at=NOW,
        )
    )
    return registry


def test_current_fragment_resolves_in_bound_world_snapshot() -> None:
    registry = populated_registry()
    ref = SourceRef.parse("record:release-candidate@r2#$.approved")

    resolved = registry.resolve(ref, "world:release-2")

    assert resolved.ref == ref
    assert resolved.artifact.owner_scope == "tenant:alpha"
    assert resolved.revision.revision_label == "r2"
    assert resolved.fragment.logical_path == "$.approved"
    assert resolved.is_historical is False


def test_historical_fragment_is_rejected_unless_explicitly_allowed() -> None:
    registry = populated_registry()
    ref = SourceRef.parse("record:release-candidate@r1#$.approved")

    with pytest.raises(SourceRegistryError) as raised:
        registry.resolve(ref, "world:release-2")

    assert raised.value.code == "STALE_SOURCE_REFERENCE"

    resolved = registry.resolve(
        ref,
        "world:release-2",
        allow_historical=True,
    )
    assert resolved.is_historical is True


def test_unknown_fragment_is_an_error_not_a_warning() -> None:
    registry = populated_registry()

    with pytest.raises(SourceRegistryError) as raised:
        registry.resolve(
            SourceRef.parse("record:release-candidate@r2#$.invented"),
            "world:release-2",
        )

    assert raised.value.code == "UNKNOWN_SOURCE_FRAGMENT"


def test_cross_scope_reference_is_rejected_even_when_source_exists() -> None:
    registry = populated_registry()

    with pytest.raises(SourceRegistryError) as raised:
        registry.resolve(
            SourceRef.parse("record:release-candidate@r2#$.approved"),
            "world:release-2",
            request_scope="tenant:other",
        )

    assert raised.value.code == "UNAUTHORIZED_SOURCE_REFERENCE"


def test_registry_never_overwrites_an_existing_revision() -> None:
    registry = populated_registry()
    source_artifact = artifact()

    with pytest.raises(SourceRegistryError) as raised:
        add_revision(registry, source_artifact, "r2", {"approved": "changed"})

    assert raised.value.code == "REVISION_ALREADY_EXISTS"
    original = registry.resolve(
        SourceRef.parse("record:release-candidate@r2#$.approved"),
        "world:release-2",
    )
    assert original.fragment.text_hash != "changed"


def test_snapshot_cannot_bind_revision_from_another_artifact() -> None:
    registry = populated_registry()

    with pytest.raises(SourceRegistryError) as raised:
        registry.add_world_snapshot(
            WorldSnapshot(
                world_snapshot_id="world:invalid",
                owner_scope="tenant:alpha",
                current_revisions={
                    "record:other": registry.revision_id_for(
                        "record:release-candidate", "r2"
                    )
                },
                created_at=NOW,
            )
        )

    assert raised.value.code == "WORLD_SNAPSHOT_INVALID"


def test_snapshot_cannot_bind_revision_outside_its_validity_interval() -> None:
    registry = InMemorySourceRegistry()
    source_artifact = artifact()
    registry.add_artifact(source_artifact)
    ingested = ingest_json_revision(
        source_artifact,
        revision_label="expired",
        value={"approved": False},
        created_at=NOW,
        valid_from=NOW - timedelta(days=2),
        valid_until=NOW - timedelta(days=1),
        parser_version="json-v1",
    )
    registry.add_revision(ingested.revision, ingested.fragments)

    with pytest.raises(SourceRegistryError) as raised:
        registry.add_world_snapshot(
            WorldSnapshot(
                world_snapshot_id="world:after-expiry",
                owner_scope="tenant:alpha",
                current_revisions={
                    source_artifact.artifact_id: ingested.revision.revision_id
                },
                created_at=NOW,
            )
        )

    assert raised.value.code == "WORLD_SNAPSHOT_INVALID"


def test_allowed_refs_are_current_scoped_and_deterministically_sorted() -> None:
    registry = populated_registry()

    refs = registry.allowed_refs("tenant:alpha", "world:release-2")

    assert refs == sorted(refs, key=str)
    assert refs == [
        SourceRef.parse("record:release-candidate@r2#$.approved")
    ]
    assert registry.allowed_refs("tenant:other", "world:release-2") == []
