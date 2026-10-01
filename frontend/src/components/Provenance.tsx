import { Database, Fingerprint, LockKeyhole } from 'lucide-react'
import type { AnalysisView, Bootstrap } from '../generated/contracts'
import { shortHash } from '../api'

export function Provenance({
  bootstrap,
  view,
}: {
  bootstrap: Bootstrap
  view: AnalysisView | null
}) {
  const dataset = bootstrap.dataset
  return (
    <div className="wide-content provenance-page">
      <div className="page-heading">
        <div>
          <h1>Know what is underneath</h1>
          <p>Frozen data, explicit contracts and an inspectable execution boundary.</p>
        </div>
        <span className="status-badge synthetic">Synthetic data</span>
      </div>
      <section className="provenance-section">
        <div className="section-icon">
          <Database size={23} />
        </div>
        <div>
          <h2>The frozen feed</h2>
          <p className="lead-copy">
            {dataset.actual_rows.toLocaleString('en')} generated monthly observations, across twelve
            Dallas-themed ZIPs and twenty-four calendar months. These records are a software test
            feed.
          </p>
          <dl className="provenance-grid">
            <div>
              <dt>Dataset</dt>
              <dd>{dataset.dataset_id}</dd>
            </div>
            <div>
              <dt>Calendar coverage</dt>
              <dd>
                {dataset.month_start} – {dataset.month_end}
              </dd>
            </div>
            <div>
              <dt>Valid / quarantined</dt>
              <dd>
                {dataset.valid_rows.toLocaleString('en')} / {dataset.quarantined_rows}
              </dd>
            </div>
            <div>
              <dt>Generated-data license</dt>
              <dd>{dataset.data_license}</dd>
            </div>
            <div className="full-span">
              <dt>CSV SHA-256</dt>
              <dd>
                <code className="hash-full">{dataset.snapshot_sha256}</code>
              </dd>
            </div>
          </dl>
          <h3>Where the data stops</h3>
          <ul className="plain-list">
            {dataset.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </section>
      <section className="provenance-section">
        <div className="section-icon">
          <LockKeyhole size={23} />
        </div>
        <div>
          <h2>The statistical contract</h2>
          <p>
            Counts represent monthly observation records. Repeated business listing labels remain
            separate observations; duplicate record identities invalidate a dataset.
          </p>
          <dl className="definition-list">
            <div>
              <dt>Median list price</dt>
              <dd>
                The exact median of qualifying raw USD prices in each month, including an average of
                the middle two values for an even count.
              </dd>
            </div>
            <div>
              <dt>Median price per area</dt>
              <dd>
                The median of each qualifying record’s individual price/size ratio. This is pooled
                again for each requested ZIP.
              </dd>
            </div>
            <div>
              <dt>Percentage change</dt>
              <dd>
                100 × (current / previous − 1), from exact values. Undefined comparisons stay null.
                Visible windows retain available historical lookbacks.
              </dd>
            </div>
            <div>
              <dt>Rounding</dt>
              <dd>
                Integers and fractions internally; six-decimal half-even serialization. Display
                conversion uses exact 0.09290304 m² per sq ft and runs on the backend.
              </dd>
            </div>
          </dl>
        </div>
      </section>
      <section className="provenance-section">
        <div className="section-icon">
          <Fingerprint size={23} />
        </div>
        <div>
          <h2>The execution boundary</h2>
          <dl className="provenance-grid">
            <div>
              <dt>Python</dt>
              <dd>{bootstrap.python_version}</dd>
            </div>
            <div>
              <dt>Fast Agent</dt>
              <dd>{bootstrap.fast_agent_version}</dd>
            </div>
            <div>
              <dt>Local model</dt>
              <dd>{bootstrap.live_model_profile}</dd>
            </div>
            <div>
              <dt>Fixed paired seeds</dt>
              <dd>{bootstrap.seed_values.join(' · ')}</dd>
            </div>
          </dl>
          <p>{bootstrap.live_model_requirements}</p>
          <p>
            Each live run verifies its frozen model digest and seed defaults. Seed-controlled
            inference remains best effort; a replay reproduces that captured decision panel.
          </p>
          {view && (
            <details className="current-provenance">
              <summary>Current run identity · {view.output.metadata.run_id}</summary>
              <dl className="definition-list">
                {Object.entries(view.output.metadata).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key.replaceAll('_', ' ')}</dt>
                    <dd>
                      <code title={String(value)}>
                        {typeof value === 'string' && value.length === 64
                          ? shortHash(value)
                          : String(value ?? 'Not applicable')}
                      </code>
                    </dd>
                  </div>
                ))}
              </dl>
            </details>
          )}
        </div>
      </section>
      <div className="method-note">
        <p>
          <strong>Coursework context.</strong> IIIT Hyderabad TSE assignment · due 16 October 2026 ·
          teams of two. The original assignment, editable implementation notes, notebook and AI-use
          disclosure ship in the repository. No submission hour or author identities are inferred.
        </p>
      </div>
    </div>
  )
}
