from __future__ import annotations

import json
import os

from app.events.outbox import (
    GooglePubSubOutboxPublisher,
    OutboxRelay,
    OutboxSweeper,
)
from app.repository.runtime_firestore import FirestoreRuntimeRepository


def main() -> int:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    topic = os.environ.get("CONTINUUM_PUBSUB_TOPIC")
    if not project or not topic:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT and CONTINUUM_PUBSUB_TOPIC are required"
        )
    repository = FirestoreRuntimeRepository.from_environment(
        project=project,
        database=os.environ.get("CONTINUUM_FIRESTORE_DATABASE"),
        collection=os.environ.get("CONTINUUM_FIRESTORE_COLLECTION", "missions"),
    )
    page_size = int(os.environ.get("CONTINUUM_OUTBOX_SWEEP_PAGE_SIZE", "500"))
    repository.ensure_outbox_projection_schema(batch_size=page_size)
    publisher = GooglePubSubOutboxPublisher.from_environment(
        project=project,
        topic=topic,
    )
    result = OutboxSweeper(
        repository,
        OutboxRelay(repository, publisher),
    ).sweep(mission_limit=page_size)
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    return 1 if result.failed_mission_ids else 0


if __name__ == "__main__":
    raise SystemExit(main())
