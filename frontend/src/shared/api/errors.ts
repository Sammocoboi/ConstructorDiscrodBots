export class ApiError extends Error {
  status: number
  code: string
  details?: unknown
  requestId?: string

  constructor(
    status: number,
    code: string,
    message: string,
    details?: unknown,
    requestId?: string,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

export function toApiError(error: unknown): ApiError {
  if (isApiError(error)) return error
  if (error instanceof TypeError) {
    return new ApiError(0, 'network_error', 'Ошибка сети. Проверьте подключение.')
  }
  if (error instanceof Error) {
    return new ApiError(500, 'unknown_error', error.message)
  }
  return new ApiError(500, 'unknown_error', 'Неизвестная ошибка.')
}

export function errorMessage(error: unknown, fallback = 'Что-то пошло не так.') {
  if (isApiError(error)) {
    if (error.code === 'network_error') {
      return 'Не удалось связаться с сервером. Проверьте соединение.'
    }
    return error.message || fallback
  }
  if (error instanceof Error) return error.message
  return fallback
}

export function fieldErrors(error: unknown): Record<string, string> {
  if (!isApiError(error) || !error.details || typeof error.details !== 'object') return {}
  const details = error.details as Record<string, unknown>
  const result: Record<string, string> = {}
  for (const [key, value] of Object.entries(details)) {
    if (typeof value === 'string') result[key] = value
    else if (Array.isArray(value) && typeof value[0] === 'string') result[key] = value[0]
  }
  return result
}
