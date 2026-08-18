from __future__ import annotations

import pytest

from app.main import _default_runtime_repository
from app.repository.runtime_firestore import FirestoreRuntimeRepository
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.repository.runtime_publishing import PublishingRuntimeRepository


def test_firestore_store_requires_explicit_google_cloud_project(monkeypatch) -> None:
    monkeypatch.setenv("CONTINUUM_RUNTIME_STORE", "firestore")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)

    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT"):
        _default_runtime_repository(isolated=False)


def test_firestore_and_pubsub_are_composed_from_environment(monkeypatch) -> None:
    captured: dict[str, object] = {}
    firestore_repository = InMemoryRuntimeRepository()

    def fake_firestore(**options):  # type: ignore[no-untyped-def]
        captured["firestore"] = options
        return firestore_repository

    class FakePublisher:
        @classmethod
        def from_environment(cls, **options):  # type: ignore[no-untyped-def]
            captured["pubsub"] = options
            return object()

    monkeypatch.setenv("CONTINUUM_RUNTIME_STORE", "firestore")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "continuum-demo")
    monkeypatch.setenv("CONTINUUM_FIRESTORE_DATABASE", "continuum")
    monkeypatch.setenv("CONTINUUM_PUBSUB_TOPIC", "continuum-events")
    monkeypatch.setattr(
        FirestoreRuntimeRepository,
        "from_environment",
        fake_firestore,
    )
    monkeypatch.setattr("app.main.GooglePubSubOutboxPublisher", FakePublisher)

    repository = _default_runtime_repository(isolated=False)

    assert isinstance(repository, PublishingRuntimeRepository)
    assert captured == {
        "firestore": {
            "project": "continuum-demo",
            "database": "continuum",
            "collection": "missions",
        },
        "pubsub": {
            "project": "continuum-demo",
            "topic": "continuum-events",
        },
    }


def test_unknown_runtime_store_fails_fast(monkeypatch) -> None:
    monkeypatch.setenv("CONTINUUM_RUNTIME_STORE", "redis")

    with pytest.raises(RuntimeError, match="CONTINUUM_RUNTIME_STORE"):
        _default_runtime_repository(isolated=False)
