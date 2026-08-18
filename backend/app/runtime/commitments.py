from app.domain.models import DomainEvent
from app.runtime.entities import Commitment, CommitmentStatus, utc_now
from app.runtime.errors import RuntimeDomainError


class CommitmentService:
    @staticmethod
    def match(commitment: Commitment, event: DomainEvent) -> bool:
        return (
            commitment.status is CommitmentStatus.OPEN
            and commitment.event_type == event.event_type
            and all(
                event.payload.get(key) == value
                for key, value in commitment.predicate.items()
            )
        )

    @staticmethod
    def satisfy(commitment: Commitment, event: DomainEvent) -> Commitment:
        if commitment.status is not CommitmentStatus.OPEN:
            raise RuntimeDomainError(
                "INVALID_COMMITMENT_TRANSITION",
                f"cannot satisfy commitment from {commitment.status}",
            )
        if not CommitmentService.match(commitment, event):
            raise RuntimeDomainError(
                "COMMITMENT_EVENT_MISMATCH",
                "event does not match commitment predicate",
            )
        return commitment.model_copy(
            update={
                "status": CommitmentStatus.SATISFIED,
                "satisfied_by_event_id": event.event_id,
                "satisfied_at": utc_now(),
            },
            deep=True,
        )

    @staticmethod
    def cancel(commitment: Commitment) -> Commitment:
        if commitment.status is not CommitmentStatus.OPEN:
            raise RuntimeDomainError(
                "INVALID_COMMITMENT_TRANSITION",
                f"cannot cancel commitment from {commitment.status}",
            )
        return commitment.model_copy(
            update={"status": CommitmentStatus.CANCELLED},
            deep=True,
        )
