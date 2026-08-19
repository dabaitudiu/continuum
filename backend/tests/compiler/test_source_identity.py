from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.sources.identity import (
    Artifact,
    ArtifactType,
    Fragment,
    FragmentType,
    Revision,
    SourceRef,
    SourceType,
    TrustClass,
    content_hash,
    ingest_json_revision,
)


NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)


def artifact() -> Artifact:
    return Artifact(
        artifact_id="record:vendor-profile",
        artifact_type=ArtifactType.RECORD,
        logical_key="vendor-profile",
        owner_scope="tenant:example",
        trust_class=TrustClass.VERIFIED,
        source_type=SourceType.STRUCTURED_RECORD,
        authority_rank=50,
        created_at=NOW,
    )


def revision(label: str = "r7") -> Revision:
    payload = {"handles_customer_pii": True, "region": "eu"}
    return Revision(
        revision_id=f"record:vendor-profile@sha256:{content_hash(payload)}",
        artifact_id="record:vendor-profile",
        revision_label=label,
        content_hash=content_hash(payload),
        created_at=NOW,
        valid_from=NOW,
    )


def test_source_ref_round_trips_without_losing_logical_path() -> None:
    raw = "policy:security-policy@v13#section/7.3"

    parsed = SourceRef.parse(raw)

    assert parsed.artifact_id == "policy:security-policy"
    assert parsed.revision_label == "v13"
    assert parsed.logical_path == "section/7.3"
    assert str(parsed) == raw
    assert SourceRef.parse(str(parsed)) == parsed


@pytest.mark.parametrize(
    "raw",
    [
        "policy:security-policy@v13",
        "policy:security-policy#section/7.3",
        "@v13#section/7.3",
        "policy:security-policy@#section/7.3",
        "policy:security-policy@v13#",
        "policy@@v13#section/7.3",
        "policy@v13#section#7.3",
    ],
)
def test_source_ref_rejects_ambiguous_or_incomplete_values(raw: str) -> None:
    with pytest.raises(ValueError, match="source ref"):
        SourceRef.parse(raw)


def test_revision_and_fragment_models_are_immutable() -> None:
    source_revision = revision()
    fragment = Fragment(
        fragment_id=(
            "record:vendor-profile@r7!representation:r7-json-v1"
            "#$.handles_customer_pii"
        ),
        representation_id="representation:r7-json-v1",
        fragment_type=FragmentType.FIELD,
        logical_path="$.handles_customer_pii",
        text_hash=content_hash(True),
        ordinal=0,
    )

    with pytest.raises(ValidationError):
        source_revision.revision_label = "r8"
    with pytest.raises(ValidationError):
        fragment.logical_path = "$.region"


def test_content_hash_is_canonical_for_mapping_key_order() -> None:
    left = {"region": "eu", "nested": {"enabled": True, "limit": 3}}
    right = {"nested": {"limit": 3, "enabled": True}, "region": "eu"}

    assert content_hash(left) == content_hash(right)
    assert len(content_hash(left)) == 64


def test_json_field_refs_survive_unrelated_field_addition() -> None:
    source_artifact = artifact()
    first = ingest_json_revision(
        source_artifact,
        revision_label="r7",
        value={"handles_customer_pii": True, "region": "eu"},
        created_at=NOW,
        valid_from=NOW,
        parser_version="json-v1",
    )
    second = ingest_json_revision(
        source_artifact,
        revision_label="r8",
        value={
            "handles_customer_pii": True,
            "region": "eu",
            "unrelated_note": "new",
        },
        created_at=NOW,
        valid_from=NOW,
        parser_version="json-v1",
    )

    first_field = first.fragment_at("$.handles_customer_pii")
    second_field = second.fragment_at("$.handles_customer_pii")

    assert first_field.logical_path == second_field.logical_path
    assert first_field.text_hash == second_field.text_hash
    assert first_field.source_ref() == SourceRef(
        artifact_id="record:vendor-profile",
        revision_label="r7",
        representation_id=first.representation.representation_id,
        logical_path="$.handles_customer_pii",
    )
    assert second_field.source_ref() == SourceRef(
        artifact_id="record:vendor-profile",
        revision_label="r8",
        representation_id=second.representation.representation_id,
        logical_path="$.handles_customer_pii",
    )


def test_json_ingestion_is_deterministic_and_includes_nested_fields() -> None:
    source_artifact = artifact()
    value = {
        "contacts": [{"email": "security@example.test"}],
        "risk": {"tier": 2},
    }

    left = ingest_json_revision(
        source_artifact,
        revision_label="r9",
        value=value,
        created_at=NOW,
        valid_from=NOW,
        parser_version="json-v1",
    )
    right = ingest_json_revision(
        source_artifact,
        revision_label="r9",
        value={"risk": {"tier": 2}, "contacts": [{"email": "security@example.test"}]},
        created_at=NOW,
        valid_from=NOW,
        parser_version="json-v1",
    )

    assert left == right
    assert left.fragment_at("$.contacts[0].email").text_hash == content_hash(
        "security@example.test"
    )
    assert left.fragment_at("$.contacts[0].email").ordinal < left.fragment_at(
        "$.risk.tier"
    ).ordinal


def test_same_content_under_distinct_business_labels_has_distinct_revisions() -> None:
    source_artifact = artifact()
    arguments = {
        "artifact": source_artifact,
        "value": {"approved": True},
        "created_at": NOW,
        "valid_from": NOW,
        "parser_version": "json-v1",
    }

    v12 = ingest_json_revision(**arguments, revision_label="v12")
    v13 = ingest_json_revision(**arguments, revision_label="v13")

    assert v12.revision.content_hash == v13.revision.content_hash
    assert v12.revision.revision_id != v13.revision.revision_id


def test_parser_versions_share_revision_and_have_distinct_representations() -> None:
    source_artifact = artifact()
    arguments = {
        "artifact": source_artifact,
        "revision_label": "r10",
        "value": {"approved": True},
        "created_at": NOW,
        "valid_from": NOW,
    }

    first = ingest_json_revision(**arguments, parser_version="json-v1")
    reparsed = ingest_json_revision(**arguments, parser_version="json-v2")

    assert first.revision.content_hash == reparsed.revision.content_hash
    assert first.revision.revision_id == reparsed.revision.revision_id
    assert first.representation.representation_id != (
        reparsed.representation.representation_id
    )


def test_qualified_source_ref_round_trips_representation_identity() -> None:
    ref = SourceRef(
        artifact_id="policy:security-policy",
        revision_label="v13",
        representation_id="sha256:abc123",
        logical_path="section/7.3",
    )

    raw = str(ref)

    assert raw == (
        "policy:security-policy@v13!sha256:abc123#section/7.3"
    )
    assert SourceRef.parse(raw) == ref
