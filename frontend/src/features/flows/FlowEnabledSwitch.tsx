import { Switch } from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { api } from '../../shared/api'
import { qk, useToastMutation } from '../../shared/api/hooks'
import type { Flow } from '../../shared/api/types'

export function FlowEnabledSwitch({ flow }: { flow: Flow }) {
  const { t } = useTranslation()
  const enabled = flow.enabled !== false
  const toggle = useToastMutation({
    mutationFn: (value: boolean) => api.flows.setEnabled(flow.botId, flow.id, value),
    successMessage: (_, value) => t(value ? 'flows.enabled' : 'flows.disabled'),
    invalidateKeys: [qk.flows(flow.botId), qk.bot(flow.botId)],
  })

  if (flow.status !== 'published') return null

  return (
    <Switch
      size="sm"
      label={t(enabled ? 'common.enabled' : 'common.disabled')}
      aria-label={t('flows.enabledLabel', { name: flow.name })}
      checked={enabled}
      disabled={toggle.isPending}
      onChange={(event) => toggle.mutate(event.currentTarget.checked)}
    />
  )
}
