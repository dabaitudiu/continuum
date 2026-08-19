#!/usr/bin/env bash
set -euo pipefail

CONTINUUM_PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-}}"
CONTINUUM_REGION="${2:-${CONTINUUM_CLOUD_REGION:-us-east1}}"
CONTINUUM_VERTEX_LOCATION="${CONTINUUM_VERTEX_LOCATION:-global}"
CONTINUUM_SERVICE="${CONTINUUM_CLOUD_RUN_SERVICE:-continuum}"
CONTINUUM_OUTBOX_JOB="${CONTINUUM_OUTBOX_RELAY_JOB:-${CONTINUUM_SERVICE}-outbox-relay}"
CONTINUUM_OUTBOX_SCHEDULER="${CONTINUUM_OUTBOX_SCHEDULER_JOB:-${CONTINUUM_OUTBOX_JOB}-schedule}"
CONTINUUM_OUTBOX_SCHEDULE="${CONTINUUM_OUTBOX_SCHEDULE:-*/2 * * * *}"
CONTINUUM_DATABASE="${CONTINUUM_FIRESTORE_DATABASE:-continuum}"
CONTINUUM_TOPIC="${CONTINUUM_PUBSUB_TOPIC:-continuum-events}"
CONTINUUM_SERVICE_ACCOUNT_ID="${CONTINUUM_SERVICE_ACCOUNT_ID:-continuum-runtime}"
CONTINUUM_SERVICE_ACCOUNT="${CONTINUUM_SERVICE_ACCOUNT_ID}@${CONTINUUM_PROJECT_ID}.iam.gserviceaccount.com"
CONTINUUM_SCHEDULER_SERVICE_ACCOUNT_ID="${CONTINUUM_SCHEDULER_SERVICE_ACCOUNT_ID:-continuum-outbox-scheduler}"
CONTINUUM_SCHEDULER_SERVICE_ACCOUNT="${CONTINUUM_SCHEDULER_SERVICE_ACCOUNT_ID}@${CONTINUUM_PROJECT_ID}.iam.gserviceaccount.com"

if [[ -z "${CONTINUUM_PROJECT_ID}" ]]; then
  echo "usage: $0 PROJECT_ID [REGION]" >&2
  exit 2
fi
if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is required" >&2
  exit 2
fi
if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1 | grep -q .; then
  echo "no active gcloud account; run gcloud auth login" >&2
  exit 2
fi

gcloud services enable \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudtrace.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  run.googleapis.com \
  --project="${CONTINUUM_PROJECT_ID}"

if ! gcloud iam service-accounts describe "${CONTINUUM_SERVICE_ACCOUNT}" \
  --project="${CONTINUUM_PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${CONTINUUM_SERVICE_ACCOUNT_ID}" \
    --display-name="Continuum runtime" \
    --project="${CONTINUUM_PROJECT_ID}"
fi

if ! gcloud iam service-accounts describe "${CONTINUUM_SCHEDULER_SERVICE_ACCOUNT}" \
  --project="${CONTINUUM_PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${CONTINUUM_SCHEDULER_SERVICE_ACCOUNT_ID}" \
    --display-name="Continuum outbox scheduler" \
    --project="${CONTINUUM_PROJECT_ID}"
fi

for CONTINUUM_ROLE in \
  roles/aiplatform.user \
  roles/cloudtrace.agent \
  roles/datastore.user \
  roles/pubsub.publisher; do
  gcloud projects add-iam-policy-binding "${CONTINUUM_PROJECT_ID}" \
    --member="serviceAccount:${CONTINUUM_SERVICE_ACCOUNT}" \
    --role="${CONTINUUM_ROLE}" \
    --condition=None \
    --quiet >/dev/null
done

if gcloud projects get-iam-policy "${CONTINUUM_PROJECT_ID}" \
  --flatten='bindings[].members' \
  --filter="bindings.role=roles/run.invoker AND bindings.members=serviceAccount:${CONTINUUM_SERVICE_ACCOUNT}" \
  --format='value(bindings.role)' | grep -qx 'roles/run.invoker'; then
  gcloud projects remove-iam-policy-binding "${CONTINUUM_PROJECT_ID}" \
    --member="serviceAccount:${CONTINUUM_SERVICE_ACCOUNT}" \
    --role=roles/run.invoker \
    --condition=None \
    --quiet >/dev/null
fi

if ! gcloud firestore databases describe \
  --database="${CONTINUUM_DATABASE}" \
  --project="${CONTINUUM_PROJECT_ID}" >/dev/null 2>&1; then
  gcloud firestore databases create \
    --database="${CONTINUUM_DATABASE}" \
    --location="${CONTINUUM_REGION}" \
    --type=firestore-native \
    --project="${CONTINUUM_PROJECT_ID}" \
    --quiet
fi

if ! gcloud pubsub topics describe "${CONTINUUM_TOPIC}" \
  --project="${CONTINUUM_PROJECT_ID}" >/dev/null 2>&1; then
  gcloud pubsub topics create "${CONTINUUM_TOPIC}" \
    --project="${CONTINUUM_PROJECT_ID}"
fi

gcloud run deploy "${CONTINUUM_SERVICE}" \
  --source=. \
  --region="${CONTINUUM_REGION}" \
  --project="${CONTINUUM_PROJECT_ID}" \
  --service-account="${CONTINUUM_SERVICE_ACCOUNT}" \
  --allow-unauthenticated \
  --cpu=1 \
  --memory=1Gi \
  --concurrency=20 \
  --max-instances=3 \
  --timeout=300 \
  --set-env-vars="CONTINUUM_AGENT_MODE=google_adk,CONTINUUM_GEMINI_MODEL=gemini-3.6-flash,GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${CONTINUUM_PROJECT_ID},GOOGLE_CLOUD_LOCATION=${CONTINUUM_VERTEX_LOCATION},CONTINUUM_RUNTIME_STORE=firestore,CONTINUUM_COMPILER_STORE=firestore,CONTINUUM_FIRESTORE_DATABASE=${CONTINUUM_DATABASE},CONTINUUM_FIRESTORE_COLLECTION=missions,CONTINUUM_FIRESTORE_COMPILER_COLLECTION=compiler_requests,CONTINUUM_PUBSUB_TOPIC=${CONTINUUM_TOPIC},CONTINUUM_OTEL_EXPORTER=google_cloud_trace,CONTINUUM_ENVIRONMENT=hackathon"

CONTINUUM_DEPLOYED_IMAGE="$(gcloud run services describe "${CONTINUUM_SERVICE}" \
  --region="${CONTINUUM_REGION}" \
  --project="${CONTINUUM_PROJECT_ID}" \
  --format='value(spec.template.spec.containers[0].image)')"

gcloud run jobs deploy "${CONTINUUM_OUTBOX_JOB}" \
  --image="${CONTINUUM_DEPLOYED_IMAGE}" \
  --region="${CONTINUUM_REGION}" \
  --project="${CONTINUUM_PROJECT_ID}" \
  --service-account="${CONTINUUM_SERVICE_ACCOUNT}" \
  --command=/app/backend/.venv/bin/python \
  --args=-m,app.events.outbox_worker \
  --max-retries=3 \
  --task-timeout=300s \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${CONTINUUM_PROJECT_ID},CONTINUUM_FIRESTORE_DATABASE=${CONTINUUM_DATABASE},CONTINUUM_FIRESTORE_COLLECTION=missions,CONTINUUM_PUBSUB_TOPIC=${CONTINUUM_TOPIC},CONTINUUM_OUTBOX_SWEEP_PAGE_SIZE=500"

gcloud run jobs add-iam-policy-binding "${CONTINUUM_OUTBOX_JOB}" \
  --region="${CONTINUUM_REGION}" \
  --project="${CONTINUUM_PROJECT_ID}" \
  --member="serviceAccount:${CONTINUUM_SCHEDULER_SERVICE_ACCOUNT}" \
  --role=roles/run.invoker \
  --quiet

CONTINUUM_OUTBOX_RUN_URI="https://run.googleapis.com/v2/projects/${CONTINUUM_PROJECT_ID}/locations/${CONTINUUM_REGION}/jobs/${CONTINUUM_OUTBOX_JOB}:run"
if gcloud scheduler jobs describe "${CONTINUUM_OUTBOX_SCHEDULER}" \
  --location="${CONTINUUM_REGION}" \
  --project="${CONTINUUM_PROJECT_ID}" >/dev/null 2>&1; then
  CONTINUUM_SCHEDULER_ACTION="update"
else
  CONTINUUM_SCHEDULER_ACTION="create"
fi
gcloud scheduler jobs "${CONTINUUM_SCHEDULER_ACTION}" http \
  "${CONTINUUM_OUTBOX_SCHEDULER}" \
  --location="${CONTINUUM_REGION}" \
  --project="${CONTINUUM_PROJECT_ID}" \
  --schedule="${CONTINUUM_OUTBOX_SCHEDULE}" \
  --time-zone="Etc/UTC" \
  --uri="${CONTINUUM_OUTBOX_RUN_URI}" \
  --http-method=POST \
  --oauth-service-account-email="${CONTINUUM_SCHEDULER_SERVICE_ACCOUNT}" \
  --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
  --max-retry-attempts=5 \
  --quiet

CONTINUUM_SERVICE_URL="$(gcloud run services describe "${CONTINUUM_SERVICE}" \
  --region="${CONTINUUM_REGION}" \
  --project="${CONTINUUM_PROJECT_ID}" \
  --format='value(status.url)')"

echo "${CONTINUUM_SERVICE_URL}"
curl --fail --silent --show-error "${CONTINUUM_SERVICE_URL}/api/health"
echo
echo "outbox relay job: ${CONTINUUM_OUTBOX_JOB}"
echo "outbox relay schedule: ${CONTINUUM_OUTBOX_SCHEDULER} (${CONTINUUM_OUTBOX_SCHEDULE})"
