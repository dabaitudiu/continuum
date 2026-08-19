# 24 — Google Cloud Deployment

## What this deploys

- one public Cloud Run service containing Mission Control and the control-plane API;
- a named Firestore Native-mode database used as the Mission and compiler system of record (`missions` and `compiler_requests` collections);
- one Pub/Sub topic receiving durable outbox events;
- one independent Cloud Run Job that scans and retries pending outbox projections;
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
CONTINUUM_VERTEX_LOCATION=global \
./scripts/deploy-google-cloud.sh YOUR_PROJECT_ID us-east1
```

The positional region controls Cloud Run and Firestore placement. Gemini uses the separate `CONTINUUM_VERTEX_LOCATION`, which defaults to the Vertex AI `global` endpoint recommended by Google's current Gemini quickstart. Keeping these values separate prevents an invalid Cloud Run region when the model endpoint is `global`.

The script is idempotent for existing APIs, service account, Firestore database, Pub/Sub topic, service, and outbox relay job. It prints the deployed URL and then calls `/api/health`. A healthy cloud response must report:

```json
{
  "status": "ok",
  "runtime": "continuum",
  "agent_mode": "google_adk",
  "runtime_store": "firestore",
  "compiler_store": "firestore",
  "event_transport": "pubsub",
  "telemetry_exporter": "google_cloud_trace"
}
```

Run the complete release gate three times against the deployed URL:

```bash
CONTINUUM_EXPECT_CLOUD=1 ./scripts/verify-deployment.sh CLOUD_RUN_URL 3
```

Each run verifies v12 baseline, v13 drift, D42/D50 invalidation, D43 preservation, the durable pen-test wait, selective revalidation, D57/D58 supersession, exactly one committed activation side effect, and final `Vendor ACTIVE / Mission COMPLETED` state. The health gate also refuses a deployment where the compiler silently fell back from Firestore.

The deployment script sets:

```text
CONTINUUM_RUNTIME_STORE=firestore
CONTINUUM_COMPILER_STORE=firestore
CONTINUUM_FIRESTORE_COLLECTION=missions
CONTINUUM_FIRESTORE_COMPILER_COLLECTION=compiler_requests
```

The whole generic `/api/compiler` surface is disabled unless a separate `CONTINUUM_COMPILER_API_CAPABILITY` is injected for an internal service caller. Runtime acceptance additionally requires `CONTINUUM_RUNTIME_COMPILER_CAPABILITY`. Do not put either capability in a public frontend environment variable. Compiler Lab uses its isolated, server-registered reference-fixture routes and does not broaden either production capability.

The public reference runner validates a bounded request identity and applies a per-instance sliding-window rate limit before creating an aggregate. For internet-scale deployment, place the service behind Cloud Armor/API Gateway for a shared cross-instance quota; the in-process guard is the prototype safety boundary, not a distributed quota service.

The deployed `${CONTINUUM_CLOUD_RUN_SERVICE}-outbox-relay` job runs `app.events.outbox_worker`. It scans durable Firestore outboxes, republishes unpublished messages, and exits nonzero when any mission remains failed so Cloud Run retries the task. Trigger it periodically with your deployment scheduler; it is intentionally independent of command replay. A manual operational check is:

```bash
gcloud run jobs execute continuum-outbox-relay \
  --region=us-east1 \
  --project=YOUR_PROJECT_ID \
  --wait
```

## Verification boundary

Local tests use contract fakes for Firestore (including compiler aggregate/outbox persistence) and Pub/Sub and a real production container. They prove adapter semantics and packaging, but not IAM, regional availability, quota, live Gemini behavior, or Cloud Trace delivery. Those claims require running the deployment in an authenticated project and recording three stable end-to-end missions plus the authenticated compiler evidence lane.

The relevant current Google references are the official [Cloud Run deploy command](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy), [Firestore database management](https://cloud.google.com/firestore/docs/manage-databases), [Pub/Sub CLI quickstart](https://docs.cloud.google.com/pubsub/docs/publish-receive-messages-gcloud), and [Vertex AI Gemini quickstart](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart).
