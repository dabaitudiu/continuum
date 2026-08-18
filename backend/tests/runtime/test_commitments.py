import pytest

from app.domain.models import DomainEvent
from app.runtime.commitments import CommitmentService
from app.runtime.entities import Commitment, CommitmentStatus
from app.runtime.errors import RuntimeDomainError


def open_pen_test_commitment() -> Commitment:
    return Commitment(
        commitment_id="commitment:pen-test",
        mission_id="m-1",
        work_item_id="work:security-review",
        event_type="vendor.document.uploaded",
        predicate={"vendor_id": "ACME", "document_type": "PEN_TEST"},
    )


def document_event(
    event_id: str,
    *,
    vendor_id: str = "ACME",
    document_type: str = "PEN_TEST",
) -> DomainEvent:
    return DomainEvent(
        event_id=event_id,
        event_type="vendor.document.uploaded",
        payload={
            "vendor_id": vendor_id,
            "document_type": document_type,
            "document_id": f"document:{event_id}",
        },
    )


def test_only_exact_event_type_and_predicate_match_open_commitment() -> None:
    commitment = open_pen_test_commitment()
    wrong_document = document_event("e-1", document_type="SOC2")
    wrong_vendor = document_event("e-2", vendor_id="OTHER")
    wrong_type = document_event("e-3").model_copy(
        update={"event_type": "vendor.profile.updated"}
    )

    assert not CommitmentService.match(commitment, wrong_document)
    assert not CommitmentService.match(commitment, wrong_vendor)
    assert not CommitmentService.match(commitment, wrong_type)
    assert CommitmentService.match(commitment, document_event("e-4"))


def test_matching_event_satisfies_commitment_without_mutating_original() -> None:
    commitment = open_pen_test_commitment()

    satisfied = CommitmentService.satisfy(commitment, document_event("e-1"))

    assert satisfied.status is CommitmentStatus.SATISFIED
    assert satisfied.satisfied_by_event_id == "e-1"
    assert satisfied.satisfied_at is not None
    assert commitment.status is CommitmentStatus.OPEN
    assert commitment.satisfied_by_event_id is None


def test_nonmatching_event_cannot_satisfy_commitment() -> None:
    with pytest.raises(RuntimeDomainError) as raised:
        CommitmentService.satisfy(
            open_pen_test_commitment(),
            document_event("e-1", document_type="SOC2"),
        )

    assert raised.value.code == "COMMITMENT_EVENT_MISMATCH"


@pytest.mark.parametrize(
    "closed_status",
    [
        CommitmentStatus.SATISFIED,
        CommitmentStatus.EXPIRED,
        CommitmentStatus.CANCELLED,
    ],
)
def test_closed_commitment_cannot_be_satisfied_again(
    closed_status: CommitmentStatus,
) -> None:
    commitment = open_pen_test_commitment().model_copy(
        update={"status": closed_status}
    )

    assert not CommitmentService.match(commitment, document_event("e-1"))
    with pytest.raises(RuntimeDomainError) as raised:
        CommitmentService.satisfy(commitment, document_event("e-1"))

    assert raised.value.code == "INVALID_COMMITMENT_TRANSITION"
