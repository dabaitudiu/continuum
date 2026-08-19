#!/usr/bin/env bash
set -euo pipefail

CONTINUUM_PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-}}"
CONTINUUM_REGION="${2:-${CONTINUUM_CLOUD_REGION:-us-east1}}"
CONTINUUM_VERTEX_LOCATION="${CONTINUUM_VERTEX_LOCATION:-global}"
CONTINUUM_SERVICE="${CONTINUUM_CLOUD_RUN_SERVICE:-continuum}"
CONTINUUM_DATABASE="${CONTINUUM_FIRESTORE_DATABASE:-continuum}"
CONTINUUM_TOPIC="${CONTINUUM_PUBSUB_TOPIC:-continuum-events}"
CONTINUUM_SERVICE_ACCOUNT_ID="${CONTINUUM_SERVICE_ACCOUNT_ID:-continuum-runtime}"
CONTINUUM_SERVICE_ACCOUNT="${CONTINUUM_SERVICE_ACCOUNT_ID}@${CONTINUUM_PROJECT_ID}.iam.gserviceaccount.com"

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

CONTINUUM_SERVICE_URL="$(gcloud run services describe "${CONTINUUM_SERVICE}" \
  --region="${CONTINUUM_REGION}" \
  --project="${CONTINUUM_PROJECT_ID}" \
  --format='value(status.url)')"

echo "${CONTINUUM_SERVICE_URL}"
curl --fail --silent --show-error "${CONTINUUM_SERVICE_URL}/api/health"
echo
