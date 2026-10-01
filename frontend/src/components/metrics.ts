export type Metric = 'price' | 'ppsf' | 'count'
export const metricNames: Record<Metric, string> = {
  price: 'Median list price',
  ppsf: 'Median price per area',
  count: 'Observations',
}
