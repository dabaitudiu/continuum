from __future__ import annotations

import json
from copy import deepcopy
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.compiler.context import CompilationContext
from app.sources.identity import FragmentType, SourceRef, TrustClass
from app.sources.registry import ResolvedSource, SourceRegistryError


class SourceToolError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class _ToolValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceCatalogEntry(_ToolValue):
    source_ref: str
    artifact_id: str
    logical_key: str
    revision_label: str
    logical_path: str
    source_type: str
    trust_class: str
    authority_rank: int
    world_snapshot_id: str
    summary: str


class SourceFragmentView(_ToolValue):
    source_ref: str
    artifact_id: str
    revision_label: str
    logical_path: str
    source_type: str
    trust_class: str
    authority_rank: int
    fragment_hash: str
    content: Any
    content_is_untrusted: bool


class StructuredFieldView(_ToolValue):
    source_ref: str
    logical_path: str
    value: Any


class CurrentRevisionView(_ToolValue):
    artifact_id: str
    revision_id: str
    revision_label: str
    representation_id: str
    source_refs: list[str] = Field(default_factory=list)


class ReadOnlySourceTools:
    """Bounded, request-scoped source reads for model reasoning."""

    def __init__(self, context: CompilationContext) -> None:
        self._context = context

    @property
    def context(self) -> CompilationContext:
        return self._context

    def search_source_catalog(
        self,
        query: str,
        *,
        source_types: set[str] | None = None,
        limit: int = 20,
    ) -> list[SourceCatalogEntry]:
        if not query.strip() or query != query.strip() or len(query) > 500:
            raise SourceToolError(
                "SOURCE_TOOL_QUERY_INVALID",
                "catalog query must be 1-500 trimmed characters",
            )
        if limit < 1 or limit > 50:
            raise SourceToolError(
                "SOURCE_TOOL_LIMIT_INVALID",
                "catalog limit must be between 1 and 50",
            )
        query_folded = query.casefold()
        results: list[SourceCatalogEntry] = []
        for source in self._catalog():
            if source_types and source.artifact.source_type.value not in source_types:
                continue
            haystack = " ".join(
                (
                    source.artifact.artifact_id,
                    source.artifact.logical_key,
                    source.fragment.logical_path,
                    source.fragment.heading or "",
                    _content_text(source.content),
                )
            ).casefold()
            if query_folded not in haystack:
                continue
            results.append(
                SourceCatalogEntry(
                    source_ref=str(source.ref),
                    artifact_id=source.artifact.artifact_id,
                    logical_key=source.artifact.logical_key,
                    revision_label=source.revision.revision_label,
                    logical_path=source.fragment.logical_path,
                    source_type=source.artifact.source_type.value,
                    trust_class=source.artifact.trust_class.value,
                    authority_rank=source.artifact.authority_rank,
                    world_snapshot_id=source.world_snapshot_id,
                    summary=_content_text(source.content)[:240],
                )
            )
        return sorted(results, key=lambda entry: entry.source_ref)[:limit]

    def get_fragment(self, fragment_ref: str) -> SourceFragmentView:
        source = self._resolve_allowed(fragment_ref)
        if source.content is None:
            raise SourceToolError(
                "SOURCE_TOOL_CONTENT_UNAVAILABLE",
                f"fragment content is unavailable: {fragment_ref}",
            )
        return SourceFragmentView(
            source_ref=str(source.ref),
            artifact_id=source.artifact.artifact_id,
            revision_label=source.revision.revision_label,
            logical_path=source.fragment.logical_path,
            source_type=source.artifact.source_type.value,
            trust_class=source.artifact.trust_class.value,
            authority_rank=source.artifact.authority_rank,
            fragment_hash=source.fragment.text_hash,
            content=deepcopy(source.content),
            content_is_untrusted=(
                source.artifact.trust_class is TrustClass.UNTRUSTED
            ),
        )

    def get_structured_field(self, fragment_ref: str) -> StructuredFieldView:
        source = self._resolve_allowed(fragment_ref)
        if source.fragment.fragment_type not in {
            FragmentType.FIELD,
            FragmentType.ROW,
            FragmentType.TOOL_FIELD,
        }:
            raise SourceToolError(
                "SOURCE_TOOL_NOT_STRUCTURED",
                f"fragment is not a structured field: {fragment_ref}",
            )
        if source.content is None:
            raise SourceToolError(
                "SOURCE_TOOL_CONTENT_UNAVAILABLE",
                f"fragment content is unavailable: {fragment_ref}",
            )
        return StructuredFieldView(
            source_ref=str(source.ref),
            logical_path=source.fragment.logical_path,
            value=deepcopy(source.content),
        )

    def list_current_revisions(
        self,
        artifact_ids: list[str],
    ) -> list[CurrentRevisionView]:
        requested = set(artifact_ids)
        grouped: dict[str, list[ResolvedSource]] = {}
        for source in self._catalog():
            if source.artifact.artifact_id not in requested:
                continue
            grouped.setdefault(source.artifact.artifact_id, []).append(source)
        return [
            CurrentRevisionView(
                artifact_id=artifact_id,
                revision_id=sources[0].revision.revision_id,
                revision_label=sources[0].revision.revision_label,
                representation_id=sources[0].representation.representation_id,
                source_refs=sorted(str(source.ref) for source in sources),
            )
            for artifact_id, sources in sorted(grouped.items())
        ]

    def get_decision_context(self) -> dict[str, Any]:
        return deepcopy(dict(self._context.decision_context or {}))

    def list_source_inventory(self) -> list[SourceFragmentView]:
        return [
            self.get_fragment(str(source.ref))
            for source in self._catalog()
        ]

    def model_tool_functions(self) -> tuple[Callable[..., Any], ...]:
        toolbox = self

        def search_source_catalog(query: str) -> list[dict[str, Any]]:
            """Search allowed source fragments and return stable opaque refs."""
            return [
                entry.model_dump(mode="json")
                for entry in toolbox.search_source_catalog(query)
            ]

        def get_fragment(fragment_ref: str) -> dict[str, Any]:
            """Read one allowed source fragment by an exact tool-returned ref."""
            return toolbox.get_fragment(fragment_ref).model_dump(mode="json")

        def get_structured_field(fragment_ref: str) -> dict[str, Any]:
            """Read the typed value of one allowed structured source field."""
            return toolbox.get_structured_field(fragment_ref).model_dump(mode="json")

        def list_current_revisions(
            artifact_ids: list[str],
        ) -> list[dict[str, Any]]:
            """List current snapshot revisions for allowed artifact IDs."""
            return [
                revision.model_dump(mode="json")
                for revision in toolbox.list_current_revisions(artifact_ids)
            ]

        def get_decision_context() -> dict[str, Any]:
            """Read the bounded mission and decision request context."""
            return toolbox.get_decision_context()

        return (
            search_source_catalog,
            get_fragment,
            get_structured_field,
            list_current_revisions,
            get_decision_context,
        )

    def _catalog(self) -> list[ResolvedSource]:
        catalog: list[ResolvedSource] = []
        for raw_ref in sorted(self._context.allowed_source_refs):
            try:
                catalog.append(
                    self._context.source_registry.resolve(
                        SourceRef.parse(raw_ref),
                        self._context.world_snapshot_id,
                        request_scope=self._context.owner_scope,
                        allow_historical=self._context.allow_historical,
                    )
                )
            except (SourceRegistryError, ValueError) as error:
                if isinstance(error, SourceRegistryError):
                    raise SourceToolError(error.code, error.message) from error
                raise SourceToolError(
                    "SOURCE_TOOL_REF_INVALID",
                    f"invalid source ref: {raw_ref}",
                ) from error
        return catalog

    def _resolve_allowed(self, raw_ref: str) -> ResolvedSource:
        if raw_ref not in self._context.allowed_source_refs:
            raise SourceToolError(
                "SOURCE_TOOL_REF_NOT_ALLOWED",
                f"source ref is outside the request allowlist: {raw_ref}",
            )
        try:
            ref = SourceRef.parse(raw_ref)
            return self._context.source_registry.resolve(
                ref,
                self._context.world_snapshot_id,
                request_scope=self._context.owner_scope,
                allow_historical=self._context.allow_historical,
            )
        except (SourceRegistryError, ValueError) as error:
            if isinstance(error, SourceRegistryError):
                raise SourceToolError(error.code, error.message) from error
            raise SourceToolError(
                "SOURCE_TOOL_REF_INVALID",
                f"invalid source ref: {raw_ref}",
            ) from error


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
