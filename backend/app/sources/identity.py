from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping
from urllib.parse import quote, unquote

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REF_COMPONENT_SAFE = ":/.$[]()=,'\"-_"


class ArtifactType(StrEnum):
    POLICY = "POLICY"
    DOCUMENT = "DOCUMENT"
    RECORD = "RECORD"
    TOOL_SNAPSHOT = "TOOL_SNAPSHOT"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"


class SourceType(StrEnum):
    POLICY = "POLICY"
    DOCUMENT = "DOCUMENT"
    STRUCTURED_RECORD = "STRUCTURED_RECORD"
    TOOL_SNAPSHOT = "TOOL_SNAPSHOT"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"


class TrustClass(StrEnum):
    AUTHORITATIVE = "AUTHORITATIVE"
    VERIFIED = "VERIFIED"
    UNTRUSTED = "UNTRUSTED"


class FragmentType(StrEnum):
    SECTION = "SECTION"
    CLAUSE = "CLAUSE"
    FIELD = "FIELD"
    ROW = "ROW"
    TOOL_FIELD = "TOOL_FIELD"
    PAGE_BLOCK = "PAGE_BLOCK"


class SourceRef(BaseModel):
    """A stable, human-readable reference to a revision fragment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: str
    revision_label: str
    representation_id: str | None = None
    logical_path: str

    @field_validator(
        "artifact_id",
        "revision_label",
        "representation_id",
        "logical_path",
    )
    @classmethod
    def _validate_component(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or value != value.strip():
            raise ValueError("source ref component is invalid")
        return value

    @classmethod
    def parse(cls, raw: str) -> SourceRef:
        if "@" not in raw or "#" not in raw:
            raise ValueError(f"invalid source ref: {raw!r}")
        prefix, encoded_path = raw.split("#", 1)
        encoded_artifact, revision_part = prefix.split("@", 1)
        if "!" in revision_part:
            encoded_revision, encoded_representation = revision_part.split("!", 1)
        else:
            encoded_revision = revision_part
            encoded_representation = None
        try:
            ref = cls(
                artifact_id=_decode_ref_component(encoded_artifact),
                revision_label=_decode_ref_component(encoded_revision),
                representation_id=(
                    None
                    if encoded_representation is None
                    else _decode_ref_component(encoded_representation)
                ),
                logical_path=_decode_ref_component(encoded_path),
            )
        except ValueError as error:
            raise ValueError(f"invalid source ref: {raw!r}") from error
        if str(ref) != raw:
            raise ValueError(f"invalid source ref: {raw!r}")
        return ref

    def __str__(self) -> str:
        revision_part = _encode_ref_component(self.revision_label)
        if self.representation_id is not None:
            revision_part += f"!{_encode_ref_component(self.representation_id)}"
        return (
            f"{_encode_ref_component(self.artifact_id)}@{revision_part}"
            f"#{_encode_ref_component(self.logical_path)}"
        )


class Artifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: str
    artifact_type: ArtifactType
    logical_key: str
    owner_scope: str
    trust_class: TrustClass
    source_type: SourceType
    authority_rank: int = Field(ge=0)
    created_at: datetime

    @field_validator("artifact_id", "logical_key", "owner_scope")
    @classmethod
    def _require_nonempty(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("source identity fields must be non-empty")
        return value


class Revision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    revision_id: str
    artifact_id: str
    revision_label: str
    content_hash: str
    created_at: datetime
    valid_from: datetime
    valid_until: datetime | None = None
    source_uri: str | None = None

    @field_validator(
        "revision_id",
        "artifact_id",
        "revision_label",
    )
    @classmethod
    def _require_nonempty(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("revision identity fields must be non-empty")
        return value

    @field_validator("content_hash")
    @classmethod
    def _validate_content_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        return value

    @model_validator(mode="after")
    def _validate_identity_and_interval(self) -> Revision:
        expected_id = derive_revision_id(
            self.artifact_id,
            self.revision_label,
        )
        if self.revision_id != expected_id:
            raise ValueError(
                "revision_id must be derived from artifact_id and revision_label"
            )
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("valid_until cannot precede valid_from")
        return self


class ParsedRepresentation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    representation_id: str
    revision_id: str
    parser_version: str
    parser_config_hash: str
    created_at: datetime

    @field_validator("representation_id", "revision_id", "parser_version")
    @classmethod
    def _require_nonempty(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("parsed representation fields must be non-empty")
        return value

    @field_validator("parser_config_hash")
    @classmethod
    def _validate_parser_config_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("parser_config_hash must be a lowercase SHA-256 digest")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> ParsedRepresentation:
        expected_id = derive_representation_id(
            self.revision_id,
            self.parser_version,
            self.parser_config_hash,
        )
        if self.representation_id != expected_id:
            raise ValueError(
                "representation_id must be derived from revision and parser inputs"
            )
        return self


class Fragment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fragment_id: str
    representation_id: str
    fragment_type: FragmentType
    logical_path: str
    heading: str | None = None
    text_hash: str
    ordinal: int = Field(ge=0)
    parent_fragment_id: str | None = None

    @field_validator("fragment_id", "representation_id", "logical_path")
    @classmethod
    def _require_nonempty(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("fragment identity fields must be non-empty")
        return value

    @field_validator("text_hash")
    @classmethod
    def _validate_text_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("text_hash must be a lowercase SHA-256 digest")
        return value

    def source_ref(self) -> SourceRef:
        ref = SourceRef.parse(self.fragment_id)
        if ref.representation_id != self.representation_id:
            raise ValueError("fragment id does not match parsed representation")
        if ref.logical_path != self.logical_path:
            raise ValueError("fragment id does not match logical path")
        return ref


class IngestedSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    revision: Revision
    representation: ParsedRepresentation
    fragments: tuple[Fragment, ...]

    def fragment_at(self, logical_path: str) -> Fragment:
        for fragment in self.fragments:
            if fragment.logical_path == logical_path:
                return fragment
        raise KeyError(logical_path)


IngestedRevision = IngestedSource


def content_hash(value: Any) -> str:
    """Hash JSON-compatible content using a deterministic canonical encoding."""

    if isinstance(value, bytes):
        encoded = value
    else:
        try:
            canonical = json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("content must be JSON-compatible") from error
        encoded = canonical.encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def derive_revision_id(artifact_id: str, revision_label: str) -> str:
    identity_hash = content_hash(
        {
            "artifact_id": artifact_id,
            "revision_label": revision_label,
        }
    )
    return f"{artifact_id}@revision:{identity_hash}"


def derive_representation_id(
    revision_id: str,
    parser_version: str,
    parser_config_hash: str,
) -> str:
    identity_hash = content_hash(
        {
            "revision_id": revision_id,
            "parser_version": parser_version,
            "parser_config_hash": parser_config_hash,
        }
    )
    return f"{revision_id}@representation:sha256:{identity_hash}"


def ingest_json_revision(
    artifact: Artifact,
    *,
    revision_label: str,
    value: Any,
    created_at: datetime,
    valid_from: datetime,
    parser_version: str,
    array_identity_keys: Mapping[str, str] | None = None,
    valid_until: datetime | None = None,
    source_uri: str | None = None,
) -> IngestedSource:
    """Create immutable identities for leaf fields in a JSON-like value."""

    normalized_array_keys = _normalize_array_identity_keys(array_identity_keys)
    digest = content_hash(value)
    revision = Revision(
        revision_id=derive_revision_id(
            artifact.artifact_id,
            revision_label,
        ),
        artifact_id=artifact.artifact_id,
        revision_label=revision_label,
        content_hash=digest,
        created_at=created_at,
        valid_from=valid_from,
        valid_until=valid_until,
        source_uri=source_uri,
    )
    parser_config_hash = content_hash(
        {"array_identity_keys": normalized_array_keys}
    )
    representation = ParsedRepresentation(
        representation_id=derive_representation_id(
            revision.revision_id,
            parser_version,
            parser_config_hash,
        ),
        revision_id=revision.revision_id,
        parser_version=parser_version,
        parser_config_hash=parser_config_hash,
        created_at=created_at,
    )
    used_array_paths: set[str] = set()
    leaves = sorted(
        _json_leaves(
            value,
            "$",
            normalized_array_keys,
            used_array_paths,
        ),
        key=lambda item: item[0],
    )
    unused_array_paths = set(normalized_array_keys) - used_array_paths
    if unused_array_paths:
        raise ValueError(
            "array identity paths do not identify arrays: "
            f"{sorted(unused_array_paths)}"
        )
    fragments = tuple(
        Fragment(
            fragment_id=str(
                SourceRef(
                    artifact_id=artifact.artifact_id,
                    revision_label=revision_label,
                    representation_id=representation.representation_id,
                    logical_path=logical_path,
                )
            ),
            representation_id=representation.representation_id,
            fragment_type=(
                FragmentType.TOOL_FIELD
                if artifact.artifact_type is ArtifactType.TOOL_SNAPSHOT
                else FragmentType.FIELD
            ),
            logical_path=logical_path,
            text_hash=content_hash(field_value),
            ordinal=ordinal,
        )
        for ordinal, (logical_path, field_value) in enumerate(leaves)
    )
    return IngestedSource(
        revision=revision,
        representation=representation,
        fragments=fragments,
    )


def _encode_ref_component(value: str) -> str:
    return quote(value, safe=_REF_COMPONENT_SAFE, encoding="utf-8", errors="strict")


def _decode_ref_component(value: str) -> str:
    return unquote(value, encoding="utf-8", errors="strict")


def _json_leaves(
    value: Any,
    path: str,
    array_identity_keys: Mapping[str, str],
    used_array_paths: set[str],
) -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        leaves: list[tuple[str, Any]] = []
        for key in sorted(value):
            if not isinstance(key, str) or not key:
                raise ValueError("JSON object keys must be non-empty strings")
            leaves.extend(
                _json_leaves(
                    value[key],
                    _field_path(path, key),
                    array_identity_keys,
                    used_array_paths,
                )
            )
        return leaves
    if isinstance(value, list):
        identity_key = array_identity_keys.get(path)
        if identity_key is None:
            return [(path, value)]
        used_array_paths.add(path)
        leaves = []
        seen_identities: set[str] = set()
        for item in value:
            if not isinstance(item, dict):
                raise ValueError(
                    f"array identity at {path} requires object items"
                )
            if identity_key not in item:
                raise ValueError(
                    f"array identity key {identity_key!r} is missing at {path}"
                )
            identity = item[identity_key]
            if identity is None or isinstance(identity, (dict, list)):
                raise ValueError(
                    f"array identity key {identity_key!r} must be a scalar"
                )
            try:
                encoded_identity = json.dumps(
                    identity,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"array identity key {identity_key!r} must be a JSON scalar"
                ) from error
            identity_token = content_hash(
                {"type": type(identity).__name__, "value": identity}
            )
            if identity_token in seen_identities:
                raise ValueError(
                    f"array identity key {identity_key!r} is duplicated at {path}"
                )
            seen_identities.add(identity_token)
            selector_key = (
                identity_key
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identity_key)
                else json.dumps(identity_key, ensure_ascii=False)
            )
            leaves.extend(
                _json_leaves(
                    item,
                    f"{path}[{selector_key}={encoded_identity}]",
                    array_identity_keys,
                    used_array_paths,
                )
            )
        return leaves
    content_hash(value)
    return [(path, value)]


def _normalize_array_identity_keys(
    value: Mapping[str, str] | None,
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, key in (value or {}).items():
        if (
            not isinstance(path, str)
            or not path
            or path != path.strip()
            or not isinstance(key, str)
            or not key
            or key != key.strip()
        ):
            raise ValueError(
                "array identity paths and keys must be non-empty strings"
            )
        normalized[path] = key
    return dict(sorted(normalized.items()))


def _field_path(parent: str, key: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return f"{parent}.{key}"
    escaped = json.dumps(key, ensure_ascii=False)
    return f"{parent}[{escaped}]"
