import assert from 'node:assert/strict'
import test from 'node:test'
import { formatUsdBound, parseUsdBound, parseWholeAreaBound } from '../src/criteria-numbers.ts'

test('USD bounds retain cents, including typed partial decimals and the safe integer boundary', () => {
  assert.deepEqual(parseUsdBound('250000.25'), { valid: true, value: 25_000_025 })
  assert.deepEqual(parseUsdBound('0.01'), { valid: true, value: 1 })
  assert.deepEqual(parseUsdBound('.5'), { valid: true, value: 50 })
  assert.deepEqual(parseUsdBound('12.'), { valid: true, value: 1200 })
  assert.deepEqual(parseUsdBound('90071992547409.91'), { valid: true, value: 9_007_199_254_740_991 })
  assert.equal(formatUsdBound(25_000_025), '250000.25')
  assert.equal(formatUsdBound(9_007_199_254_740_991), '90071992547409.91')
})

test('malformed or excessive-precision USD is rejected instead of truncated', () => {
  for (const value of ['250000.255', '1e3', '-1', 'NaN', '.', '90071992547409.92']) {
    assert.equal(parseUsdBound(value).valid, false, value)
  }
  assert.deepEqual(parseUsdBound(''), { valid: true, value: null })
  assert.deepEqual(parseUsdBound('0.00'), { valid: true, value: 0 })
  assert.equal(formatUsdBound(null), '')
})

test('whole-area bounds reject fractional and exponent input instead of changing its meaning', () => {
  for (const value of ['1400.5', '1e3', '0', '-1', '9007199254740992']) {
    assert.equal(parseWholeAreaBound(value).valid, false, value)
  }
  assert.deepEqual(parseWholeAreaBound('1400'), { valid: true, value: 1400 })
  assert.deepEqual(parseWholeAreaBound(''), { valid: true, value: null })
})
