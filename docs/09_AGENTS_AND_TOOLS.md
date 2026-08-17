# 09 — Agents and Tools

## General rule

Use a small, defensible multi-agent topology. Three agents are sufficient to prove specialization and delegation.

## Vendor Agent

### Responsibility

- validate intake completeness;
- understand uploaded vendor documents;
- request missing vendor information;
- maintain vendor-facing commitments.

### Tools

- `get_vendor_profile`
- `list_vendor_documents`
- `request_vendor_document`
- `send_vendor_email`

### Forbidden

- approve security;
- activate vendor;
- modify security policy.

## Security Agent

### Responsibility

- read current security policy;
- examine security evidence;
- produce structured security decision and dependency set;
- request missing evidence during revalidation.

### Tools

- `get_security_policy(version/current)`
- `get_document`
- `get_vendor_data_classification`
- `propose_security_decision`

### Critical structured output

Must emit explicit evidence/dependency refs rather than free-text-only verdict.

## Procurement Agent

### Responsibility

- combine valid upstream decisions;
- obtain/represent procurement approval;
- perform vendor activation when authorized.

### Tools

- `get_valid_decisions`
- `request_human_approval`
- `activate_vendor`

## Orchestration

The control plane decides **when** an agent is runnable. Agents decide **how to reason inside their bounded task**.

Avoid a free-running supervisor loop that can mutate canonical state arbitrarily.

## Gemini usage

Gemini must be materially visible in:

- security policy/document interpretation;
- dependency proposal;
- explanation of why new evidence is needed;
- re-review after policy drift.

The deterministic runtime then validates and persists these proposals.
