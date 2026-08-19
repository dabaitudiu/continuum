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
        line for line in commands.splitlines() if line.startswith("run deploy ")
    )
    assert "--region=us-east1" in deploy
    assert "GOOGLE_CLOUD_LOCATION=global" in deploy
    assert "CONTINUUM_COMPILER_STORE=firestore" in deploy
    assert "CONTINUUM_FIRESTORE_COMPILER_COLLECTION=compiler_requests" in deploy
    outbox_job = next(
        line for line in commands.splitlines() if line.startswith("run jobs deploy ")
    )
    assert "continuum-outbox-relay" in outbox_job
    assert "app.events.outbox_worker" in outbox_job
    assert "--max-retries=3" in outbox_job
    assert "cloudscheduler.googleapis.com" in commands
    project_grants = [
        line
        for line in commands.splitlines()
        if line.startswith("projects add-iam-policy-binding ")
    ]
    assert all("roles/run.invoker" not in line for line in project_grants)
    job_grant = next(
        line
        for line in commands.splitlines()
        if line.startswith("run jobs add-iam-policy-binding ")
    )
    assert "continuum-outbox-relay" in job_grant
    assert "roles/run.invoker" in job_grant
    assert (
        "serviceAccount:continuum-outbox-scheduler@continuum-test.iam.gserviceaccount.com"
        in job_grant
    )
    scheduler = next(
        line
        for line in commands.splitlines()
        if line.startswith(
            ("scheduler jobs create http ", "scheduler jobs update http ")
        )
    )
    assert "continuum-outbox-relay-schedule" in scheduler
    assert "--schedule=*/2 * * * *" in scheduler
    assert (
        "--uri=https://run.googleapis.com/v2/projects/continuum-test/locations/"
        "us-east1/jobs/continuum-outbox-relay:run"
    ) in scheduler
    assert (
        "--oauth-service-account-email=continuum-outbox-scheduler@continuum-test.iam.gserviceaccount.com"
        in scheduler
    )


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)
