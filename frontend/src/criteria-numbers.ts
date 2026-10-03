// User-entered bounds are parsed as decimal text before becoming safe JSON integers.
export type ParsedBound =
  | { valid: true; value: number | null }
  | { valid: false; error: string }

const maximumInteger = 9_007_199_254_740_991n

export function parseUsdBound(text: string): ParsedBound {
  const value = text.trim()
  if (value === '') return { valid: true, value: null }
  const match = /^([0-9]*)(?:\.([0-9]{0,2}))?$/.exec(value)
  const whole = match?.[1] ?? ''
  const fraction = match?.[2] ?? ''
  if (!match || (!whole && !fraction) || value.length > 32) {
    return { valid: false, error: 'Use dollars with up to two decimal places.' }
  }
  const cents = BigInt(whole || '0') * 100n + BigInt(fraction.padEnd(2, '0'))
  if (cents > maximumInteger) return { valid: false, error: 'Enter a smaller price.' }
  return { valid: true, value: Number(cents) }
}

export function formatUsdBound(cents: number | null): string {
  if (cents === null) return ''
  if (!Number.isSafeInteger(cents) || cents < 0) throw new RangeError('Invalid integer-cent bound')
  const value = BigInt(cents)
  const whole = (value / 100n).toString()
  const fraction = value % 100n
  return fraction === 0n ? whole : whole + '.' + fraction.toString().padStart(2, '0')
}

export function parseWholeAreaBound(text: string): ParsedBound {
  const value = text.trim()
  if (value === '') return { valid: true, value: null }
  if (!/^[0-9]+$/.test(value) || value.length > 32) {
    return { valid: false, error: 'Use a positive whole number of square feet.' }
  }
  const area = BigInt(value)
  if (area < 1n) return { valid: false, error: 'Area must be at least one square foot.' }
  if (area > maximumInteger) return { valid: false, error: 'Enter a smaller area.' }
  return { valid: true, value: Number(area) }
}
