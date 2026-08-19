#!/usr/bin/env bash
set -euo pipefail

CONTINUUM_BASE_URL="${1:-http://127.0.0.1:8080}"
CONTINUUM_RUN_COUNT="${2:-3}"
CONTINUUM_EXPECT_CLOUD="${CONTINUUM_EXPECT_CLOUD:-0}"
CONTINUUM_BASE_URL="${CONTINUUM_BASE_URL%/}"

if ! command -v curl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  echo "curl and jq are required" >&2
  exit 2
fi
if ! [[ "${CONTINUUM_RUN_COUNT}" =~ ^[1-9][0-9]*$ ]]; then
  echo "run count must be a positive integer" >&2
  exit 2
fi

CONTINUUM_HEALTH=""
for ((CONTINUUM_READY_ATTEMPT = 1; CONTINUUM_READY_ATTEMPT <= 60; CONTINUUM_READY_ATTEMPT++)); do
  if CONTINUUM_HEALTH="$(curl --fail --silent --show-error \
    --connect-timeout 1 \
    --max-time 2 \
    "${CONTINUUM_BASE_URL}/api/health" 2>/dev/null)"; then
    break
  fi
  if [[ "${CONTINUUM_READY_ATTEMPT}" == "60" ]]; then
    echo "service did not become ready within 60 attempts: ${CONTINUUM_BASE_URL}" >&2
    exit 1
  fi
  sleep 1
done
if [[ "${CONTINUUM_EXPECT_CLOUD}" == "1" ]]; then
  jq -e '
    .status == "ok" and
    .agent_mode == "google_adk" and
    .runtime_store == "firestore" and
    .compiler_store == "firestore" and
    .event_transport == "pubsub" and
    .telemetry_exporter == "google_cloud_trace"
  ' <<<"${CONTINUUM_HEALTH}" >/dev/null
fi

CONTINUUM_AGENT_MODE="$(jq -r '.agent_mode' <<<"${CONTINUUM_HEALTH}")"
if [[ "${CONTINUUM_AGENT_MODE}" == "google_adk" ]]; then
  CONTINUUM_EXECUTION_MODE="GOOGLE_ADK_GEMINI"
else
  CONTINUUM_EXECUTION_MODE="LOCAL_DETERMINISTIC"
fi

for ((CONTINUUM_RUN_INDEX = 1; CONTINUUM_RUN_INDEX <= CONTINUUM_RUN_COUNT; CONTINUUM_RUN_INDEX++)); do
  CONTINUUM_RUN_ID="verify-$(date +%s)-$$-${CONTINUUM_RUN_INDEX}"
  CONTINUUM_CREATE_BODY="$(jq -cn --arg request_id "${CONTINUUM_RUN_ID}:create" '{request_id:$request_id}')"
  CONTINUUM_CREATE_RESULT="$(curl --fail --silent --show-error \
    -X POST "${CONTINUUM_BASE_URL}/api/missions/demo" \
    -H 'content-type: application/json' \
    -d "${CONTINUUM_CREATE_BODY}")"
  CONTINUUM_MISSION_ID="$(jq -r '.mission_id' <<<"${CONTINUUM_CREATE_RESULT}")"

  CONTINUUM_START_BODY="$(jq -cn --arg request_id "${CONTINUUM_RUN_ID}:start" '{request_id:$request_id}')"
  curl --fail --silent --show-error \
    -X POST "${CONTINUUM_BASE_URL}/api/missions/${CONTINUUM_MISSION_ID}/start" \
    -H 'content-type: application/json' \
    -d "${CONTINUUM_START_BODY}" >/dev/null

  CONTINUUM_POLICY_BODY="$(jq -cn \
    --arg mission_id "${CONTINUUM_MISSION_ID}" \
    --arg event_id "${CONTINUUM_RUN_ID}:policy-v13" \
    '{mission_id:$mission_id,event_id:$event_id}')"
  curl --fail --silent --show-error \
    -X POST "${CONTINUUM_BASE_URL}/api/demo/policy/upgrade" \
    -H 'content-type: application/json' \
    -d "${CONTINUUM_POLICY_BODY}" >/dev/null

  CONTINUUM_DRIFT="$(curl --fail --silent --show-error \
    "${CONTINUUM_BASE_URL}/api/missions/${CONTINUUM_MISSION_ID}/control")"
  jq -e '
    .mission.status == "REVALIDATING" and
    .current_policy == "v13" and
    ([.graph.nodes[] | select(.id == "D42") | .status] == ["STALE"]) and
    ([.graph.nodes[] | select(.id == "D43") | .status] == ["VALID"]) and
    ([.graph.nodes[] | select(.id == "D50") | .status] == ["STALE"])
  ' <<<"${CONTINUUM_DRIFT}" >/dev/null

  CONTINUUM_REVALIDATE_BODY="$(jq -cn --arg request_id "${CONTINUUM_RUN_ID}:revalidate" '{request_id:$request_id}')"
  curl --fail --silent --show-error \
    -X POST "${CONTINUUM_BASE_URL}/api/missions/${CONTINUUM_MISSION_ID}/revalidate" \
    -H 'content-type: application/json' \
    -d "${CONTINUUM_REVALIDATE_BODY}" >/dev/null

  CONTINUUM_WAITING="$(curl --fail --silent --show-error \
    "${CONTINUUM_BASE_URL}/api/missions/${CONTINUUM_MISSION_ID}/control")"
  jq -e '
    .mission.status == "WAITING" and
    .scenario_phase == "MISSING_EVIDENCE" and
    ([.commitments[] | select(.status == "OPEN") | .event_type] == ["vendor.document.uploaded"])
  ' <<<"${CONTINUUM_WAITING}" >/dev/null

  CONTINUUM_DOCUMENT_BODY="$(jq -cn \
    --arg mission_id "${CONTINUUM_MISSION_ID}" \
    --arg event_id "${CONTINUUM_RUN_ID}:pen-test" \
    '{mission_id:$mission_id,event_id:$event_id}')"
  curl --fail --silent --show-error \
    -X POST "${CONTINUUM_BASE_URL}/api/demo/documents/pen-test" \
    -H 'content-type: application/json' \
    -d "${CONTINUUM_DOCUMENT_BODY}" >/dev/null

  CONTINUUM_FINAL="$(curl --fail --silent --show-error \
    "${CONTINUUM_BASE_URL}/api/missions/${CONTINUUM_MISSION_ID}/control")"
  jq -e --arg execution_mode "${CONTINUUM_EXECUTION_MODE}" '
    .mission.status == "COMPLETED" and
    .scenario_phase == "COMPLETED" and
    .vendor_status == "ACTIVE" and
    .execution_mode == $execution_mode and
    ([.side_effects[] | select(.effect_type == "ACTIVATE_VENDOR" and .status == "COMMITTED")] | length == 1) and
    ([.graph.nodes[] | select(.id == "D43") | .status] == ["VALID"]) and
    ([.graph.nodes[] | select(.id == "D57") | .status] == ["VALID"]) and
    ([.graph.nodes[] | select(.id == "D58") | .status] == ["VALID"])
  ' <<<"${CONTINUUM_FINAL}" >/dev/null

  echo "run ${CONTINUUM_RUN_INDEX}/${CONTINUUM_RUN_COUNT} passed mission=${CONTINUUM_MISSION_ID} mode=${CONTINUUM_EXECUTION_MODE}"
done
