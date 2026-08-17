# 10 — Enterprise Simulator

## Purpose

Provide a complete, controllable business world without requiring real enterprise integrations or customer data.

## Simulator modules

### Vendor Database

Seed vendor `ACME_ANALYTICS` with:

- AI analytics vendor;
- handles customer PII = true;
- status `PENDING`;
- profile revision 7.

### Document Store

Initial:

- SOC2 report `soc2-A31.pdf` metadata/hash.
- no penetration test.

Later event:

- `pen-test-P9.pdf` uploaded.

### Security Policy Store

Policy v12:

- SOC2 sufficient for the demo vendor category.

Policy v13:

- AI vendors handling customer PII additionally require penetration-test evidence.

Policy must be represented as a versioned artifact, not merely a string variable.

### Procurement System

- Approval begins pending.
- A demo button or timed simulator produces `human.approval.received`.
- Vendor activation changes durable simulator state.

### Email Simulator

Stores outbound messages and idempotency keys. UI can show that crash retry did not duplicate email.

## Demo controls

Hidden or clearly labeled "Demo Controls" panel:

- Reset scenario.
- Start mission.
- Approve procurement.
- Inject Policy v13.
- Upload penetration test / simulate 7 days later.
- Kill active worker (optional P1).

## Anti-cheating requirement

Demo controls only change simulator/world inputs. They must not directly set Continuum decision statuses. All status changes must be produced by runtime logic.
