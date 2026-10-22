import { ActionIcon, Tooltip } from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { IconDeviceDesktop, IconMoon, IconSun } from '@tabler/icons-react'
import { useThemeStore } from '../stores/themeStore'
import type { ThemePreference } from '../api/types'

const order: ThemePreference[] = ['auto', 'light', 'dark']

export function ThemeToggle() {
  const { t } = useTranslation()
  const preference = useThemeStore((state) => state.preference)
  const setPreference = useThemeStore((state) => state.setPreference)

  const next = order[(order.indexOf(preference) + 1) % order.length]
  const Icon =
    preference === 'auto' ? IconDeviceDesktop : preference === 'light' ? IconSun : IconMoon

  return (
    <Tooltip label={`${t('theme.label')}: ${t(`theme.${preference}`)}`}>
      <ActionIcon
        variant="subtle"
        color="gray"
        size="lg"
        aria-label={t('theme.switch')}
        onClick={() => setPreference(next)}
      >
        <Icon size={19} stroke={1.8} />
      </ActionIcon>
    </Tooltip>
  )
}
