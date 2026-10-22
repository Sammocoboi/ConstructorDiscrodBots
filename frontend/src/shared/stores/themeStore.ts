import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ThemePreference } from '../api/types'

interface ThemeState {
  preference: ThemePreference
  setPreference: (preference: ThemePreference) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      preference: 'auto',
      setPreference: (preference) => set({ preference }),
    }),
    { name: 'botforge.theme' },
  ),
)
