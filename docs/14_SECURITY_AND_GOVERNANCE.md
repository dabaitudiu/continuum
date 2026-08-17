# 14 — Security and Governance

## Threat model

Protect against:

- agent invoking unauthorized tool;
- tool output containing prompt injection;
- untrusted vendor documents attempting instruction hijack;
- PII leakage into logs;
- replayed side-effect calls;
- stale authorization being reused after role/policy change;
- one agent impersonating another.

## Agent identity

Preferred P1 design:

- distinct identity/principal per deployed agent where platform support/time allows;
- minimal scopes;
- runtime stores identity snapshot/version on decisions and tool calls.

If full Agent Identity setup is too risky for the hackathon environment, emulate permissions in the simulator/runtime and clearly label the difference; do not pretend it is zero-trust production enforcement.

## Agent Gateway

Use Agent Gateway if reliably available to govern tool/agent traffic and demonstrate fleet-level policy enforcement.

Core MVP must not fail if Gateway provisioning is unavailable. Keep a runtime Tool Gateway abstraction so integration is replaceable.

## Model Armor

Use where available to screen untrusted prompts/responses/tool payloads. Particularly valuable for vendor-supplied document text or MCP/tool responses.

Do not claim Model Armor protects intermediate paths it is not configured to inspect. Demonstrate only verified integration behavior.

## Agent Registry

Register deployed agents and expose name/version/capabilities in a Fleet page or architecture evidence.

## Secrets

- Use Secret Manager/environment-backed credentials.
- Never put API keys in repo or UI.
- Use service account auth to Google Cloud services.

## PII

Demo data is synthetic. Avoid storing raw document contents in logs. Store hashes/IDs and small safe summaries in domain records.

## Authorization drift

Identity/permission snapshot can be modeled as a versioned `WorldArtifact`. A permission change can invalidate decisions/actions that depend on that authorization context.
