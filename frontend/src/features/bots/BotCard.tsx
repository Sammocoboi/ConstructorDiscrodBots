import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Group,
  Menu,
  Stack,
  Text,
  Title,
  Tooltip,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  IconArrowRight,
  IconDots,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-react'
import type { Bot } from '../../shared/api/types'
import { api } from '../../shared/api'
import { qk, useToastMutation } from '../../shared/api/hooks'
import { BotAvatar, StatusBadge } from '../../shared/components/bits'
import { ConfirmModal } from '../../shared/components/ConfirmModal'
import { formatRelative } from '../../shared/lib/format'

export function BotCard({ bot }: { bot: Bot }) {
  const { t } = useTranslation()
  const [deleteOpened, setDeleteOpened] = useState(false)
  const invalidate = [qk.bots, qk.dashboard, qk.bot(bot.id)]

  const startMutation = useToastMutation({
    mutationFn: () => api.bots.start(bot.id),
    successMessage: t('dashboard.started'),
    invalidateKeys: invalidate,
  })
  const stopMutation = useToastMutation({
    mutationFn: () => api.bots.stop(bot.id),
    successMessage: t('dashboard.stopped'),
    invalidateKeys: invalidate,
  })
  const restartMutation = useToastMutation({
    mutationFn: () => api.bots.restart(bot.id),
    successMessage: t('dashboard.restarted'),
    invalidateKeys: invalidate,
  })
  const deleteMutation = useToastMutation({
    mutationFn: () => api.bots.remove(bot.id),
    successMessage: t('dashboard.deleted'),
    invalidateKeys: [qk.bots, qk.dashboard],
    onSuccess: () => setDeleteOpened(false),
  })

  const isRunning = bot.status === 'online' || bot.status === 'starting'

  return (
    <>
      <Card withBorder radius="lg" p="lg" className="bf-hover-lift">
        <Stack gap="md">
          <Group justify="space-between" align="flex-start" wrap="nowrap">
            <Group gap="sm" wrap="nowrap" align="flex-start">
              <BotAvatar name={bot.name} color={bot.avatarColor} size={46} radius={13} />
              <Stack gap={4}>
                <Group gap={8} wrap="wrap">
                  <Title order={3} fz={17} lh={1.2}>
                    <Link to={`/app/bots/${bot.id}/overview`}>{bot.name}</Link>
                  </Title>
                  <StatusBadge status={bot.status} size="sm" />
                </Group>
                <Text size="xs" c="dimmed" lineClamp={2} maw={430}>
                  {bot.description || '—'}
                </Text>
              </Stack>
            </Group>
            <Menu position="bottom-end" width={210}>
              <Menu.Target>
                <Button variant="subtle" color="gray" size="compact-sm" px={4}>
                  <IconDots size={18} />
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item
                  leftSection={<IconRefresh size={15} />}
                  onClick={() => restartMutation.mutate()}
                >
                  {t('dashboard.restart')}
                </Menu.Item>
                <Menu.Item
                  leftSection={<IconArrowRight size={15} />}
                  component={Link}
                  to={`/app/bots/${bot.id}/profile`}
                >
                  {t('nav.botProfile')}
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item
                  color="red"
                  leftSection={<IconTrash size={15} />}
                  onClick={() => setDeleteOpened(true)}
                >
                  {t('common.delete')}
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>

          {bot.status === 'error' && bot.lastError && (
            <Text size="xs" c="red" lineClamp={2}>
              {bot.lastError}
            </Text>
          )}

          <Group gap={6}>
            <Badge variant="light" color="gray" size="sm">
              {t('bot.guilds')}: {bot.guilds.length}
            </Badge>
            <Badge variant="light" color="gray" size="sm">
              {t('bot.ping')}: {bot.ping} ms
            </Badge>
            <Badge variant="light" color="gray" size="sm">
              v{bot.version}
            </Badge>
          </Group>

          <Group justify="space-between" align="center">
            <Text size="xs" c="dimmed">
              {formatRelative(bot.updatedAt)}
            </Text>
            <Group gap="xs">
              <Tooltip label={isRunning ? t('dashboard.stop') : t('dashboard.start')}>
                <Button
                  variant="light"
                  color={isRunning ? 'red' : 'teal'}
                  size="compact-sm"
                  px={10}
                  loading={startMutation.isPending || stopMutation.isPending}
                  onClick={() =>
                    isRunning ? stopMutation.mutate() : startMutation.mutate()
                  }
                >
                  {isRunning ? <IconPlayerStop size={15} /> : <IconPlayerPlay size={15} />}
                </Button>
              </Tooltip>
              <Button
                component={Link}
                to={`/app/bots/${bot.id}/overview`}
                size="compact-sm"
                variant="default"
                rightSection={<IconArrowRight size={14} />}
              >
                {t('common.open')}
              </Button>
            </Group>
          </Group>
        </Stack>
      </Card>

      <ConfirmModal
        opened={deleteOpened}
        onClose={() => setDeleteOpened(false)}
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
        title={t('dashboard.deleteTitle')}
        description={t('dashboard.deleteText')}
        confirmLabel={t('common.delete')}
      />
    </>
  )
}
