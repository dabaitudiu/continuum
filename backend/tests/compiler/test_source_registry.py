from datetime import UTC, datetime, timedelta

import pytest

from app.sources.identity import (
    Artifact,
    ArtifactType,
    IngestedSource,
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


def ingest(
    source_artifact: Artifact,
    label: str,
    value: dict[str, object],
    *,
    parser_version: str = "json-v1",
    valid_from: datetime = NOW,
    valid_until: datetime | None = None,
) -> IngestedSource:
    return ingest_json_revision(
        source_artifact,
        revision_label=label,
        value=value,
        created_at=NOW,
        valid_from=valid_from,
        valid_until=valid_until,
        parser_version=parser_version,
    )


def add_ingested(
    registry: InMemorySourceRegistry,
    ingested: IngestedSource,
) -> None:
    registry.add_revision(ingested.revision)
    registry.add_representation(
        ingested.representation,
        ingested.fragments,
    )


def bind_snapshot(
    registry: InMemorySourceRegistry,
    ingested: IngestedSource,
    snapshot_id: str = "world:release-2",
) -> None:
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id=snapshot_id,
            owner_scope="tenant:alpha",
            current_revisions={
                ingested.revision.artifact_id: ingested.revision.revision_id
            },
            current_representations={
                ingested.revision.revision_id: (
                    ingested.representation.representation_id
                )
            },
            created_at=NOW,
        )
    )


def populated_registry() -> tuple[
    InMemorySourceRegistry,
    IngestedSource,
    IngestedSource,
]:
    registry = InMemorySourceRegistry()
    source_artifact = artifact()
    registry.add_artifact(source_artifact)
    r1 = ingest(source_artifact, "r1", {"approved": False})
    r2 = ingest(source_artifact, "r2", {"approved": True})
    add_ingested(registry, r1)
    add_ingested(registry, r2)
    bind_snapshot(registry, r2)
    return registry, r1, r2


def test_current_qualified_fragment_resolves_in_bound_world_snapshot() -> None:
    registry, _, r2 = populated_registry()
    ref = r2.fragment_at("$.approved").source_ref()

    resolved = registry.resolve(ref, "world:release-2")

    assert resolved.ref == ref
    assert resolved.artifact.owner_scope == "tenant:alpha"
    assert resolved.revision.revision_label == "r2"
    assert resolved.representation == r2.representation
    assert resolved.fragment.logical_path == "$.approved"
    assert resolved.is_historical_revision is False
    assert resolved.is_historical_representation is False
    assert resolved.is_historical is False


def test_unqualified_ref_resolves_through_snapshot_active_representation() -> None:
    registry, _, r2 = populated_registry()
    shorthand = SourceRef(
        artifact_id=r2.revision.artifact_id,
        revision_label="r2",
        logical_path="$.approved",
    )

    resolved = registry.resolve(shorthand, "world:release-2")

    assert resolved.ref.representation_id == r2.representation.representation_id
    assert resolved.fragment.source_ref() == resolved.ref


def test_historical_revision_is_rejected_unless_explicitly_allowed() -> None:
    registry, r1, _ = populated_registry()
    ref = r1.fragment_at("$.approved").source_ref()

    with pytest.raises(SourceRegistryError) as raised:
        registry.resolve(ref, "world:release-2")

    assert raised.value.code == "STALE_SOURCE_REFERENCE"

    resolved = registry.resolve(
        ref,
        "world:release-2",
        allow_historical=True,
    )
    assert resolved.is_historical_revision is True
    assert resolved.is_historical is True


def test_parser_versions_coexist_and_old_provenance_resolves_exactly() -> None:
    registry = InMemorySourceRegistry()
    source_artifact = artifact()
    registry.add_artifact(source_artifact)
    parser_v1 = ingest(
        source_artifact,
        "r1",
        {"approved": True},
        parser_version="json-v1",
    )
    parser_v2 = ingest(
        source_artifact,
        "r1",
        {"approved": True},
        parser_version="json-v2",
    )
    registry.add_revision(parser_v1.revision)
    registry.add_representation(
        parser_v1.representation,
        parser_v1.fragments,
    )
    registry.add_representation(
        parser_v2.representation,
        parser_v2.fragments,
    )
    bind_snapshot(registry, parser_v2)

    current = registry.resolve(
        parser_v2.fragment_at("$.approved").source_ref(),
        "world:release-2",
    )
    assert current.representation.parser_version == "json-v2"

    old_ref = parser_v1.fragment_at("$.approved").source_ref()
    with pytest.raises(SourceRegistryError) as raised:
        registry.resolve(old_ref, "world:release-2")
    assert raised.value.code == "STALE_PARSED_REPRESENTATION"

    historical = registry.resolve(
        old_ref,
        "world:release-2",
        allow_historical=True,
    )
    assert historical.representation.parser_version == "json-v1"
    assert historical.fragment.fragment_id == str(old_ref)
    assert historical.is_historical_representation is True


def test_same_content_business_revisions_coexist() -> None:
    registry = InMemorySourceRegistry()
    source_artifact = artifact()
    registry.add_artifact(source_artifact)
    r1 = ingest(source_artifact, "r1", {"approved": True})
    r2 = ingest(source_artifact, "r2", {"approved": True})

    add_ingested(registry, r1)
    add_ingested(registry, r2)
    bind_snapshot(registry, r2)

    assert r1.revision.content_hash == r2.revision.content_hash
    assert registry.revision_id_for(source_artifact.artifact_id, "r1") != (
        registry.revision_id_for(source_artifact.artifact_id, "r2")
    )


def test_unknown_fragment_is_an_error_not_a_warning() -> None:
    registry, _, r2 = populated_registry()
    ref = SourceRef(
        artifact_id=r2.revision.artifact_id,
        revision_label="r2",
        representation_id=r2.representation.representation_id,
        logical_path="$.invented",
    )

    with pytest.raises(SourceRegistryError) as raised:
        registry.resolve(ref, "world:release-2")

    assert raised.value.code == "UNKNOWN_SOURCE_FRAGMENT"


def test_cross_scope_reference_is_rejected_even_when_source_exists() -> None:
    registry, _, r2 = populated_registry()

    with pytest.raises(SourceRegistryError) as raised:
        registry.resolve(
            r2.fragment_at("$.approved").source_ref(),
            "world:release-2",
            request_scope="tenant:other",
        )

    assert raised.value.code == "UNAUTHORIZED_SOURCE_REFERENCE"


def test_registry_never_overwrites_business_revision_content() -> None:
    registry, _, r2 = populated_registry()
    changed = ingest(artifact(), "r2", {"approved": "changed"})

    with pytest.raises(SourceRegistryError) as raised:
        registry.add_revision(changed.revision)

    assert raised.value.code == "REVISION_ALREADY_EXISTS"
    original = registry.resolve(
        r2.fragment_at("$.approved").source_ref(),
        "world:release-2",
    )
    assert original.revision.content_hash == r2.revision.content_hash


def test_registry_rejects_revision_identity_bypassing_model_validation() -> None:
    registry = InMemorySourceRegistry()
    source_artifact = artifact()
    registry.add_artifact(source_artifact)
    valid = ingest(source_artifact, "r1", {"approved": True})
    forged = valid.revision.model_copy(
        update={"revision_id": "forged-revision"},
        deep=True,
    )

    with pytest.raises(SourceRegistryError) as raised:
        registry.add_revision(forged)

    assert raised.value.code == "REVISION_ID_INVALID"


def test_registry_rejects_representation_identity_bypassing_validation() -> None:
    registry = InMemorySourceRegistry()
    source_artifact = artifact()
    registry.add_artifact(source_artifact)
    valid = ingest(source_artifact, "r1", {"approved": True})
    registry.add_revision(valid.revision)
    forged = valid.representation.model_copy(
        update={"representation_id": "forged-representation"},
        deep=True,
    )

    with pytest.raises(SourceRegistryError) as raised:
        registry.add_representation(forged, ())

    assert raised.value.code == "REPRESENTATION_ID_INVALID"


def test_snapshot_cannot_bind_revision_from_another_artifact() -> None:
    registry, _, r2 = populated_registry()

    with pytest.raises(SourceRegistryError) as raised:
        registry.add_world_snapshot(
            WorldSnapshot(
                world_snapshot_id="world:invalid",
                owner_scope="tenant:alpha",
                current_revisions={"record:other": r2.revision.revision_id},
                current_representations={
                    r2.revision.revision_id: r2.representation.representation_id
                },
                created_at=NOW,
            )
        )

    assert raised.value.code == "WORLD_SNAPSHOT_INVALID"


def test_snapshot_requires_active_representation_for_each_revision() -> None:
    registry = InMemorySourceRegistry()
    source_artifact = artifact()
    registry.add_artifact(source_artifact)
    r1 = ingest(source_artifact, "r1", {"approved": True})
    add_ingested(registry, r1)

    with pytest.raises(SourceRegistryError) as raised:
        registry.add_world_snapshot(
            WorldSnapshot(
                world_snapshot_id="world:missing-parser",
                owner_scope="tenant:alpha",
                current_revisions={
                    source_artifact.artifact_id: r1.revision.revision_id
                },
                current_representations={},
                created_at=NOW,
            )
        )

    assert raised.value.code == "WORLD_SNAPSHOT_INVALID"


def test_snapshot_cannot_bind_revision_outside_validity_interval() -> None:
    registry = InMemorySourceRegistry()
    source_artifact = artifact()
    registry.add_artifact(source_artifact)
    expired = ingest(
        source_artifact,
        "expired",
        {"approved": False},
        valid_from=NOW - timedelta(days=2),
        valid_until=NOW - timedelta(days=1),
    )
    add_ingested(registry, expired)

    with pytest.raises(SourceRegistryError) as raised:
        bind_snapshot(registry, expired, "world:after-expiry")

    assert raised.value.code == "WORLD_SNAPSHOT_INVALID"


def test_allowed_refs_are_active_qualified_scoped_and_sorted() -> None:
    registry, _, r2 = populated_registry()

    refs = registry.allowed_refs("tenant:alpha", "world:release-2")

    assert refs == sorted(refs, key=str)
    assert refs == [r2.fragment_at("$.approved").source_ref()]
    assert refs[0].representation_id == r2.representation.representation_id
    assert registry.allowed_refs("tenant:other", "world:release-2") == []
