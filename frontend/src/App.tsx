import {
  AlertCircle,
  ArrowRight,
  ChartNoAxesCombined,
  Database,
  FlaskConical,
  Network,
  RefreshCw,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { monthLabel, request, useResource } from './api'
import type { AnalysisRequest, AnalysisView, Bootstrap, Job } from './generated/contracts'
import { CriteriaForm } from './components/CriteriaForm'
import { Explore } from './components/Explore'
import { Experiments } from './components/Experiments'
import { Provenance } from './components/Provenance'
import { Workflow } from './components/Workflow'
import './App.css'

const pages = ['explore', 'workflow', 'experiments', 'provenance'] as const
type Page = (typeof pages)[number]
const navigation = [
  { page: 'explore', title: 'Explore', icon: ChartNoAxesCombined },
  { page: 'workflow', title: 'Workflow', icon: Network },
  { page: 'experiments', title: 'Experiments', icon: FlaskConical },
  { page: 'provenance', title: 'Provenance', icon: Database },
] as const
const pageFromHash = (): Page =>
  pages.find((page) => '#' + page === window.location.hash) ?? 'explore'

function App() {
  const bootstrap = useResource<Bootstrap>('/api/bootstrap')
  const [page, setPage] = useState<Page>(pageFromHash)
  const [draft, setDraft] = useState<AnalysisRequest | null>(null)
  const [baseUrl, setBaseUrl] = useState('/api/analyses/capture/normal')
  const [workflowOverride, setWorkflowOverride] = useState<string | null>(null)
  const [captureId, setCaptureId] = useState('normal')
  const [selectedMonth, setSelectedMonth] = useState('2026-09')
  const [money, setMoney] = useState<'USD' | 'USD_THOUSANDS'>('USD')
  const [area, setArea] = useState<'SQFT' | 'SQM'>('SQFT')
  const [job, setJob] = useState<Job | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submissionError, setSubmissionError] = useState<string | null>(null)
  const pending = job?.state === 'queued' || job?.state === 'running'
  const busy = pending || submitting
  const analysis = useResource<AnalysisView>(baseUrl + `?money=${money}&area=${area}`)
  const receiveJob = useCallback(
    (updated: Job) => {
      if (updated.id !== job?.id) return
      setJob(updated)
      if (updated.state === 'completed') {
        setBaseUrl('/api/analyses/job/' + updated.id)
        setCaptureId('')
        setWorkflowOverride(null)
      }
    },
    [job?.id],
  )
  const jobResource = useResource<Job>(
    job ? '/api/jobs/' + job.id : null,
    pending ? 1500 : 0,
    receiveJob,
  )
  const history = useResource<Job[]>('/api/jobs', 5000)
  useEffect(() => {
    const onHash = () => {
      if (window.location.hash !== '#main-content') setPage(pageFromHash())
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  useEffect(() => {
    document.title = `${page[0]?.toUpperCase()}${page.slice(1)} · Housing Evidence`
  }, [page])
  const navigate = (next: Page) => {
    window.location.hash = next
    setPage(next)
  }
  const chooseCapture = (id: string) => {
    if (busy) return
    const capture = bootstrap.data?.captures.find((item) => item.id === id)
    if (!capture) return
    setCaptureId(id)
    setBaseUrl('/api/analyses/capture/' + id)
    setDraft(capture.request)
    setSelectedMonth(capture.request.window_end)
    setJob(null)
    setSubmissionError(null)
    setWorkflowOverride(null)
  }
  const inspectWorkflow = (url?: string) => {
    setWorkflowOverride(url ?? null)
    navigate('workflow')
  }
  const submit = async (mode: 'live' | 'replay') => {
    const currentDraft = draft ?? bootstrap.data?.default_request
    if (busy || !currentDraft) return
    const capture = bootstrap.data?.captures.find((item) => item.id === captureId)
    const query =
      mode === 'replay' && capture ? capture.request : { ...currentDraft, display: { money, area } }
    for (const [low, high, title] of [
      [query.criteria.bedrooms_min, query.criteria.bedrooms_max, 'Bedrooms'],
      [query.criteria.price_min_cents, query.criteria.price_max_cents, 'Price'],
      [query.criteria.sqft_min, query.criteria.sqft_max, 'Size'],
    ] as const) {
      if (
        (low !== null && !Number.isSafeInteger(low)) ||
        (high !== null && !Number.isSafeInteger(high))
      ) {
        setSubmissionError(`${title} bounds must be valid whole numbers.`)
        return
      }
      if (low !== null && high !== null && low > high) {
        setSubmissionError(`${title}: minimum must be no greater than maximum.`)
        return
      }
    }
    setSubmitting(true)
    setSubmissionError(null)
    try {
      const created = await request<Job>('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request: query,
          mode,
          capture_id: mode === 'replay' ? capture?.id : null,
        }),
      })
      setJob(created)
    } catch (failure) {
      setSubmissionError(
        failure instanceof Error ? failure.message : 'The analysis could not start.',
      )
    } finally {
      setSubmitting(false)
    }
  }
  const view = analysis.data
  const displayedDraft = draft ?? bootstrap.data?.default_request
  const changedDraft =
    view &&
    displayedDraft &&
    JSON.stringify([
      displayedDraft.criteria,
      displayedDraft.window_end,
      displayedDraft.compare_regions,
      displayedDraft.seed,
    ]) !==
      JSON.stringify([
        view.request.criteria,
        view.request.window_end,
        view.request.compare_regions,
        view.request.seed,
      ])
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="app-header">
        <a
          className="brand"
          href="#explore"
          onClick={() => navigate('explore')}
          aria-label="Housing Evidence home"
        >
          <svg width="35" height="35" viewBox="0 0 35 35" aria-hidden="true">
            <path
              d="M5 26 L5 18 L17 6 L29 18 L29 26 L18 26 L18 17"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinejoin="round"
            />
            <circle cx="18" cy="17" r="3.6" fill="white" stroke="currentColor" strokeWidth="2.4" />
          </svg>
          <span>
            Housing <strong>Evidence</strong>
          </span>
        </a>
        <nav aria-label="Primary navigation">
          {navigation.map((item) => (
            <a
              key={item.page}
              href={'#' + item.page}
              aria-current={page === item.page ? 'page' : undefined}
              onClick={() => {
                if (item.page === 'workflow') setWorkflowOverride(null)
                navigate(item.page)
              }}
            >
              <item.icon size={17} strokeWidth={1.8} />
              <span>{item.title}</span>
            </a>
          ))}
        </nav>
        <span className="snapshot-label">
          <span />
          Synthetic · Dallas
        </span>
      </header>
      <main id="main-content" tabIndex={-1}>
        {pending && jobResource.error && (
          <div className="notice error" role="alert">
            <p>Status updates are interrupted: {jobResource.error}</p>
            <button className="button secondary" onClick={jobResource.retry}>
              Retry status
            </button>
          </div>
        )}
        {bootstrap.error ? (
          <div className="wide-content">
            <div className="notice error" role="alert">
              <AlertCircle size={20} />
              <div>
                <h1>The local workspace could not load</h1>
                <p>{bootstrap.error}</p>
                <button className="button secondary" onClick={bootstrap.retry}>
                  <RefreshCw size={15} />
                  Retry connection
                </button>
              </div>
            </div>
          </div>
        ) : !bootstrap.data || !displayedDraft ? (
          <div className="wide-content loading-surface" role="status">
            <h1>Loading the frozen workspace</h1>
            <div className="skeleton title" />
            <div className="skeleton chart" />
          </div>
        ) : (
          <>
            {(busy || job?.state === 'failed' || submissionError) && (
              <div
                className={`job-status ${job?.state === 'failed' || submissionError ? 'failed' : ''}`}
                role={job?.state === 'failed' || submissionError ? 'alert' : 'status'}
              >
                <div>
                  <strong>
                    {submissionError
                      ? 'Check your request'
                      : job?.state === 'failed'
                        ? `Analysis failed · ${job.error?.code}`
                        : job?.state === 'queued' || submitting
                          ? 'Analysis queued'
                          : 'Agents are working'}
                  </strong>
                  <p>
                    {submissionError ??
                      job?.error?.message ??
                      (submitting
                        ? 'Submitting your request to the local queue.'
                        : job?.state === 'queued'
                          ? 'Waiting for the local worker. Your criteria remain fixed.'
                          : job?.submission.mode === 'replay'
                            ? 'Replaying exact captured decisions and rerunning current tools offline.'
                            : 'Running genuine local model decisions. Your criteria remain fixed.')}
                  </p>
                </div>
                {job && (
                  <button
                    className="button quiet"
                    onClick={() => inspectWorkflow('/api/analyses/job/' + job.id)}
                  >
                    Inspect this run
                    <ArrowRight size={15} />
                  </button>
                )}
                {busy && <progress aria-label="Analysis in progress" />}
              </div>
            )}
            {page === 'explore' && (
              <div className="explore-layout">
                <CriteriaForm
                  bootstrap={bootstrap.data}
                  draft={displayedDraft}
                  onChange={setDraft}
                  onSubmit={() => void submit('live')}
                  busy={busy}
                  reset={() => {
                    if (view) setDraft(view.request)
                  }}
                />
                <div className="analysis-area">
                  {changedDraft && (
                    <div className="draft-notice">
                      <InfoIcon />
                      Draft criteria changed. Run a live analysis to update the result.
                    </div>
                  )}
                  {analysis.error ? (
                    <div className="notice error" role="alert">
                      <p>{analysis.error}</p>
                      <button className="button secondary" onClick={analysis.retry}>
                        Retry result
                      </button>
                    </div>
                  ) : analysis.loading || !view ? (
                    <div className="explore-content loading-surface" role="status">
                      <h1>Loading the recorded analysis</h1>
                      <div className="skeleton title" />
                      <div className="skeleton chart" />
                    </div>
                  ) : (
                    <Explore
                      view={view}
                      selectedMonth={selectedMonth}
                      selectMonth={setSelectedMonth}
                      money={money}
                      area={area}
                      setMoney={setMoney}
                      setArea={setArea}
                      openWorkflow={() => inspectWorkflow()}
                      replay={() => void submit('replay')}
                      busy={busy}
                      captures={bootstrap.data.captures}
                      capture={captureId}
                      chooseCapture={chooseCapture}
                    />
                  )}
                </div>
              </div>
            )}
            {page === 'workflow' && (
              <>
                <Workflow
                  busy={busy}
                  key={workflowOverride ?? baseUrl}
                  baseUrl={workflowOverride ?? baseUrl}
                  feedback={() => {
                    chooseCapture('feedback')
                    setWorkflowOverride(null)
                  }}
                />
                {workflowOverride && (
                  <div className="wide-content return-route">
                    <button className="button secondary" onClick={() => setWorkflowOverride(null)}>
                      Return to current analysis route
                    </button>
                  </div>
                )}
              </>
            )}
            {page === 'experiments' && (
              <Experiments bootstrap={bootstrap.data} openWorkflow={inspectWorkflow} />
            )}
            {page === 'provenance' && <Provenance bootstrap={bootstrap.data} view={view} />}
          </>
        )}
      </main>
      <footer className="app-footer">
        <div>
          <span className="footer-mark" />
          Exact tools. Recorded decisions. Synthetic observations.
        </div>
        <span>
          Frozen feed ·{' '}
          {bootstrap.data
            ? `${monthLabel(bootstrap.data.dataset.month_start)} – ${monthLabel(bootstrap.data.dataset.month_end)}`
            : 'Loading provenance'}
        </span>
        <details className="recent-runs">
          <summary>Recent local runs</summary>
          {history.data?.length ? (
            <ul>
              {history.data.slice(0, 8).map((item) => (
                <li key={item.id}>
                  <button
                    onClick={() => {
                      if (item.output) {
                        setBaseUrl('/api/analyses/job/' + item.id)
                        setCaptureId('')
                        setDraft(item.submission.request)
                        setJob(item)
                        navigate('explore')
                      } else {
                        inspectWorkflow('/api/analyses/job/' + item.id)
                      }
                    }}
                  >
                    {item.submission.mode} · {item.state}
                    <small>{item.id.slice(0, 10)}</small>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p>No local web runs yet. Start a live analysis or replay a captured run.</p>
          )}
        </details>
      </footer>
    </>
  )
}

function InfoIcon() {
  return <AlertCircle size={16} aria-hidden="true" />
}
export default App
