import { ArrowRight, Download, Info, Network, Play, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import type { AnalysisView, CaptureSummary, MonthView } from '../generated/contracts'
import { shortHash } from '../api'
import { TrendChart } from './TrendChart'
import { metricNames } from './metrics'
import type { Metric } from './metrics'

export function Explore({
  view,
  selectedMonth,
  selectMonth,
  money,
  area,
  setMoney,
  setArea,
  openWorkflow,
  replay,
  busy,
  captures,
  capture,
  chooseCapture,
}: {
  view: AnalysisView
  selectedMonth: string
  selectMonth: (month: string) => void
  money: 'USD' | 'USD_THOUSANDS'
  area: 'SQFT' | 'SQM'
  setMoney: (value: 'USD' | 'USD_THOUSANDS') => void
  setArea: (value: 'SQFT' | 'SQM') => void
  openWorkflow: () => void
  replay: () => void
  busy: boolean
  captures: CaptureSummary[]
  capture: string
  chooseCapture: (value: string) => void
}) {
  const [metric, setMetric] = useState<Metric>('price')
  const selected: MonthView | undefined =
    view.months.find((month) => month.month === selectedMonth) ?? view.months.at(-1)
  const selectedId = selected?.month ?? selectedMonth
  const csv = `${view.csv_url}?money=${money}&area=${area}`
  const noMatches = view.output.canonical.summary.total_observations === 0
  return (
    <div className="explore-content">
      <div className="page-heading">
        <div>
          <h1>Twelve months of housing</h1>
          <p>A synthetic slice. Every number has a trail.</p>
        </div>
        <label className="record-select">
          Recorded example
          <select
            value={capture}
            disabled={busy}
            onChange={(event) => chooseCapture(event.target.value)}
          >
            <option value="" disabled>
              Current analysis
            </option>
            {captures.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="analysis-status">
        <span className="status-badge">
          {view.origin === 'live_capture'
            ? 'Captured live'
            : view.origin === 'replay'
              ? 'Offline replay'
              : 'Live analysis'}
        </span>
        <span>
          {view.output.canonical.window_start} – {view.output.canonical.window_end}
        </span>
        <span className="status-right">
          {noMatches ? <Info size={15} /> : <ShieldCheck size={15} />}
          {noMatches
            ? 'No matches'
            : view.output.quality.status === 'complete'
              ? 'Complete support'
              : 'Limited support'}
        </span>
      </div>
      {view.purpose === 'auxiliary_index_omission' && (
        <div className="notice warning">
          <Info size={18} />
          <p>
            <strong>Auxiliary feedback control.</strong> An omitted index partition triggered an
            authoritative rescan, recovering two observations to three. This control is separate
            from headline experiments.
          </p>
        </div>
      )}
      <section className="trend-section" aria-labelledby="trend-heading">
        <div className="chart-toolbar">
          <h2 id="trend-heading">
            {metricNames[metric]}
            {metric === 'ppsf' ? ` / ${view.area_unit}` : ''}
          </h2>
          <div className="display-controls">
            <label>
              <span className="sr-only">Money display</span>
              <select
                value={money}
                onChange={(event) => setMoney(event.target.value as 'USD' | 'USD_THOUSANDS')}
              >
                <option value="USD">USD</option>
                <option value="USD_THOUSANDS">USD thousands</option>
              </select>
            </label>
            <label>
              <span className="sr-only">Area display</span>
              <select
                value={area}
                onChange={(event) => setArea(event.target.value as 'SQFT' | 'SQM')}
              >
                <option value="SQFT">sq ft</option>
                <option value="SQM">m²</option>
              </select>
            </label>
          </div>
        </div>
        <div className="metric-switch" role="group" aria-label="Chart measure">
          {(['price', 'ppsf', 'count'] as const).map((item) => (
            <button
              type="button"
              key={item}
              aria-pressed={metric === item}
              onClick={() => setMetric(item)}
            >
              {item === 'price' ? 'List price' : item === 'ppsf' ? 'Price / area' : 'Observations'}
            </button>
          ))}
        </div>
        {noMatches ? (
          <div className="empty-state empty-trend" role="status">
            <Info size={24} aria-hidden="true" />
            <h3>No matching observations</h3>
            <p>
              These criteria match none of the frozen synthetic observations in this twelve-month
              window. Adjust the criteria and run again, or choose a recorded example.
            </p>
          </div>
        ) : (
          <TrendChart
            view={view}
            selectedMonth={selectedId}
            selectMonth={selectMonth}
            metric={metric}
          />
        )}
        {selected && (
          <div className="month-inspector" aria-live="polite">
            <div className="inspector-title">
              <span className="station-mark" />
              <h3>{selected.label}</h3>
              <span className={`support-label ${selected.support}`}>
                {selected.support === 'supported'
                  ? '5+ observations'
                  : selected.support === 'sparse'
                    ? 'Sparse support'
                    : 'Empty month'}
              </span>
            </div>
            <dl className="selected-values">
              <div>
                <dt>Median list price</dt>
                <dd>{selected.price}</dd>
              </div>
              <div>
                <dt>Median / {view.area_unit}</dt>
                <dd>{selected.price_per_area}</dd>
              </div>
              <div>
                <dt>Month over month</dt>
                <dd>{selected.price_mom}</dd>
              </div>
              <div>
                <dt>Observations</dt>
                <dd>{selected.observations}</dd>
              </div>
            </dl>
          </div>
        )}
        <p className="chart-note">
          Select a month to inspect. Price per area is the median of individual listing ratios.
          Empty months stay visible.
        </p>
      </section>
      <div className="analysis-brief">
        <p>
          <strong>{view.window_change_label}</strong> first-to-last median price change across
          eleven monthly intervals.
          <br />
          <span>{view.total_label} qualifying monthly observations in this window.</span>
        </p>
        <button className="button secondary" type="button" onClick={openWorkflow}>
          <Network size={17} />
          Follow the agents
          <ArrowRight size={16} />
        </button>
      </div>
      <section className="monthly-section" aria-labelledby="monthly-heading">
        <div className="section-heading">
          <div>
            <h2 id="monthly-heading">The monthly record</h2>
            <p>Rounded for reading. Exact six-decimal values are in the JSON export.</p>
          </div>
          <div className="export-links">
            <a className="button quiet" href={csv}>
              <Download size={15} />
              CSV
            </a>
            <a className="button quiet" href={view.json_url}>
              <Download size={15} />
              JSON
            </a>
          </div>
        </div>
        <div className="table-scroll">
          <p className="table-hint">Scroll horizontally to see every measure.</p>
          <table className="data-table monthly-table">
            <caption className="sr-only">
              Synthetic housing observations and median statistics by month
            </caption>
            <thead>
              <tr>
                <th scope="col">Month</th>
                <th scope="col">List price</th>
                <th scope="col">Price / {view.area_unit}</th>
                <th scope="col">MoM price</th>
                <th scope="col">YoY price</th>
                <th scope="col">Observations</th>
              </tr>
            </thead>
            <tbody>
              {view.months.map((month) => (
                <tr key={month.month} className={month.month === selectedId ? 'selected' : ''}>
                  <th scope="row">
                    <button
                      type="button"
                      aria-pressed={month.month === selectedId}
                      onClick={() => selectMonth(month.month)}
                    >
                      {month.label}
                    </button>
                  </th>
                  <td>{month.price}</td>
                  <td>{month.price_per_area}</td>
                  <td>{month.price_mom}</td>
                  <td>{month.price_yoy}</td>
                  <td>{month.observations}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="grounded-note">
        <Info size={19} />
        <div>
          <h2>What this run supports</h2>
          <p>{view.output.narrative.text}</p>
          <div className="provenance-inline">
            <span>
              Query{' '}
              <code title={view.output.metadata.query_sha256}>
                {shortHash(view.output.metadata.query_sha256)}
              </code>
            </span>
            <span>Seed {view.output.metadata.requested_seed}</span>
            <span>{view.output.metadata.model_profile}</span>
          </div>
        </div>
      </section>
      {view.origin === 'live_capture' && (
        <div className="replay-row">
          <div>
            <h2>Run this evidence again</h2>
            <p>
              Replay the captured model decisions through current tools and control flow, with
              network access blocked.
            </p>
          </div>
          <button type="button" className="button secondary" onClick={replay} disabled={busy}>
            <Play size={15} />
            Replay captured run
          </button>
        </div>
      )}
    </div>
  )
}
