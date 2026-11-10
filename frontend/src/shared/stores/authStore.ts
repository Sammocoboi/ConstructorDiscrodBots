import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '../api/types'

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  setSession: (user: User, accessToken: string) => void
  setAccessToken: (accessToken: string) => void
  updateUser: (patch: Partial<User>) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      setSession: (user, accessToken) =>
        set({ user, accessToken, isAuthenticated: true }),
      setAccessToken: (accessToken) => set({ accessToken, isAuthenticated: true }),
      updateUser: (patch) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...patch } : state.user,
        })),
      logout: () => set({ user: null, accessToken: null, isAuthenticated: false }),
    }),
    {
      name: 'botforge.auth',
      merge: (persistedState, currentState) => {
        const persisted = persistedState as Partial<AuthState> | undefined
        const persistedToken = persisted?.accessToken

        // A demo session must never be treated as a real backend session.
        if (
          import.meta.env.VITE_USE_MOCKS !== 'true' &&
          typeof persistedToken === 'string' &&
          persistedToken.startsWith('mock-access-')
        ) {
          return currentState
        }

        return { ...currentState, ...persisted }
      },
    },
  ),
)

export function getAccessToken() {
  return useAuthStore.getState().accessToken
}
