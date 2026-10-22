import { getAccessToken, useAuthStore } from '../stores/authStore'
import { ApiError } from './errors'

export const API_BASE = (import.meta.env.VITE_API_URL ?? '/api/v1').replace(/\/$/, '')

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
  signal?: AbortSignal
  retryOnUnauthorized?: boolean
}

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: { Accept: 'application/json' },
        })
        if (!response.ok) return null
        const payload = (await response.json()) as {
          access_token?: string
          accessToken?: string
        }
        const token = payload.access_token ?? payload.accessToken ?? null
        if (token) useAuthStore.getState().setAccessToken(token)
        return token
      } catch {
        return null
      } finally {
        refreshPromise = null
      }
    })()
  }
  return refreshPromise
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: Record<string, unknown> = {}
  try {
    payload = (await response.json()) as Record<string, unknown>
  } catch {
    payload = {}
  }
  const code = typeof payload.code === 'string' ? payload.code : `http_${response.status}`
  const message =
    typeof payload.message === 'string'
      ? payload.message
      : typeof payload.detail === 'string'
        ? payload.detail
        : `Запрос завершился с ошибкой ${response.status}.`
  const requestId =
    (typeof payload.request_id === 'string' ? payload.request_id : undefined) ??
    response.headers.get('x-request-id') ??
    undefined
  return new ApiError(
    response.status,
    code,
    message,
    payload.details ?? payload.errors,
    requestId,
  )
}

async function send<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getAccessToken()
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...options.headers,
  }
  if (token) headers.Authorization = `Bearer ${token}`

  let body: BodyInit | undefined
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body,
    credentials: 'include',
    signal: options.signal,
  })

  if (response.status === 401 && options.retryOnUnauthorized !== false) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      return send<T>(path, { ...options, retryOnUnauthorized: false })
    }
    useAuthStore.getState().logout()
    throw new ApiError(401, 'unauthorized', 'Сессия истекла. Войдите снова.')
  }

  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) return undefined as T
  return (await response.json()) as T
}

export const http = {
  get: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    send<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    send<T>(path, { ...options, method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => send<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => send<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => send<T>(path, { method: 'DELETE' }),
}
