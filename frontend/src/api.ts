import { useEffect, useState } from 'react'
import type { ErrorInfo } from './generated/contracts'

export class ApiError extends Error {
  readonly code: string
  readonly stage: string
  constructor(info: ErrorInfo) {
    super(info.message)
    this.code = info.code
    this.stage = info.stage
  }
}

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: { Accept: 'application/json', ...init?.headers },
  })
  const value: unknown = await response.json()
  if (!response.ok) {
    if (
      value &&
      typeof value === 'object' &&
      'message' in value &&
      typeof value.message === 'string'
    ) {
      throw new ApiError({
        message: value.message,
        code: 'code' in value ? String(value.code) : String(response.status),
        stage: 'stage' in value ? String(value.stage) : 'request',
      })
    }
    throw new Error(`The local server returned ${response.status}. Please retry.`)
  }
  return value as T
}

export function useResource<T>(url: string | null, refreshMs = 0, onLoaded?: (data: T) => void) {
  const [result, setResult] = useState<{
    url: string | null
    data: T | null
    error: string | null
  }>({ url: null, data: null, error: null })
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    if (!url) return
    const controller = new AbortController()
    let active = true
    let pending = false
    async function load() {
      if (pending) return
      pending = true
      try {
        const result = await request<T>(url!, { signal: controller.signal })
        if (active) {
          setResult({ url, data: result, error: null })
          onLoaded?.(result)
        }
      } catch (failure) {
        if (active && !controller.signal.aborted) {
          setResult((previous) => ({
            url,
            data: previous.url === url ? previous.data : null,
            error:
              failure instanceof Error
                ? failure.message
                : 'The workspace could not load this evidence.',
          }))
        }
      } finally {
        pending = false
      }
    }
    void load()
    const timer = refreshMs ? window.setInterval(() => void load(), refreshMs) : undefined
    return () => {
      active = false
      controller.abort()
      window.clearInterval(timer)
    }
  }, [url, refreshMs, revision, onLoaded])
  return {
    data: result.url === url ? result.data : null,
    error: result.url === url ? result.error : null,
    loading: Boolean(url) && result.url !== url,
    retry: () => {
      setResult((previous) => ({ ...previous, url: null }))
      setRevision((value) => value + 1)
    },
  }
}

export const shortHash = (value: string) => `${value.slice(0, 10)}…${value.slice(-6)}`
export const monthLabel = (value: string) =>
  new Intl.DateTimeFormat('en', { month: 'short', year: 'numeric', timeZone: 'UTC' }).format(
    new Date(value + '-01T12:00:00Z'),
  )
