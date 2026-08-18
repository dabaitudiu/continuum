from typing import Any

from app.domain.models import DecisionStatus
from app.runtime.entities import RuntimeSnapshot


class MissionToolbox:
    """Read-only mission tools. Runtime mutations are deliberately absent."""

    def __init__(self, snapshot: RuntimeSnapshot) -> None:
        if snapshot.world is None:
            raise ValueError("agent tools require an enterprise simulator world")
        self._snapshot = snapshot.model_copy(deep=True)

    def get_vendor_profile(self) -> dict[str, Any]:
        """Return the current vendor profile and data classification."""
        world = self._snapshot.world
        assert world is not None
        return world.vendor.model_dump(mode="json")

    def list_vendor_documents(self) -> list[dict[str, Any]]:
        """List current vendor document artifacts with stable identifiers."""
        world = self._snapshot.world
        assert world is not None
        return [
            world.artifacts[document_id].model_dump(mode="json")
            for document_id in world.documents
        ]

    def get_security_policy(self) -> dict[str, Any]:
        """Return the current immutable security policy artifact."""
        world = self._snapshot.world
        assert world is not None
        return world.artifacts[world.current_policy_id].model_dump(mode="json")

    def get_document(self, document_id: str) -> dict[str, Any]:
        """Return one document by the stable identifier supplied in task context."""
        world = self._snapshot.world
        assert world is not None
        artifact = world.artifacts.get(document_id)
        if artifact is None or document_id not in world.documents:
            return {"error": "DOCUMENT_NOT_FOUND", "document_id": document_id}
        return {
            **artifact.model_dump(mode="json"),
            "document_type": artifact.metadata.get("document_type"),
        }

    def get_vendor_data_classification(self) -> dict[str, Any]:
        """Return whether the current vendor handles customer PII."""
        world = self._snapshot.world
        assert world is not None
        return {
            "vendor_id": world.vendor.vendor_id,
            "handles_customer_pii": world.vendor.handles_customer_pii,
        }

    def get_valid_decisions(self) -> list[dict[str, Any]]:
        """Return only currently VALID canonical decisions."""
        return [
            decision.model_dump(mode="json")
            for decision in self._snapshot.graph.decisions.values()
            if decision.status is DecisionStatus.VALID
        ]
