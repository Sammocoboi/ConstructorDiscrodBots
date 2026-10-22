import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UiState {
  navbarOpened: boolean
  setNavbarOpened: (opened: boolean) => void
  commandPaletteOpened: boolean
  setCommandPaletteOpened: (opened: boolean) => void
  notificationsOpened: boolean
  setNotificationsOpened: (opened: boolean) => void
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      navbarOpened: false,
      setNavbarOpened: (navbarOpened) => set({ navbarOpened }),
      commandPaletteOpened: false,
      setCommandPaletteOpened: (commandPaletteOpened) => set({ commandPaletteOpened }),
      notificationsOpened: false,
      setNotificationsOpened: (notificationsOpened) => set({ notificationsOpened }),
    }),
    {
      name: 'botforge.ui',
      partialize: (state) => ({ navbarOpened: state.navbarOpened }),
    },
  ),
)
