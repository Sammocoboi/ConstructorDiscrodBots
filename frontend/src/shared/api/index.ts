import { httpApi } from './httpApi'
import { mockApi, type MockApi } from './mockApi'

const useMocks = import.meta.env.VITE_USE_MOCKS === 'true'

export const api: MockApi = useMocks ? mockApi : httpApi

export const isMockMode = useMocks
export { isApiError, errorMessage, ApiError } from './errors'
export * from './types'
