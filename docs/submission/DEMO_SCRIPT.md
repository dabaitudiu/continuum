# Four-minute demo script

The spoken script is deliberately in English for the hackathon recording. UI mode labels must remain visible so local and cloud evidence cannot be confused.

| Time | Screen action | Voiceover |
|---|---|---|
| 0:00–0:20 | Open Mission Control on the hosted URL. | “Agents can work for minutes today. Enterprises need them to work for weeks. But the world changes while they wait. Continuum prevents an agent from blindly continuing when the assumptions behind an earlier decision are no longer true.” |
| 0:20–0:38 | Point to the three agent lanes and click **Start mission**. | “This mission onboards Acme Analytics through Vendor, Security, and Procurement agents. Under Security Policy v12, Security decision D42 and financial decision D43 are valid, so Procurement decision D50 can authorize activation.” |
| 0:38–0:55 | Show the WAITING state and activation-window Commitment. | “The mission is durably waiting on an external activation window. It can survive a browser refresh or process restart because the wait is an explicit Commitment—not hidden prompt context.” |
| 0:55–1:20 | Click **Inject Policy v13**. | “Now the world changes. Policy v13 adds a penetration-test requirement for AI vendors handling customer PII. The simulator emits a normal versioned policy event; it does not mutate any Decision directly.” |
| 1:20–1:48 | Show D42/D50 stale, D43 preserved, activation blocked. Open the Decision Graph briefly. | “Continuum traverses provenance. D42 depended on v12, so it becomes stale. D50 inherited that invalidation and activation is blocked. D43 remains valid because no dependency path connects it to the changed policy. This is semantic resume—not restart-all.” |
| 1:48–2:15 | Return to Mission route and click **Run affected branch**. | “Only the affected Security branch is dispatched. Gemini reads the new policy and existing evidence through a bounded ADK agent. The model proposes a typed result; the deterministic runtime validates its references before persisting anything.” |
| 2:15–2:38 | Point to **Pen test required** and `vendor.document.uploaded`. Refresh the browser. | “Security cannot approve yet, so the runtime records an exact Commitment for a penetration-test document. Reloading restores the same Mission and the same open wait.” |
| 2:38–3:00 | Click **Upload pen test · +7 days**. | “We compress seven days into one normal document event. The matching event satisfies the Commitment exactly once and wakes only its linked work.” |
| 3:00–3:22 | Show D57/D58, D43 preserved, vendor ACTIVE. | “Fresh Security decision D57 supersedes D42. Fresh Procurement decision D58 supersedes D50. D43 is reused, and the Side Effect Ledger commits vendor activation exactly once.” |
| 3:22–3:38 | Click **Reset**, open **Mission history**, reopen the completed Mission. | “Reset creates a new namespace without deleting history. Operators can reopen any durable Mission and inspect the exact state that authorized its outcome.” |
| 3:38–3:52 | Show Cloud Run service, Firestore Mission document, and one Cloud Trace. | “The product runs on Google Cloud with ADK and Gemini, Firestore state, Pub/Sub outbox events, and Cloud Trace telemetry.” |
| 3:52–4:00 | Return to completed Mission Control. | “Continuum doesn’t just remember where an agent stopped. It remembers why it was allowed to continue.” |

## Recording guardrails

- Record only after `CONTINUUM_EXPECT_CLOUD=1 ./scripts/verify-deployment.sh CLOUD_RUN_URL 3` passes.
- The utility rail must say `GOOGLE ADK · GEMINI` in the final video.
- Show one D43 `VALID / PRESERVED` view long enough to read.
- Show exactly one committed activation side effect.
- Do not claim Agent Runtime, Registry, Gateway, or Model Armor without live console evidence.
