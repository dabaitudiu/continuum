from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.repository.runtime_memory import InMemoryRuntimeRepository


def test_production_static_bundle_serves_spa_without_shadowing_api(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text("<h1>Continuum Mission Control</h1>")
    client = TestClient(
        create_app(
            runtime_repository=InMemoryRuntimeRepository(),
            static_dir=tmp_path,
        )
    )

    assert client.get("/").text == "<h1>Continuum Mission Control</h1>"
    assert client.get("/missions/demo-route").text == "<h1>Continuum Mission Control</h1>"
    assert client.get("/api/health").json()["status"] == "ok"
