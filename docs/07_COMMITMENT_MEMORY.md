# 07 — Commitment Memory

## Thesis

Long-term memory is not only facts and preferences. A long-running agent must remember **obligations that remain open across time**.

## Example

After Policy v13 invalidates security approval, the Security Agent concludes that a penetration-test report is missing.

It creates:

```text
Commitment:
  owner: security-agent
  trigger: vendor.document.uploaded
  predicate: vendor_id == ACME && document_type == PEN_TEST
  resume: SECURITY_REVALIDATION
```

The worker exits. The commitment persists.

Seven simulated days later the document arrives. The event satisfies the commitment and wakes the correct mission.

## Requirements

- Structured trigger type.
- Deterministic predicate over event metadata.
- Human-readable description for UI.
- Owner agent.
- Resume work definition.
- Deadline/expiry optional for MVP.
- Exactly-once satisfaction.

## Relationship to Google Memory Bank

Use Memory Bank for semantic long-term memory such as stable vendor facts or user/operator preferences if useful.

Do **not** store open commitments only as generated memories. Commitments are execution obligations and therefore belong in canonical Continuum state.

## UI

Commitment card should show:

- what is awaited;
- who owes it;
- what event will satisfy it;
- what will resume;
- how long it has been open.
