import { Braces, Download, GitBranch, Play, ShieldCheck } from 'lucide-react'
import { useLayoutEffect, useRef, useState } from 'react'
import type { ModelTurn, TraceEvent, WorkflowView } from '../generated/contracts'
import { shortHash, useResource } from '../api'

const eventNames: Record<string, string> = {
  RUN_STARTED: 'Request bound',
  AGENT_DECISION: 'Model decision validated',
  AGENT_REPAIR: 'Schema repair requested',
  PLAN_APPLIED: 'Scan plan applied',
  PLAN_CREATED: 'Scan plan created',
  TOOL_COMPLETED: 'Specialist tool completed',
  AGGREGATE_COMPLETED: 'Receipts aggregated',
  PLAN_DECIDED: 'Scan plan decided',
  SELECTION_COMPLETED: 'Immutable selection completed',
  REVIEW_DECIDED: 'Coverage review',
  REFINEMENT_APPLIED: 'Plan changed after feedback',
  RUN_COMPLETED: 'Verified result returned',
  RUN_FAILED: 'Run failed',
}
const nodes = [
  { id: 'orchestrator', label: 'Orchestrator', x: 115, y: 180, subtitle: 'Public entry & exit' },
  { id: 'price', label: 'Price', x: 337, y: 90, subtitle: 'Price + individual ratios' },
  { id: 'supply', label: 'Supply', x: 337, y: 180, subtitle: 'Counts + coverage' },
  { id: 'region', label: 'Region', x: 337, y: 270, subtitle: 'Conditional comparison' },
  { id: 'reviewer', label: 'Reviewer', x: 730, y: 180, subtitle: 'Stop or refine' },
  { id: 'composer', label: 'Composer', x: 730, y: 300, subtitle: 'Grounded fact selection' },
]

function label(event: TraceEvent): string {
  const decision = event.payload.decision
  if (
    event.event === 'REVIEW_DECIDED' &&
    decision &&
    typeof decision === 'object' &&
    !Array.isArray(decision) &&
    'decision' in decision
  ) {
    return `Coverage review: ${String(decision.decision)}`
  }
  if (event.event === 'AGENT_DECISION' && event.payload.valid === false)
    return 'Invalid decision preserved'
  return eventNames[event.event] ?? event.event.toLowerCase().replaceAll('_', ' ')
}

function AgentMap({
  workflow,
  pickRole,
  selectedRole,
}: {
  workflow: WorkflowView
  pickRole: (role: string) => void
  selectedRole: string
}) {
  const present = new Set(workflow.events.map((event) => event.actor))
  const refined = workflow.refinements > 0
  return (
    <div className="agent-map">
      <svg
        viewBox="0 0 920 438"
        aria-label="Agent topology inside the Orchestrator boundary"
        role="group"
      >
        <defs>
          <marker id="flow-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6" fill="currentColor" />
          </marker>
        </defs>
        <rect className="agent-boundary" x="18" y="18" width="884" height="402" rx="14" />
        <g className="agent-edges" fill="none" markerEnd="url(#flow-arrow)">
          <path d="M140,180 L205,180 L295,90 L320,90" />
          <path d="M140,180 L320,180" />
          <path
            d="M140,180 L205,180 L295,270 L320,270"
            className={present.has('region') ? '' : 'inactive-edge'}
          />
          <path d="M355,90 L410,90 L485,165" />
          <path d="M355,180 L485,180" />
          <path
            d="M355,270 L410,270 L485,195"
            className={present.has('region') ? '' : 'inactive-edge'}
          />
          <path d="M575,180 L710,180" />
          <path d="M730,204 L730,281" />
          <path d="M747,300 L850,300 L850,376 L50,376 L50,215 L92,180" />
          <path
            d="M730,156 L730,62 L210,62 L115,157"
            className={refined ? 'feedback-edge fired' : 'feedback-edge inactive-edge'}
          />
        </g>
        <text
          x="465"
          y="49"
          textAnchor="middle"
          className={refined ? 'map-feedback-label fired' : 'map-feedback-label'}
        >
          {refined
            ? `REFINE · ${workflow.refinements} actual plan change${workflow.refinements === 1 ? '' : 's'}`
            : 'REFINE · conditional feedback'}
        </text>
        <g className="aggregate-node">
          <rect x="481" y="150" width="103" height="60" rx="5" />
          <text x="532" y="176" textAnchor="middle">
            Exact
          </text>
          <text x="532" y="193" textAnchor="middle">
            aggregation
          </text>
        </g>
        {nodes.map((node) => {
          const active = present.has(node.id)
          return (
            <g
              key={node.id}
              className={`agent-node ${active ? 'visited' : 'inactive'} ${selectedRole === node.id ? 'selected' : ''}`}
              role="button"
              tabIndex={0}
              aria-label={`Inspect ${node.label} evidence${active ? '' : ', no role event recorded'}`}
              onClick={() => pickRole(node.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  pickRole(node.id)
                }
              }}
            >
              <rect
                x={node.x - 100}
                y={node.y - 25}
                width="200"
                height="88"
                fill="transparent"
                stroke="none"
                aria-hidden="true"
              />
              <circle cx={node.x} cy={node.y} r={node.id === 'orchestrator' ? 24 : 17} />
              <circle className="node-core" cx={node.x} cy={node.y} r={5} />
              <text x={node.x} y={node.y + 42} textAnchor="middle" className="node-label">
                {node.label}
              </text>
              <text x={node.x} y={node.y + 59} textAnchor="middle" className="node-subtitle">
                {active ? node.subtitle : 'No role event recorded'}
              </text>
            </g>
          )
        })}
        <text x="42" y="412" className="map-boundary-label">
          ORCHESTRATOR BOUNDARY
        </text>
        <text x="880" y="412" textAnchor="end" className="map-boundary-label">
          CHILD RESULTS RETURN TO PARENT
        </text>
      </svg>
      <div className="mobile-agent-route">
        <p>Orchestrator · sole public entry and exit</p>
        <div>
          {nodes.slice(1).map((node) => (
            <button
              type="button"
              key={node.id}
              onClick={() => pickRole(node.id)}
              aria-pressed={selectedRole === node.id}
            >
              <span className={present.has(node.id) ? 'route-dot active' : 'route-dot'} />
              {node.label}
              <small>{present.has(node.id) ? 'Evidence recorded' : 'No role event recorded'}</small>
            </button>
          ))}
        </div>
        <p className={refined ? 'loop-label fired' : 'loop-label'}>
          <GitBranch size={16} />
          {refined
            ? `${workflow.refinements} feedback loop fired: Reviewer → Orchestrator → fresh scans`
            : 'Reviewer may return work to Orchestrator for fresh scans'}
        </p>
      </div>
    </div>
  )
}

export function Workflow({
  baseUrl,
  feedback,
  busy = false,
}: {
  baseUrl: string
  feedback: () => void
  busy?: boolean
}) {
  const resource = useResource<WorkflowView>(baseUrl + '/workflow', 4000)
  const [eventSequence, setEventSequence] = useState<number | null>(null)
  const [iteration, setIteration] = useState('all')
  const [showModel, setShowModel] = useState(false)
  const [turn, setTurn] = useState(0)
  const workflow = resource.data
  const traceList = useRef<HTMLOListElement>(null)
  const selectedButton = useRef<HTMLButtonElement>(null)
  const events = !workflow
    ? []
    : iteration === 'all'
      ? workflow.events
      : workflow.events.filter((event) => event.display_iteration === Number(iteration))
  const selected =
    events.find((event) => event.sequence === eventSequence) ??
    events.find((event) => event.event === 'REVIEW_DECIDED') ??
    events[0]
  useLayoutEffect(() => {
    const list = traceList.current
    const button = selectedButton.current
    if (!list || !button) return
    const bounds = list.getBoundingClientRect()
    const chosen = button.getBoundingClientRect()
    if (chosen.top < bounds.top) list.scrollTop += chosen.top - bounds.top
    else if (chosen.bottom > bounds.bottom) list.scrollTop += chosen.bottom - bounds.bottom
  }, [baseUrl, selected?.sequence, showModel])
  const model = useResource<ModelTurn>(
    showModel && workflow && workflow.model_decisions > 0 ? baseUrl + '/model/' + turn : null,
  )
  if (resource.error)
    return (
      <div className="notice error" role="alert">
        <p>{resource.error}</p>
        <button className="button secondary" onClick={resource.retry}>
          Retry trace
        </button>
      </div>
    )
  if (!workflow || resource.loading)
    return (
      <div className="loading-surface" role="status">
        Loading the recorded agent route…
        <div className="skeleton chart" />
      </div>
    )
  const pickRole = (role: string) => {
    const event = [...workflow.events].reverse().find((item) => item.actor === role)
    if (event) {
      setEventSequence(event.sequence)
      setIteration('all')
    }
  }
  return (
    <div className="wide-content workflow-page">
      <div className="page-heading">
        <div>
          <h1>The agent route</h1>
          <p>One public Orchestrator. Internal specialists. A real way back.</p>
        </div>
        <button className="button secondary" onClick={feedback} disabled={busy}>
          <GitBranch size={17} />
          Open feedback control
        </button>
      </div>
      <div className="analysis-status">
        <span className="status-badge">
          {workflow.mode === 'replay' ? 'Offline replay' : 'Captured live'}
        </span>
        <span>{workflow.model_decisions} model decisions</span>
        <span>
          {workflow.refinements} refinement{workflow.refinements === 1 ? '' : 's'}
        </span>
        <span>{workflow.schema_repairs} repairs</span>
        <span className="status-right">
          <ShieldCheck size={15} />
          {workflow.query_unchanged ? 'Criteria unchanged' : 'Inspect query lineage'}
        </span>
      </div>
      <p className="workflow-identity">
        <code>{workflow.run_id}</code> ·{' '}
        {workflow.evidence_scope === 'auxiliary_index_omission'
          ? 'Auxiliary index-omission control · excluded from headline results'
          : workflow.evidence_scope === 'pilot'
            ? 'Pilot evidence · separate from headline evaluation'
            : workflow.evidence_scope === 'headline'
              ? 'Headline campaign evidence'
              : workflow.evidence_scope === 'development_smoke'
                ? 'Development smoke run'
                : 'Application analysis'}
      </p>
      {workflow.failure && (
        <div className="notice error" role="alert">
          <p>
            <strong>{workflow.failure.code}</strong> · {workflow.failure.message}
            <br />
            <small>
              Stage: {workflow.failure.stage}. The failed attempt remains part of this trace.
            </small>
          </p>
        </div>
      )}
      <AgentMap workflow={workflow} selectedRole={selected?.actor ?? ''} pickRole={pickRole} />
      <p className="map-explanation">
        The parent calls agents as tools. Python binds their validated intents to exact tools;
        aggregation consumes their receipts. Reviewer feedback changes scan strategy and can
        activate Region. Composer returns grounded facts to the Orchestrator.
      </p>
      <section className="trace-section">
        <div className="section-heading">
          <div>
            <h2>Inspect the execution</h2>
            <p>Choose a trace event or open the captured model boundary.</p>
          </div>
          <div className="export-links">
            <button
              type="button"
              className="button quiet"
              aria-pressed={showModel}
              onClick={() => setShowModel(!showModel)}
            >
              <Braces size={16} />
              Model decisions
            </button>
            <a className="button quiet" href={workflow.trace_url}>
              <Download size={16} />
              JSONL trace
            </a>
          </div>
        </div>
        {showModel ? (
          <div className="model-inspector">
            <label className="field inline">
              Decision sequence
              <select value={turn} onChange={(event) => setTurn(Number(event.target.value))}>
                {Array.from({ length: workflow.model_decisions }, (_, index) => (
                  <option value={index} key={index}>
                    {index}
                  </option>
                ))}
              </select>
            </label>
            {model.error && <p className="error-text">{model.error}</p>}
            {model.loading ? (
              <p role="status">Loading exact model boundary…</p>
            ) : (
              model.data && (
                <>
                  <p>
                    <strong>{String(model.data.input.agent)}</strong> · exact prompt, tool schemas
                    and trusted context · response captured before dispatch.
                  </p>
                  <details open>
                    <summary>Actual model response</summary>
                    <pre>{JSON.stringify(model.data.response, null, 2)}</pre>
                  </details>
                  <details>
                    <summary>Verified dispatcher result</summary>
                    <pre>{JSON.stringify(model.data.dispatched, null, 2)}</pre>
                  </details>
                  <details>
                    <summary>Exact input and context budget</summary>
                    <pre>
                      {JSON.stringify(
                        { input: model.data.input, budget: model.data.budget },
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                </>
              )
            )}
          </div>
        ) : (
          <div className="trace-inspector">
            <div className="trace-list">
              <label className="field inline">
                Pass
                <select
                  value={iteration}
                  onChange={(event) => {
                    setIteration(event.target.value)
                    setEventSequence(null)
                  }}
                >
                  <option value="all">All passes</option>
                  {Array.from({ length: workflow.refinements + 1 }, (_, index) => (
                    <option value={index} key={index}>
                      Pass {index + 1}
                    </option>
                  ))}
                </select>
              </label>
              <ol ref={traceList}>
                {events.map((event) => (
                  <li key={event.sequence}>
                    <button
                      type="button"
                      className={event.sequence === selected?.sequence ? 'selected' : ''}
                      aria-pressed={event.sequence === selected?.sequence}
                      ref={event.sequence === selected?.sequence ? selectedButton : null}
                      onClick={() => setEventSequence(event.sequence)}
                    >
                      <span className="event-sequence">{event.sequence}</span>
                      <span>
                        <strong>{label(event)}</strong>
                        <small>
                          {event.actor} · pass {event.display_iteration + 1}
                          {event.iteration_label_basis !== 'recorded' && ' · plan-derived'}
                        </small>
                      </span>
                    </button>
                  </li>
                ))}
              </ol>
            </div>
            {selected ? (
              <div className="trace-detail">
                <h3>{label(selected)}</h3>
                <dl className="trace-facts">
                  <div>
                    <dt>Event type</dt>
                    <dd>
                      <code>{selected.event}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Actor</dt>
                    <dd>{selected.actor}</dd>
                  </div>
                  <div>
                    <dt>Pass</dt>
                    <dd>{selected.display_iteration + 1}</dd>
                  </div>
                  <div>
                    <dt>Query hash</dt>
                    <dd>
                      <code title={selected.query_sha256}>{shortHash(selected.query_sha256)}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Causal parent event</dt>
                    <dd>{selected.parent_event_sequence ?? 'None recorded'}</dd>
                  </div>
                </dl>
                {selected.iteration_label_basis !== 'recorded' && (
                  <p className="trace-iteration-note">
                    Pass {selected.display_iteration + 1} follows the active plan and the preceding
                    invalid decision. The raw trace records pass {selected.iteration + 1}.
                  </p>
                )}
                <h4>Recorded payload</h4>
                <pre>{JSON.stringify(selected.payload, null, 2)}</pre>
                <p className="trace-hash">
                  Payload SHA-256{' '}
                  <code title={selected.payload_sha256}>{shortHash(selected.payload_sha256)}</code>
                </p>
              </div>
            ) : (
              <p>No trace events have been emitted yet.</p>
            )}
          </div>
        )}
      </section>
      <div className="method-note">
        <Play size={18} />
        <p>
          <strong>Replay preserves the decisions, then executes the work.</strong> Exact prompt,
          schema, tool, model, seed and upstream receipt identities must match. A mismatch stops
          playback with REPLAY_MISS.
        </p>
      </div>
    </div>
  )
}
