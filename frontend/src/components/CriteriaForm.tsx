import { ArrowRight, ChevronDown, RotateCcw, SlidersHorizontal } from 'lucide-react'
import { useState } from 'react'
import type {
  AnalysisRequest,
  Bootstrap,
  Criteria,
  PropertyType,
  Zip,
} from '../generated/contracts'
import { monthLabel } from '../api'

const propertyNames: Record<PropertyType, string> = {
  single_family: 'Single family',
  condo: 'Condo',
  townhouse: 'Townhouse',
}

export function CriteriaForm({
  bootstrap,
  draft,
  onChange,
  onSubmit,
  busy,
  reset,
}: {
  bootstrap: Bootstrap
  draft: AnalysisRequest
  onChange: (request: AnalysisRequest) => void
  onSubmit: () => void
  busy: boolean
  reset: () => void
}) {
  const [expanded, setExpanded] = useState(() => window.matchMedia('(min-width: 761px)').matches)
  const criteria = draft.criteria
  const update = (changes: Partial<Criteria>) =>
    onChange({ ...draft, criteria: { ...criteria, ...changes } })
  const months = Object.keys(bootstrap.dataset.month_completeness).sort().slice(11)
  const toggleZip = (zip: Zip) => {
    const next = criteria.zips.includes(zip)
      ? criteria.zips.filter((item) => item !== zip)
      : [...criteria.zips, zip].sort()
    if (next.length) update({ zips: next as Criteria['zips'] })
  }
  const toggleType = (property: PropertyType) => {
    const next = criteria.property_types.includes(property)
      ? criteria.property_types.filter((item) => item !== property)
      : [...criteria.property_types, property]
    if (next.length) update({ property_types: next as Criteria['property_types'] })
  }
  const integer = (value: string) => (value === '' ? null : Number.parseInt(value, 10))
  return (
    <aside className="criteria-rail">
      <button
        className="criteria-disclosure"
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
      >
        <span>
          <SlidersHorizontal size={18} /> Your slice
        </span>
        <ChevronDown size={18} className={expanded ? 'rotated' : ''} />
      </button>
      {!expanded && (
        <p className="collapsed-summary">
          {criteria.zips.length} ZIPs · through {monthLabel(draft.window_end)}
        </p>
      )}
      {expanded && (
        <form
          className="criteria-form"
          onSubmit={(event) => {
            event.preventDefault()
            onSubmit()
          }}
        >
          <p className="form-context">Criteria stay fixed throughout every agent review.</p>
          <label className="field">
            Window ends
            <select
              value={draft.window_end}
              onChange={(event) => onChange({ ...draft, window_end: event.target.value })}
            >
              {months.map((month) => (
                <option key={month} value={month}>
                  {monthLabel(month)}
                </option>
              ))}
            </select>
            <small>Twelve calendar months, with available lookbacks.</small>
          </label>
          <fieldset>
            <legend>
              ZIP codes <span>{criteria.zips.length} selected</span>
            </legend>
            <div className="zip-grid">
              {bootstrap.dataset.zips.map((zip) => (
                <label className="zip-choice" key={zip}>
                  <input
                    type="checkbox"
                    checked={criteria.zips.includes(zip)}
                    onChange={() => toggleZip(zip)}
                  />
                  <span>{zip}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>Property types</legend>
            <div className="check-stack">
              {bootstrap.dataset.property_types.map((property) => (
                <label key={property}>
                  <input
                    type="checkbox"
                    checked={criteria.property_types.includes(property)}
                    onChange={() => toggleType(property)}
                  />
                  {propertyNames[property]}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>Bedrooms</legend>
            <div className="field-pair">
              <label className="field">
                Minimum
                <select
                  value={criteria.bedrooms_min}
                  onChange={(event) => update({ bedrooms_min: Number(event.target.value) })}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n}>{n}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                Maximum
                <select
                  value={criteria.bedrooms_max}
                  onChange={(event) => update({ bedrooms_max: Number(event.target.value) })}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n}>{n}</option>
                  ))}
                </select>
              </label>
            </div>
          </fieldset>
          <fieldset>
            <legend>
              List price <span>USD</span>
            </legend>
            <div className="field-pair">
              <label className="field">
                Minimum
                <input
                  type="number"
                  min="0"
                  step="1"
                  placeholder="Any"
                  value={criteria.price_min_cents === null ? '' : criteria.price_min_cents / 100}
                  onChange={(event) => {
                    const value = integer(event.target.value)
                    update({ price_min_cents: value === null ? null : value * 100 })
                  }}
                />
              </label>
              <label className="field">
                Maximum
                <input
                  type="number"
                  min="0"
                  step="1"
                  placeholder="Any"
                  value={criteria.price_max_cents === null ? '' : criteria.price_max_cents / 100}
                  onChange={(event) => {
                    const value = integer(event.target.value)
                    update({ price_max_cents: value === null ? null : value * 100 })
                  }}
                />
              </label>
            </div>
            <small>Inclusive bounds in raw US dollars.</small>
          </fieldset>
          <details className="advanced">
            <summary>
              Size and execution <ChevronDown size={15} />
            </summary>
            <fieldset>
              <legend>
                Interior area <span>sq ft</span>
              </legend>
              <div className="field-pair">
                <label className="field">
                  Minimum
                  <input
                    type="number"
                    min="1"
                    step="1"
                    placeholder="Any"
                    value={criteria.sqft_min ?? ''}
                    onChange={(event) => update({ sqft_min: integer(event.target.value) })}
                  />
                </label>
                <label className="field">
                  Maximum
                  <input
                    type="number"
                    min="1"
                    step="1"
                    placeholder="Any"
                    value={criteria.sqft_max ?? ''}
                    onChange={(event) => update({ sqft_max: integer(event.target.value) })}
                  />
                </label>
              </div>
            </fieldset>
            <label className="field">
              Fixed model seed
              <select
                value={draft.seed}
                onChange={(event) => onChange({ ...draft, seed: Number(event.target.value) })}
              >
                {bootstrap.seed_values.map((seed) => (
                  <option key={seed}>{seed}</option>
                ))}
              </select>
            </label>
            <label className="checkbox-line">
              <input
                type="checkbox"
                checked={draft.compare_regions}
                onChange={(event) => onChange({ ...draft, compare_regions: event.target.checked })}
              />
              Compare ZIPs with Region
            </label>
          </details>
          <button type="submit" className="button primary full" disabled={busy}>
            {busy ? 'Analysis in progress' : 'Run live analysis'}
            <ArrowRight size={17} />
          </button>
          <button type="button" className="text-button reset" onClick={reset} disabled={busy}>
            <RotateCcw size={14} /> Restore recorded criteria
          </button>
          <p className="form-footnote">
            Uses the frozen synthetic feed and your selected local model seed.
          </p>
        </form>
      )}
    </aside>
  )
}
