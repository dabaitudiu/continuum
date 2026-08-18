from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_deploy_separates_resource_region_from_vertex_endpoint(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gcloud_log = tmp_path / "gcloud.log"
    _write_executable(
        bin_dir / "gcloud",
        """#!/bin/sh
printf '%s\\n' "$*" >> "$GCLOUD_LOG"
case "$*" in
  "auth list"*) printf '%s\\n' 'developer@example.com' ;;
  "run services describe"*) printf '%s\\n' 'https://continuum.example.test' ;;
esac
""",
    )
    _write_executable(
        bin_dir / "curl",
        """#!/bin/sh
printf '%s\\n' '{"status":"ok"}'
""",
    )
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "GCLOUD_LOG": str(gcloud_log),
        "CONTINUUM_VERTEX_LOCATION": "global",
    }

    subprocess.run(
        [
            str(REPOSITORY_ROOT / "scripts/deploy-google-cloud.sh"),
            "continuum-test",
            "us-east1",
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    commands = gcloud_log.read_text()
    deploy = next(
        line for line in commands.splitlines()
        if line.startswith("run deploy ")
    )
    assert "--region=us-east1" in deploy
    assert "GOOGLE_CLOUD_LOCATION=global" in deploy


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)
