import {
  ArrowRight,
  Braces,
  ChevronDown,
  Download,
  ExternalLink,
  FlaskConical,
  Info,
} from 'lucide-react'
import { useState } from 'react'
import type {
  Bootstrap,
  CampaignOverview,
  CaseDetail,
  CaseIndexItem,
  ExperimentView,
} from '../generated/contracts'
import { shortHash, useResource } from '../api'

function ResultTable({
  campaign,
  catalog,
}: {
  campaign: CampaignOverview
  catalog: Bootstrap['mr_catalog']
}) {
  if (!campaign.headlines.length)
    return (
      <div className="pending-results">
        <FlaskConical size={24} />
        <div>
          <h3>Outcomes are still being captured</h3>
          <p>
            The table is built from immutable case records after the campaign runs. Completed pairs
            are available below.
          </p>
        </div>
      </div>
    )
  return (
    <div className="table-scroll">
      <table className="data-table headline-table">
        <caption className="sr-only">
          Base-level any-seed violations and nominal Wilson 95% intervals
        </caption>
        <thead>
          <tr>
            <th scope="col">Relation</th>
            <th scope="col">Violating bases</th>
            <th scope="col">Rate</th>
            <th scope="col">Nominal 95% CI</th>
            <th scope="col">Seed pairs</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {campaign.headlines.map((row) => (
            <tr key={row.mr_id}>
              <th scope="row">
                <span className="mr-label">{row.mr_id}</span>
                {catalog.find((item) => item.id === row.mr_id)?.title}
              </th>
              <td>
                {row.violating_bases} / {row.completed_bases}
              </td>
              <td>{row.base_rate_label}</td>
              <td>
                <span>{row.ci95_label}</span>
                {row.ci95_low !== null && row.ci95_high !== null && (
                  <svg
                    className="interval"
                    viewBox="-2 0 104 10"
                    role="img"
                    aria-label={row.ci95_label}
                  >
                    <line x1="0" x2="100" y1="5" y2="5" className="interval-ground" />
                    <line
                      x1={Number(row.ci95_low) * 100}
                      x2={Number(row.ci95_high) * 100}
                      y1="5"
                      y2="5"
                      className="interval-range"
                    />
                    <circle cx={Number(row.base_rate ?? 0) * 100} cy="5" r="2.5" />
                  </svg>
                )}
              </td>
              <td>{row.seed_pairs_completed}</td>
              <td>
                <span className={`result-status ${row.complete ? 'pass' : 'execution_error'}`}>
                  {row.complete ? 'Complete' : 'Incomplete'}
                </span>
                {row.execution_errors > 0 && <small>{row.execution_errors} execution errors</small>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PairDetail({
  campaignId,
  item,
  openWorkflow,
}: {
  campaignId: string
  item: CaseIndexItem
  openWorkflow: (url: string) => void
}) {
  const url = `/api/experiments/${campaignId}/cases/${item.key}`
  const resource = useResource<CaseDetail>(url)
  if (resource.error)
    return (
      <div className="notice error">
        <p>{resource.error}</p>
        <button className="button secondary" onClick={resource.retry}>
          Retry comparison
        </button>
      </div>
    )
  if (resource.loading || !resource.data)
    return (
      <div className="loading-surface" role="status">
        Loading the paired evidence…
      </div>
    )
  const detail = resource.data
  return (
    <div className="pair-detail">
      <div className="section-heading">
        <div>
          <h3>
            {item.mr_id} · {item.base_id} · seed {item.seed}
          </h3>
          <p>
            <span className={`result-status ${item.status}`}>
              {item.status.replaceAll('_', ' ')}
            </span>
            {detail.result.violation_kind
              ? ` · ${detail.result.violation_kind.replaceAll('_', ' ')}`
              : ''}
          </p>
        </div>
        <a className="button quiet" href={url} download={`${item.key}.json`}>
          <Download size={15} />
          Case JSON
        </a>
      </div>
      <div className="paired-leg-headings">
        {(['source', 'followup'] as const).map((leg) => (
          <div key={leg}>
            <h4>{leg === 'source' ? 'Source' : 'Follow-up'}</h4>
            <span>
              {detail.result[leg].status === 'completed'
                ? `${detail[leg]?.total_label} observations`
                : `${detail.result[leg].error_code} · ${detail.result[leg].error_stage}`}
            </span>
            <button className="text-button" onClick={() => openWorkflow(url + '/' + leg)}>
              {detail.result[leg].status === 'completed' ? 'Inspect route' : 'Inspect failed trace'}
              <ArrowRight size={14} />
            </button>
          </div>
        ))}
      </div>
      {detail.source && detail.followup && (
        <div className="table-scroll">
          <table className="data-table pair-table">
            <caption>
              Selected projection for inspection · all assertions are in the case record
            </caption>
            <thead>
              <tr>
                <th scope="col">Month</th>
                <th scope="col">Source count</th>
                <th scope="col">Follow-up count</th>
                <th scope="col">Source price</th>
                <th scope="col">Follow-up price</th>
              </tr>
            </thead>
            <tbody>
              {detail.source.months.map((source) => {
                const followup = detail.followup?.months.find(
                  (month) => month.month === source.month,
                )
                return (
                  <tr key={source.month}>
                    <th scope="row">{source.label}</th>
                    <td>{source.observations}</td>
                    <td>{followup?.observations ?? 'Outside window'}</td>
                    <td>{source.price}</td>
                    <td>{followup?.price ?? 'Outside window'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {detail.result.comparison && (
        <p className="comparison-scope">
          {detail.result.comparison.compared_numeric_count} numeric fields compared · maximum
          declared-projection error <code>{detail.result.comparison.max_absolute_error}</code>
        </p>
      )}
      {!!detail.result.comparison?.differences.length && (
        <div className="difference-list">
          <h4>Observed differences</h4>
          {detail.result.comparison.differences.map((difference) => (
            <div key={difference.path}>
              <code>{difference.path}</code>
              <p>
                {difference.rule} · expected {JSON.stringify(difference.expected)} · observed{' '}
                {JSON.stringify(difference.followup)}
              </p>
              <small>
                Tolerance {difference.tolerance ?? 'exact'} · absolute error{' '}
                {difference.absolute_error ?? 'not numeric'}
              </small>
            </div>
          ))}
        </div>
      )}
      {!!detail.result.reason_codes.length && (
        <div className="notice error">
          <p>
            Recorded failure: {detail.result.reason_codes.join(' · ')}.{' '}
            {detail.result.status === 'execution_error'
              ? 'This pair leaves its base incomplete.'
              : 'This eligible output-contract failure counts as a violation.'}
          </p>
        </div>
      )}
      {detail.result.source_reused_from && (
        <p className="source-reuse">
          <Info size={15} />
          Source reused under an identical full execution key. Follow-up executed afresh.
        </p>
      )}
      <details>
        <summary>
          Nonvacuity witnesses and transformation <ChevronDown size={16} />
        </summary>
        <div className="evidence-columns">
          <div>
            <h4>Independent preflight</h4>
            <pre>{JSON.stringify(detail.witness, null, 2)}</pre>
          </div>
          <div>
            <h4>Frozen recipe</h4>
            <pre>{JSON.stringify(detail.recipe, null, 2)}</pre>
            <p>
              Base identity{' '}
              <code title={detail.result.base_semantic_sha256}>
                {shortHash(detail.result.base_semantic_sha256)}
              </code>
            </p>
          </div>
        </div>
      </details>
    </div>
  )
}

export function Experiments({
  bootstrap,
  openWorkflow,
}: {
  bootstrap: Bootstrap
  openWorkflow: (url: string) => void
}) {
  const resource = useResource<ExperimentView>('/api/experiments', 5000)
  const [campaignId, setCampaignId] = useState('')
  const [mr, setMr] = useState('all')
  const [selectedCase, setSelectedCase] = useState('')
  const [page, setPage] = useState(0)
  const campaigns = resource.data?.campaigns ?? []
  const campaign =
    campaigns.find((item) => item.id === campaignId) ??
    [...campaigns].reverse().find((item) => item.scope === 'headline' && item.mode === 'live') ??
    campaigns[0]
  const index = useResource<CaseIndexItem[]>(
    campaign ? `/api/experiments/${campaign.id}/cases` : null,
    5000,
  )
  const filtered = (index.data ?? []).filter((item) => mr === 'all' || item.mr_id === mr)
  const current = filtered.find((item) => item.key === selectedCase) ?? filtered[0]
  const pageItems = filtered.slice(page * 30, page * 30 + 30)
  return (
    <div className="wide-content experiments-page">
      <div className="page-heading">
        <div>
          <h1>Metamorphic experiments</h1>
          <p>Change an input. Execute both legs. Inspect the declared relationship.</p>
        </div>
        {campaign && (
          <label className="record-select">
            Campaign
            <select
              value={campaign.id}
              onChange={(event) => {
                setCampaignId(event.target.value)
                setPage(0)
                setSelectedCase('')
              }}
            >
              {campaigns.map((item) => (
                <option value={item.id} key={item.id}>
                  {item.id} · {item.mode}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {resource.error && (
        <div className="notice error" role="alert">
          <p>{resource.error}</p>
          <button className="button secondary" onClick={resource.retry}>
            Retry campaigns
          </button>
        </div>
      )}
      {campaign ? (
        <>
          <section className="campaign-progress">
            <div>
              <span className="status-badge">
                {campaign.scope === 'headline'
                  ? 'Headline'
                  : campaign.scope === 'pilot'
                    ? 'Pilot · MR01 only'
                    : 'Auxiliary'}{' '}
                · {campaign.mode}
              </span>
              <h2>
                {campaign.completed_comparisons} / {campaign.expected_comparisons} comparisons
                recorded
              </h2>
              <p>
                {campaign.state === 'complete'
                  ? 'All expected paired outcomes are available.'
                  : campaign.state === 'incomplete'
                    ? 'The campaign needs missing or failed infrastructure attempts resolved.'
                    : 'Actual source/follow-up executions are being captured.'}
              </p>
            </div>
            <div className="progress-detail">
              <progress
                value={campaign.completed_comparisons}
                max={campaign.expected_comparisons}
                aria-label="Recorded logical comparisons"
              />
              <small>Fixed paired seeds {campaign.seeds.join(' · ')}</small>
              {campaign.last_case && (
                <code>
                  {campaign.last_case} · {campaign.last_status}
                </code>
              )}
            </div>
          </section>
          <section className="results-section">
            <div className="section-heading">
              <div>
                <h2>Base-level outcomes</h2>
                <p>A base violates when any of its three fixed seed pairs violates.</p>
              </div>
            </div>
            <ResultTable campaign={campaign} catalog={bootstrap.mr_catalog} />
            <div className="method-note">
              <Info size={17} />
              <p>
                Wilson intervals use completed <strong>bases</strong>, with all three paired
                outcomes available. Query slices overlap one synthetic feed; these are nominal
                uncertainty summaries for a designed workload. A pilot is separate from the
                30-base-per-relation headline evaluation.
              </p>
            </div>
          </section>
          <section className="cases-section">
            <div className="section-heading">
              <div>
                <h2>Open a paired case</h2>
                <p>Every outcome links source, transformation, follow-up and failure evidence.</p>
              </div>
              <label className="field inline">
                Relation
                <select
                  value={mr}
                  onChange={(event) => {
                    setMr(event.target.value)
                    setPage(0)
                  }}
                >
                  <option value="all">All recorded</option>
                  {bootstrap.mr_catalog.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.id}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {index.error ? (
              <p className="error-text">{index.error}</p>
            ) : filtered.length ? (
              <div className="case-inspector">
                <div className="case-list">
                  <div className="case-list-heading">
                    <span>Base / paired seed</span>
                    <span>Outcome</span>
                  </div>
                  {pageItems.map((item) => (
                    <button
                      type="button"
                      key={item.key}
                      className={current?.key === item.key ? 'selected' : ''}
                      aria-pressed={current?.key === item.key}
                      onClick={() => setSelectedCase(item.key)}
                    >
                      <span>
                        <strong>
                          {item.mr_id} · {item.base_id}
                        </strong>
                        <small>seed {item.seed}</small>
                      </span>
                      <span className={`result-status ${item.status}`}>
                        {item.status.replaceAll('_', ' ')}
                      </span>
                    </button>
                  ))}
                  {filtered.length > 30 && (
                    <div className="pagination">
                      <button
                        className="text-button"
                        onClick={() => setPage((value) => Math.max(0, value - 1))}
                        disabled={page === 0}
                      >
                        Previous
                      </button>
                      <span>
                        {page + 1} / {Math.ceil(filtered.length / 30)}
                      </span>
                      <button
                        className="text-button"
                        onClick={() => setPage((value) => value + 1)}
                        disabled={(page + 1) * 30 >= filtered.length}
                      >
                        Next
                      </button>
                    </div>
                  )}
                </div>
                {current && (
                  <PairDetail
                    key={`${campaign.id}/${current.key}`}
                    campaignId={campaign.id}
                    item={current}
                    openWorkflow={openWorkflow}
                  />
                )}
              </div>
            ) : (
              <div className="empty-state">
                <Braces size={24} />
                <h3>No completed case here yet</h3>
                <p>
                  Choose another relation, or return after its first source/follow-up comparison is
                  recorded.
                </p>
              </div>
            )}
          </section>
        </>
      ) : (
        <div className="empty-state">
          <FlaskConical size={28} />
          <h2>Ready for captured experiments</h2>
          <p>
            Campaigns appear here when the local harness starts. The ten declared relations are
            available below.
          </p>
        </div>
      )}
      <section className="catalog-section">
        <div className="section-heading">
          <div>
            <h2>The ten relations</h2>
            <p>Three families, explicit subdomains and meaningful witnesses.</p>
          </div>
          <a className="text-button" href="/api/bootstrap" target="_blank" rel="noreferrer">
            Catalog JSON
            <ExternalLink size={14} />
          </a>
        </div>
        {bootstrap.mr_catalog.map((item) => (
          <details key={item.id} className="catalog-entry">
            <summary>
              <span className="mr-label">{item.id}</span>
              <strong>{item.title}</strong>
              <span className="family-label">{item.family}</span>
              <ChevronDown size={16} />
            </summary>
            <div className="catalog-detail">
              <p>{item.relation}</p>
              <h3>Valid subdomain</h3>
              <ul>
                {item.preconditions.map((condition) => (
                  <li key={condition}>{condition}</li>
                ))}
              </ul>
              <p>
                <strong>Nonvacuity witness:</strong> {item.witness}
              </p>
              <details>
                <summary>Compared fields and tolerances</summary>
                <pre>
                  {JSON.stringify(
                    { fields: item.compared_fields, tolerances: item.tolerances },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </div>
          </details>
        ))}
      </section>
    </div>
  )
}
