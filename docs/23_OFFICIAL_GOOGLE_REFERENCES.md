# 23 — Official Google References

These are the authoritative implementation references to re-check while building because Google Agent Platform APIs and launch stages can change.

## Gemini Enterprise Agent Runtime

https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime

Use for current Agent Runtime capabilities, Sessions, Memory Bank, Code Execution, observability, and governance integration.

## Deploy ADK agent to Agent Runtime

https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/deploy-an-agent

## Use an ADK agent / async long-running query jobs

https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/use-an-adk-agent

Current documentation describes asynchronous long-running query jobs; do not equate a single job lifetime with Continuum mission lifetime. Continuum mission continuity is persisted in its own domain state and can span multiple invocations/events.

## Memory Bank with ADK

https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank/adk-quickstart

Use Memory Bank for semantic long-term memory; retain deterministic execution obligations in Continuum's explicit store.

## Agent Gateway

https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/gateways/agent-gateway-overview

## Model Armor + Agent Gateway

https://docs.cloud.google.com/model-armor/model-armor-agent-gateway-integration

## Agent governance / Registry / policies

https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern

## Agent observability

https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability

ADK emits telemetry aligned with OpenTelemetry GenAI semantics; use this for cloud-native proof and debugging.

## agents-cli / ADK workflow

https://google.github.io/agents-cli/cli/

Useful for current scaffolding/deployment conventions. Verify CLI flags against current docs at build time rather than pinning this specification to a possibly changing command line.
