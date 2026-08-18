import os

from google.adk.agents import Agent

from app.agents.contracts import (
    ProcurementProposal,
    SecurityProposal,
    VendorProposal,
)
from app.agents.tools import MissionToolbox


DEFAULT_MODEL = "gemini-3.6-flash"


def build_agent_fleet(
    toolbox: MissionToolbox,
    *,
    model: str | None = None,
) -> dict[str, Agent]:
    resolved_model = model or os.environ.get("CONTINUUM_GEMINI_MODEL", DEFAULT_MODEL)
    return {
        "vendor-agent": Agent(
            name="vendor_agent",
            description="Validates vendor intake and current document completeness.",
            model=resolved_model,
            instruction=(
                "Inspect the vendor profile and document list using tools. Return only "
                "the structured proposal. Never approve security or activate a vendor."
            ),
            tools=[toolbox.get_vendor_profile, toolbox.list_vendor_documents],
            output_schema=VendorProposal,
            mode="single_turn",
        ),
        "security-agent": Agent(
            name="security_agent",
            description="Interprets current policy and proposes a security decision.",
            model=resolved_model,
            instruction=(
                "Read current policy, vendor data classification, and only documents "
                "whose IDs are supplied. Cite every governing artifact/evidence ID in "
                "dependency_refs. Under v13, an AI vendor handling customer PII needs "
                "PEN_TEST evidence. If absent return MISSING_EVIDENCE with "
                "missing_document_type=PEN_TEST. Never mutate runtime state."
            ),
            tools=[
                toolbox.get_security_policy,
                toolbox.get_document,
                toolbox.get_vendor_data_classification,
            ],
            output_schema=SecurityProposal,
            mode="single_turn",
        ),
        "procurement-agent": Agent(
            name="procurement_agent",
            description="Combines current valid decisions and proposes activation.",
            model=resolved_model,
            instruction=(
                "Use only VALID canonical decisions returned by the tool. Cite their "
                "IDs in dependency_refs. Propose ACTIVATE_VENDOR only when current "
                "security and financial approvals exist. Never perform the side effect."
            ),
            tools=[toolbox.get_valid_decisions],
            output_schema=ProcurementProposal,
            mode="single_turn",
        ),
    }
