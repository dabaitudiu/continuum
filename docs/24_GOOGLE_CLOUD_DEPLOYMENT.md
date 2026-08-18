# 24 — Google Cloud Deployment

## What this deploys

- one public Cloud Run service containing Mission Control and the control-plane API;
- a named Firestore Native-mode database used as the Mission system of record;
- one Pub/Sub topic receiving durable outbox events;
- Google ADK agents using Gemini through Vertex AI;
- FastAPI/OpenTelemetry spans exported to Google Cloud Trace.

The runtime service account receives `roles/datastore.user`, `roles/pubsub.publisher`, `roles/aiplatform.user`, and `roles/cloudtrace.agent`. The deployer still needs permission to enable APIs, create resources, grant those roles, build, and deploy Cloud Run services.

## Prerequisites

1. Install and authenticate the Google Cloud CLI.
2. Select a billing-enabled Google Cloud project.
3. Ensure the project can use Gemini on Vertex AI in the target region.

The application uses Application Default Credentials from the Cloud Run service identity. No API key is embedded in the image or passed as a plain environment variable.

## Deploy

```bash
./scripts/deploy-google-cloud.sh YOUR_PROJECT_ID us-east1
```

Optional resource names can be overridden before invocation:

```bash
CONTINUUM_CLOUD_RUN_SERVICE=continuum \
CONTINUUM_FIRESTORE_DATABASE=continuum \
CONTINUUM_PUBSUB_TOPIC=continuum-events \
./scripts/deploy-google-cloud.sh YOUR_PROJECT_ID us-east1
```

The script is idempotent for existing APIs, service account, Firestore database, and Pub/Sub topic. It prints the deployed URL and then calls `/api/health`. A healthy cloud response must report:

```json
{
  "status": "ok",
  "runtime": "continuum",
  "agent_mode": "google_adk",
  "runtime_store": "firestore",
  "event_transport": "pubsub",
  "telemetry_exporter": "google_cloud_trace"
}
```

## Verification boundary

Local tests use contract fakes for Firestore and Pub/Sub and a real production container. They prove adapter semantics and packaging, but not IAM, regional availability, quota, live Gemini behavior, or Cloud Trace delivery. Those claims require running the deployment in an authenticated project and recording three stable end-to-end missions.

The relevant current Google references are the official [Cloud Run deploy command](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy), [Firestore database management](https://cloud.google.com/firestore/docs/manage-databases), and [Pub/Sub CLI quickstart](https://docs.cloud.google.com/pubsub/docs/publish-receive-messages-gcloud).
