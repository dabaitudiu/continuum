from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class AgentOutcome(StrEnum):
    COMPLETE = "COMPLETE"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"


class AgentProposal(BaseModel):
    outcome: AgentOutcome
    dependency_refs: list[str] = Field(default_factory=list)
    explanation: str = Field(min_length=1)


class VendorProposal(AgentProposal):
    missing_document_types: list[str] = Field(default_factory=list)


class SecurityProposal(AgentProposal):
    missing_document_type: str | None = None

    @model_validator(mode="after")
    def require_missing_type(self) -> "SecurityProposal":
        if (
            self.outcome is AgentOutcome.MISSING_EVIDENCE
            and not self.missing_document_type
        ):
            raise ValueError("missing evidence outcome requires a document type")
        return self


class ProcurementProposal(AgentProposal):
    requested_action: str | None = None
