# 08 — Side-Effect Ledger

## Problem

A retryable agent runtime can accidentally duplicate real-world actions.

Example:

1. Procurement Agent calls `activate_vendor`.
2. Simulator commits vendor status `ACTIVE`.
3. Worker dies before receiving the response.
4. Runtime retries.

Without an idempotency protocol the vendor could be activated/provisioned twice or two external records could be created.

## Protocol

### Step 1 — ActionIntent

Before invoking a side-effecting tool, persist:

- action type;
- normalized request hash;
- deterministic idempotency key;
- target resource;
- status `INTENDED`.

### Step 2 — Execute

Mark `EXECUTING`, call tool with idempotency key where supported.

### Step 3 — Commit

Persist external reference and mark `COMMITTED`.

### Retry behavior

- `COMMITTED`: return previous result; never execute again.
- `INTENDED` with no external evidence: retry may proceed.
- `EXECUTING/UNKNOWN`: reconcile with simulator/external system before retry.
- `FAILED`: retry according to policy.

## MVP actions

At minimum implement two:

1. `send_vendor_email` — idempotent.
2. `activate_vendor` — idempotent and blocks if upstream authorization is stale.

## Safety rule

No decision in `STALE`, `INVALID`, or `REVALIDATING` may authorize an irreversible external action.
