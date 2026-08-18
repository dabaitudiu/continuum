from pathlib import Path

from app.demo.runtime_fixture import seed_runtime_demo
from app.repository.runtime_sqlite import SQLiteRuntimeRepository
from app.runtime.entities import VendorStatus


def test_demo_seeds_versioned_enterprise_world() -> None:
    snapshot = seed_runtime_demo("create-world")

    assert snapshot.world.vendor.vendor_id == "ACME"
    assert snapshot.world.vendor.status is VendorStatus.PENDING
    assert snapshot.world.current_policy_id == "policy-v12"
    assert set(snapshot.world.artifacts) == {
        "policy-v12",
        "vendor-profile-r7",
        "soc2-A31",
    }
    assert snapshot.world.documents == ["soc2-A31"]
    assert "pen-test-P9" not in snapshot.world.artifacts


def test_enterprise_world_survives_sqlite_restart(tmp_path: Path) -> None:
    path = tmp_path / "world.db"
    first = SQLiteRuntimeRepository(path)
    snapshot = seed_runtime_demo("create-world")
    first.create(snapshot)
    first.close()

    second = SQLiteRuntimeRepository(path)
    restored = second.load(snapshot.mission.mission_id)

    assert restored.world == snapshot.world
    second.close()
