import { useEffect, useRef, useState } from 'react'
import type { AnalysisView, MonthView, PlotPoint } from '../generated/contracts'
import { metricNames } from './metrics'
import type { Metric } from './metrics'

export function TrendChart({
  view,
  selectedMonth,
  selectMonth,
  metric,
}: {
  view: AnalysisView
  selectedMonth: string
  selectMonth: (month: string) => void
  metric: Metric
}) {
  const frame = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(900)
  useEffect(() => {
    if (!frame.current) return
    const observer = new ResizeObserver((entries) => {
      const first = entries[0]
      if (first) setWidth(Math.max(280, first.contentRect.width))
    })
    observer.observe(frame.current)
    return () => observer.disconnect()
  }, [])
  const compact = width < 584
  const height = compact ? 252 : 280
  const left = 78,
    right = width - 22,
    top = 24,
    bottom = height - (compact ? 40 : 24)
  const pointFor = (month: MonthView): PlotPoint =>
    metric === 'price' ? month.price_plot : metric === 'ppsf' ? month.ppsf_plot : month.count_plot
  const xFor = (point: PlotPoint) => left + Number(point.x) * (right - left)
  const yFor = (point: PlotPoint) => top + Number(point.y) * (bottom - top)
  const ticks =
    metric === 'price' ? view.price_ticks : metric === 'ppsf' ? view.ppsf_ticks : view.count_ticks
  const selected = view.months.find((month) => month.month === selectedMonth)
  const selectedPoint = selected ? pointFor(selected) : null
  let path = '',
    penDown = false
  for (const month of view.months) {
    const point = pointFor(month)
    if (point.y === null) {
      penDown = false
      continue
    }
    path += `${penDown ? 'L' : 'M'}${xFor(point)},${yFor(point)} `
    penDown = true
  }
  return (
    <div className="trend-chart" ref={frame}>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="trend-title trend-desc">
        <title id="trend-title">{metricNames[metric]} across twelve months</title>
        <desc id="trend-desc">
          Synthetic observations. Select a month using the controls below; its exact values also
          appear in the monthly table. Gaps represent months without observations.
        </desc>
        {ticks.map((tick) => {
          const y = top + Number(tick.y) * (bottom - top)
          return (
            <g key={tick.y}>
              <line className="chart-grid" x1={left} x2={right} y1={y} y2={y} />
              <text className="chart-tick" x={left - 14} y={y + 4} textAnchor="end">
                {tick.label}
              </text>
            </g>
          )
        })}
        {selectedPoint && (
          <line
            className="chart-selection"
            x1={xFor(selectedPoint)}
            x2={xFor(selectedPoint)}
            y1={top}
            y2={bottom}
          />
        )}
        <path className="chart-line" d={path} fill="none" />
        {view.months.map((month) => {
          const point = pointFor(month)
          return point.y === null ? null : (
            <circle
              key={month.month}
              className={month.month === selectedMonth ? 'chart-station selected' : 'chart-station'}
              cx={xFor(point)}
              cy={yFor(point)}
              r={month.month === selectedMonth ? 6 : 3.5}
            />
          )
        })}
        {compact &&
          [0, 3, 6, 9, 11].map((index) => {
            const month = view.months[index]
            return (
              month && (
                <text
                  key={month.month}
                  className="chart-tick chart-month-tick"
                  x={xFor(pointFor(month))}
                  y={height - 12}
                  textAnchor="middle"
                >
                  {month.short_label} ’{month.month.slice(2, 4)}
                </text>
              )
            )
          })}
      </svg>
      {compact ? (
        <label className="mobile-month-picker">
          Inspect month
          <select value={selectedMonth} onChange={(event) => selectMonth(event.target.value)}>
            {view.months.map((month) => (
              <option key={month.month} value={month.month}>
                {month.label}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <div className="month-selector" role="group" aria-label="Select a month to inspect">
          {view.months.map((month, index) => (
            <button
              key={month.month}
              type="button"
              aria-pressed={month.month === selectedMonth}
              onClick={() => selectMonth(month.month)}
              onKeyDown={(event) => {
                const next =
                  event.key === 'ArrowRight'
                    ? Math.min(index + 1, 11)
                    : event.key === 'ArrowLeft'
                      ? Math.max(0, index - 1)
                      : event.key === 'Home'
                        ? 0
                        : event.key === 'End'
                          ? 11
                          : null
                const target = next === null ? null : view.months[next]
                if (target && next !== null) {
                  event.preventDefault()
                  selectMonth(target.month)
                  const sibling = event.currentTarget.parentElement?.children[next]
                  if (sibling instanceof HTMLButtonElement) sibling.focus()
                }
              }}
              aria-label={`Inspect ${month.label}`}
            >
              <span>{month.short_label}</span>
              <small>{month.month.slice(2, 4)}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
