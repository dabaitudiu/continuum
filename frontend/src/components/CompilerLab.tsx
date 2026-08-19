import {
  AlertTriangle,
  ArrowRight,
  Check,
  CircleHelp,
  FileCheck2,
  LockKeyhole,
  RotateCcw,
  ShieldAlert,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import type {
  CompilerEvidenceDto,
  CompilerLabStatusDto,
  CompilerLabViewDto,
  ContinuumApi,
  ProviderEvidenceDto,
  ReferenceScenarioDto,
} from '../types'

function requestId(): string {
  const suffix = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`
  return `compiler-lab-${suffix}`
}

function money(value: string | undefined): string {
  const parsed = Number(value ?? '0')
  return Number.isFinite(parsed) ? parsed.toFixed(2) : '0.00'
}

function statusLabel(evidence: ProviderEvidenceDto): string {
  if (evidence.status === 'PASS') return 'PASSING EVIDENCE'
  if (!evidence.credentials_configured) {
    return evidence.provider === 'OPENAI' ? 'KEY NOT CONFIGURED' : 'CREDENTIALS NOT CONFIGURED'
  }
  return evidence.status
}

export function CompilerLab({ api }: { api: ContinuumApi }) {
  const [status, setStatus] = useState<CompilerLabStatusDto | null>(null)
  const [scenarioId, setScenarioId] = useState('authorized-access')
  const [view, setView] = useState<CompilerLabViewDto | null>(null)
  const [busy, setBusy] = useState<'status' | 'run' | 'accept' | null>('status')
  const [error, setError] = useState<string | null>(null)
  const [retryIntent, setRetryIntent] = useState<'status' | 'run' | 'accept' | null>(null)

  const loadStatus = async () => {
    setBusy('status')
    setError(null)
    setRetryIntent(null)
    try {
      if (!api.getCompilerLabStatus) throw new Error('Compiler Lab API is unavailable')
      const next = await api.getCompilerLabStatus()
      setStatus(next)
      if (!next.scenarios.some((scenario) => scenario.scenario_id === scenarioId)) {
        setScenarioId(next.scenarios[0]?.scenario_id ?? '')
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load compiler evidence')
      setRetryIntent('status')
    } finally {
      setBusy(null)
    }
  }

  useEffect(() => {
    void loadStatus()
    // The API object is stable at the application boundary. Re-fetching because a
    // parent recreated a test double would create duplicate compilation controls.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const run = async () => {
    if (!api.runCompilerScenario || !scenarioId || busy) return
    setBusy('run')
    setError(null)
    setRetryIntent(null)
    try {
      setView(await api.runCompilerScenario(scenarioId, requestId()))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Reference compilation failed')
      setRetryIntent('run')
    } finally {
      setBusy(null)
    }
  }

  const accept = async () => {
    const compilerRequestId = view?.aggregate.request.request_id
    if (!api.acceptCompilerScenario || !compilerRequestId || busy) return
    setBusy('accept')
    setError(null)
    setRetryIntent(null)
    try {
      setView(await api.acceptCompilerScenario(compilerRequestId))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Runtime acceptance failed')
      setRetryIntent('accept')
    } finally {
      setBusy(null)
    }
  }

  const scenarios = status?.scenarios ?? []
  const selectedScenario = scenarios.find((scenario) => scenario.scenario_id === scenarioId)
  const evidence = view?.evidence ?? status?.evidence
  const result = view?.aggregate.result
  const accepted = result?.status === 'ACCEPTED'
  const retry = () => {
    if (retryIntent === 'status') void loadStatus()
    if (retryIntent === 'run') void run()
    if (retryIntent === 'accept') void accept()
  }

  return (
    <section className="compiler-lab" aria-label="Semantic Dependency Compiler Lab" aria-busy={busy !== null}>
      <header className="compiler-lab__heading">
        <div>
          <p className="eyebrow">SEMANTIC DEPENDENCY COMPILER / MODULE 01</p>
          <h1>Compile model judgment into runtime-safe state.</h1>
          <p className="compiler-lab__description">Inspect exact source fragments, canonical claims, blocking findings, and the immutable acceptance boundary.</p>
          <p className="compiler-execution-mode">Execution mode: {view?.execution_mode ?? status?.execution_mode ?? 'DETERMINISTIC_REFERENCE'}</p>
        </div>
        <div className="compiler-lab__evidence" aria-label="Model evidence status">
          {evidence ? <EvidenceStrip evidence={evidence} /> : <span className="compiler-loading">Loading evidence register…</span>}
        </div>
      </header>

      {error ? (
        <div className="compiler-error" role="alert">
          <AlertTriangle aria-hidden="true" />
          <span>{error}</span>
          <button type="button" onClick={retry} disabled={busy !== null || retryIntent === null}>
            <RotateCcw aria-hidden="true" /> Retry
          </button>
        </div>
      ) : null}

      <div className="compiler-stage-ruler" aria-label="Compilation stages">
        <Stage number="01" label="REQUESTED" owner="COMPILER" state={view ? 'done' : 'active'} />
        <Stage number="02" label="DRAFT_RECEIVED" owner="MODEL PROPOSAL" state={view ? 'done' : 'waiting'} />
        <Stage number="03" label="VALIDATED" owner="COMPILER" state={result ? 'done' : 'waiting'} />
        <Stage number="04" label="REVIEWED" owner="MODEL PROPOSAL" state={result ? 'done' : 'waiting'} />
        <Stage number="05" label="COMPILED" owner="COMPILER" state={result ? 'done' : 'waiting'} />
        <Stage number="06" label="RUNTIME_ACCEPTED" owner="RUNTIME" state={view?.runtime_receipt ? 'done' : accepted ? 'active' : 'waiting'} />
      </div>

      <div className="compiler-scenario-bar">
        <div className="compiler-scenario-selector" aria-label="Reference scenarios">
          {scenarios.map((scenario) => (
            <ScenarioButton
              key={scenario.scenario_id}
              scenario={scenario}
              selected={scenario.scenario_id === scenarioId}
              onSelect={() => {
                setScenarioId(scenario.scenario_id)
                setView(null)
                setError(null)
                setRetryIntent(null)
              }}
            />
          ))}
        </div>
        <div className="compiler-scenario-command">
          <div>
            <span>EXPECTED GATE</span>
            <strong>{selectedScenario?.expected_disposition ?? '—'}</strong>
          </div>
          <button type="button" onClick={run} disabled={!status || busy !== null || !scenarioId}>
            <span>{busy === 'run' ? 'Compiling reference…' : 'Run reference compilation'}</span>
            <ArrowRight aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="compiler-workspace">
        <SourceRegister view={view} />
        <ProvenanceDraft view={view} scenario={selectedScenario} />
        <VerificationLedger view={view} busy={busy} onAccept={accept} />
      </div>
    </section>
  )
}

function EvidenceStrip({ evidence }: { evidence: CompilerEvidenceDto }) {
  const openaiBudget = evidence.openai.budget
  return (
    <>
      <EvidenceCell label="DETERMINISTIC REFERENCE" evidence={evidence.deterministic_reference} />
      <EvidenceCell label="OPENAI EVIDENCE" evidence={evidence.openai} />
      <EvidenceCell label="GEMINI EVIDENCE" evidence={evidence.gemini} />
      <div className="evidence-cell evidence-cell--budget">
        <span>OPENAI BUDGET GUARD</span>
        <strong>${money(openaiBudget?.spent_usd)} / ${money(openaiBudget?.limit_usd)} CUMULATIVE CAP</strong>
        <small>${money(openaiBudget?.remaining_usd)} REMAINING · {openaiBudget?.settled_calls ?? 0} SETTLED</small>
      </div>
    </>
  )
}

function EvidenceCell({ label, evidence }: { label: string; evidence: ProviderEvidenceDto }) {
  return (
    <div className={`evidence-cell evidence-${evidence.status.toLowerCase()}`} title={evidence.reason ?? undefined}>
      <span>{label}</span>
      <strong>{evidence.status}</strong>
      <small><b>{statusLabel(evidence)}</b> · {evidence.model}</small>
    </div>
  )
}

function Stage({ number, label, owner, state }: { number: string; label: string; owner: string; state: 'active' | 'done' | 'waiting' }) {
  return (
    <div className={`compiler-stage stage-${state}`}>
      <span>{number}</span><strong>{label}</strong><small>{owner}</small><i />
    </div>
  )
}

function ScenarioButton({ scenario, selected, onSelect }: { scenario: ReferenceScenarioDto; selected: boolean; onSelect(): void }) {
  return (
    <button
      type="button"
      className={selected ? 'is-selected' : ''}
      aria-pressed={selected}
      aria-label={scenario.label}
      onClick={onSelect}
    >
      <span>{scenario.label}</span>
      <small>{scenario.summary}</small>
    </button>
  )
}

function PanelHeader({ index, title, detail }: { index: string; title: string; detail: string }) {
  return (
    <header className="compiler-panel-header">
      <span>{index}</span>
      <div><strong>{title}</strong><small>{detail}</small></div>
    </header>
  )
}

function SourceRegister({ view }: { view: CompilerLabViewDto | null }) {
  return (
    <section className="source-register" aria-label="Exact source register">
      <PanelHeader index="A" title="SOURCE REGISTER" detail="Exact immutable fragments" />
      {view ? (
        <div className="source-register__rows">
          {view.sources.map((source) => (
            <article className={`source-entry ${source.historical ? 'is-historical' : ''}`} key={source.source_ref}>
              <div className="source-entry__top">
                <span>{source.artifact_type}</span>
                <em>{source.historical ? 'HISTORICAL' : 'CURRENT'}</em>
              </div>
              <strong>{source.logical_key}</strong>
              <code>{source.source_ref}</code>
              <blockquote>{typeof source.content === 'string' ? source.content : JSON.stringify(source.content)}</blockquote>
              <dl>
                <div><dt>AUTHORITY</dt><dd>{source.authority_rank}</dd></div>
                <div><dt>REVISION</dt><dd>{source.revision_label}</dd></div>
                <div><dt>FRAGMENT HASH</dt><dd><code>{source.fragment_hash.slice(0, 16)}…</code></dd></div>
              </dl>
            </article>
          ))}
        </div>
      ) : <PanelEmpty icon={<LockKeyhole />} title="No source set loaded" body="Run a reference compilation to bind an exact, bounded source set." />}
    </section>
  )
}

function ProvenanceDraft({ view, scenario }: { view: CompilerLabViewDto | null; scenario?: ReferenceScenarioDto }) {
  const result = view?.aggregate.result
  const draft = view?.aggregate.draft
  const claims = result?.canonical_claims.length ? result.canonical_claims : draft?.claims ?? []
  const draftByLocalId = useMemo(
    () => new Map(draft?.claims.map((claim) => [claim.claim_local_id, claim]) ?? []),
    [draft?.claims],
  )
  return (
    <section className="provenance-draft" aria-label="Provenance draft">
      <PanelHeader index="B" title="PROVENANCE DRAFT" detail="Claim graph before runtime mutation" />
      {view && draft ? (
        <>
          <div className="compiler-request-strip">
            <span>REQUEST</span><code>{view.aggregate.request.request_id}</code>
            <span>WORLD</span><code>{view.aggregate.request.world_snapshot_id}</code>
          </div>
          <div className="claim-spine">
            {claims.map((claim, index) => {
              const claimLocalId = claim.claim_local_id
              const source = draftByLocalId.get(claimLocalId)
              return (
                <article className="claim-entry" key={claimLocalId}>
                  <div className="claim-spine__marker"><span>{String(index + 1).padStart(2, '0')}</span><i /></div>
                  <div className="claim-entry__body">
                    <div><span>{claim.claim_type}</span><em>{claim.materiality}</em></div>
                    <code>{'claim_id' in claim ? claim.claim_id : claimLocalId}</code>
                    <h3>{claim.statement}</h3>
                    {source?.dependencies.map((dependency) => (
                      <div className="claim-anchor" key={`${claimLocalId}:${dependency.source_ref}`}>
                        <span>{dependency.relation}</span>
                        <code>{dependency.source_ref}</code>
                      </div>
                    ))}
                  </div>
                </article>
              )
            })}
          </div>
          <div className="decision-candidate">
            <span>DECISION CANDIDATE</span>
            {result?.decision_candidate ? (
              <><strong>{result.decision_candidate.outcome}</strong><code>{result.decision_candidate.decision_id}</code></>
            ) : (
              <><strong>WITHHELD</strong><small>Blocking gate prevents a runtime decision.</small></>
            )}
          </div>
        </>
      ) : <PanelEmpty icon={<CircleHelp />} title={scenario?.label ?? 'Select a reference case'} body={scenario?.summary ?? 'The canonical claim graph will appear here.'} />}
    </section>
  )
}

function VerificationLedger({ view, busy, onAccept }: { view: CompilerLabViewDto | null; busy: string | null; onAccept(): void }) {
  const result = view?.aggregate.result
  const findings = [...(result?.validation_findings ?? []), ...(result?.critic_findings ?? [])]
  const contradictions = result?.contradictions ?? []
  const canAccept = result?.status === 'ACCEPTED' && !view?.runtime_receipt
  const blockerCount = result?.status === 'ACCEPTED'
    ? findings.filter((finding) => finding.blocking).length
    : findings.filter((finding) => finding.severity === 'CRITICAL' || finding.blocking).length
      + contradictions.filter((item) => item.severity === 'CRITICAL' && item.resolution === 'UNRESOLVED').length
  return (
    <aside className="verification-ledger" aria-label="Verification ledger">
      <PanelHeader index="C" title="VERIFICATION LEDGER" detail="Deterministic acceptance gate" />
      {result ? (
        <>
          <div className={`compiler-disposition disposition-${result.status.toLowerCase()}`}>
            {result.status === 'ACCEPTED' ? <Check aria-hidden="true" /> : <ShieldAlert aria-hidden="true" />}
            <div><span>COMPILATION DISPOSITION</span><strong>Compilation disposition: {result.status}</strong></div>
          </div>
          <dl className="verification-facts">
            <div><dt>COMPILER</dt><dd>{result.compiler_version}</dd></div>
            <div><dt>POLICY</dt><dd>{result.validation_policy_version}</dd></div>
            <div><dt>CLAIMS</dt><dd>{result.canonical_claims.length}</dd></div>
            <div><dt>BLOCKERS</dt><dd>{blockerCount}</dd></div>
          </dl>
          <section className="ledger-section">
            <h3>FINDINGS</h3>
            {findings.length === 0 && contradictions.length === 0 ? <p className="ledger-pass"><FileCheck2 /> No blocking findings</p> : null}
            {findings.map((finding) => (
              <article key={finding.finding_id}>
                <span>{finding.severity}</span>
                <strong>{finding.finding_type ?? finding.code ?? 'VALIDATION FINDING'}</strong>
                <p>{finding.message}</p>
                {finding.candidate_ref ? <code>{finding.candidate_ref}</code> : null}
              </article>
            ))}
            {contradictions.map((finding) => (
              <article key={finding.finding_id}>
                <span>{finding.severity}</span>
                <strong>CONTRADICTION · {finding.resolution}</strong>
                <p>{finding.claim_or_topic}</p>
                <code>{finding.source_ref_a}</code><code>{finding.source_ref_b}</code>
              </article>
            ))}
          </section>
          <section className="compilation-hash">
            <span>IMMUTABLE COMPILATION HASH</span>
            <code>{result.compilation_hash ?? 'WITHHELD — COMPILATION NOT ACCEPTABLE'}</code>
          </section>
          {canAccept ? (
            <button className="runtime-commit" type="button" onClick={onAccept} disabled={busy !== null}>
              <LockKeyhole aria-hidden="true" />
              <span>{busy === 'accept' ? 'Committing exactly once…' : 'Commit accepted compilation to Runtime'}</span>
            </button>
          ) : null}
          {view?.runtime_receipt ? <RuntimeReceipt view={view} /> : (
            <div className="runtime-boundary-empty">
              <span>RUNTIME BOUNDARY</span>
              <p>{result.status === 'ACCEPTED' ? 'Accepted, but no runtime state has changed.' : 'No runtime mutation is available for this disposition.'}</p>
            </div>
          )}
        </>
      ) : <PanelEmpty icon={<FileCheck2 />} title="Gate awaiting compilation" body="No claims, edges, decisions, or side effects have entered Runtime." />}
    </aside>
  )
}

function RuntimeReceipt({ view }: { view: CompilerLabViewDto }) {
  const receipt = view.runtime_receipt
  if (!receipt) return null
  return (
    <section className="runtime-receipt" aria-label="Runtime acceptance receipt">
      <div><Check aria-hidden="true" /><strong>RUNTIME ACCEPTED</strong><span>{receipt.duplicate ? 'IDEMPOTENT REPLAY' : 'COMMITTED ONCE'}</span></div>
      <dl>
        <div><dt>DECISION</dt><dd><code>{receipt.decision_id}</code></dd></div>
        <div><dt>MISSION REVISION</dt><dd>{receipt.mission_revision}</dd></div>
        <div><dt>AUDIT EVENT</dt><dd><code>{receipt.audit_event_id}</code></dd></div>
        <div><dt>CLAIMS</dt><dd>{receipt.claim_ids.length}</dd></div>
      </dl>
    </section>
  )
}

function PanelEmpty({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="compiler-panel-empty">
      {icon}<strong>{title}</strong><p>{body}</p>
    </div>
  )
}
