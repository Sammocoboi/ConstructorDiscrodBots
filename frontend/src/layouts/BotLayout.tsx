import { useState } from 'react'
import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Card,
  Group,
  Menu,
  Stack,
  Tabs,
  Text,
  Title,
  Tooltip,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconBrandDiscord,
  IconCopy,
  IconDots,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { qk, useBot, useToastMutation } from '../shared/api/hooks'
import { api } from '../shared/api'
import { errorMessage } from '../shared/api/errors'
import { BotAvatar, StatusBadge } from '../shared/components/bits'
import { ErrorState, LoadingState } from '../shared/components/states'
import { ConfirmModal } from '../shared/components/ConfirmModal'
import { AppIcon } from '../shared/components/icons'
import { formatDuration } from '../shared/lib/format'

const tabs = [
  { value: 'overview', labelKey: 'nav.overview', icon: 'dashboard' },
  { value: 'modules', labelKey: 'nav.modules', icon: 'layout' },
  { value: 'commands', labelKey: 'nav.commands', icon: 'terminal' },
  { value: 'flows', labelKey: 'nav.flows', icon: 'bolt' },
  { value: 'messages', labelKey: 'nav.messages', icon: 'messages' },
  { value: 'guilds', labelKey: 'nav.guilds', icon: 'server' },
  { value: 'status', labelKey: 'bot.diagnostics', icon: 'activity' },
  { value: 'profile', labelKey: 'nav.botProfile', icon: 'settings' },
] as const

export function BotLayout() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { data: bot, isLoading, isError, error, refetch } = useBot(botId)
  const [deleteOpened, setDeleteOpened] = useState(false)

  const invalidate = [qk.bot(botId ?? ''), qk.bots, qk.dashboard, qk.botEvents(botId ?? '')]

  const startMutation = useToastMutation({
    mutationFn: () => api.bots.start(botId as string),
    successMessage: t('dashboard.started'),
    invalidateKeys: invalidate,
  })
  const stopMutation = useToastMutation({
    mutationFn: () => api.bots.stop(botId as string),
    successMessage: t('dashboard.stopped'),
    invalidateKeys: invalidate,
  })
  const restartMutation = useToastMutation({
    mutationFn: () => api.bots.restart(botId as string),
    successMessage: t('dashboard.restarted'),
    invalidateKeys: invalidate,
  })
  const deleteMutation = useToastMutation({
    mutationFn: () => api.bots.remove(botId as string),
    successMessage: t('dashboard.deleted'),
    invalidateKeys: [qk.bots, qk.dashboard],
    onSuccess: () => navigate('/app', { replace: true }),
  })

  if (isLoading) return <LoadingState />
  if (isError || !bot) {
    return (
      <ErrorState
        title={t('bot.notFoundTitle')}
        message={error ? errorMessage(error) : t('bot.notFoundText')}
        onRetry={() => void refetch()}
      />
    )
  }

  const segment = location.pathname.split('/')[5] ?? 'overview'
  const activeTab = tabs.some((tab) => tab.value === segment) ? segment : 'overview'
  const isRunning = bot.status === 'online' || bot.status === 'starting'
  const copyInvite = async () => {
    try {
      await navigator.clipboard.writeText(bot.inviteUrl)
      notifications.show({ color: 'teal', message: t('bot.inviteCopied') })
    } catch {
      notifications.show({ color: 'red', message: t('common.error') })
    }
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start" wrap="wrap" gap="md">
        <Group align="flex-start" gap="md" wrap="nowrap">
          <ActionIcon variant="subtle" color="gray" size="lg" component={Link} to="/app" mt={2}>
            <IconArrowLeft size={20} />
          </ActionIcon>
          <BotAvatar name={bot.name} color={bot.avatarColor} size={58} radius={17} />
          <Stack gap={4}>
            <Group gap="sm" wrap="wrap">
              <Title order={2} fz={{ base: 22, sm: 27 }} lh={1.1}>
                {bot.name}
              </Title>
              <StatusBadge status={bot.status} />
            </Group>
            <Text size="sm" c="dimmed" maw={620}>
              {bot.description}
            </Text>
            <Group gap="lg" mt={2}>
              <Text size="xs" c="dimmed">
                {t('bot.uptime')}: <strong>{formatDuration(bot.uptimeSeconds)}</strong>
              </Text>
              <Text size="xs" c="dimmed">
                {t('bot.ping')}: <strong>{bot.ping} ms</strong>
              </Text>
              <Text size="xs" c="dimmed">
                {t('bot.guilds')}: <strong>{bot.guilds.length}</strong>
              </Text>
            </Group>
          </Stack>
        </Group>

        <Group gap="sm">
          <Tooltip label={t('bot.inviteCopied')}>
            <Button
              variant="default"
              leftSection={<IconBrandDiscord size={17} />}
              rightSection={<IconCopy size={14} />}
              onClick={() => void copyInvite()}
            >
              {t('bot.invite')}
            </Button>
          </Tooltip>
          {isRunning ? (
            <Button
              color="red"
              variant="light"
              leftSection={<IconPlayerStop size={17} />}
              loading={stopMutation.isPending}
              onClick={() => stopMutation.mutate()}
            >
              {t('dashboard.stop')}
            </Button>
          ) : (
            <Button
              leftSection={<IconPlayerPlay size={17} />}
              loading={startMutation.isPending}
              onClick={() => startMutation.mutate()}
            >
              {t('dashboard.start')}
            </Button>
          )}
          <Menu position="bottom-end" width={210}>
            <Menu.Target>
              <ActionIcon variant="default" size="lg" aria-label={t('common.more')}>
                <IconDots size={18} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item
                leftSection={<IconRefresh size={15} />}
                onClick={() => restartMutation.mutate()}
              >
                {t('dashboard.restart')}
              </Menu.Item>
              <Menu.Item
                leftSection={<AppIcon name="template" size={15} />}
                component={Link}
                to={`/app/bots/${bot.id}/profile`}
              >
                {t('bot.saveAsTemplate')}
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
      </Group>

      {bot.status === 'error' && (
        <Alert color="red" icon={<IconAlertTriangle size={17} />} title={t('bot.launchError')}>
          {bot.lastError ?? t('bot.launchErrorHint')}
        </Alert>
      )}

      <Card withBorder radius="lg" p={0}>
        <Tabs value={activeTab} variant="outline" keepMounted={false}>
          <Tabs.List px="sm" pt="xs" style={{ flexWrap: 'nowrap', overflowX: 'auto' }}>
            {tabs.map((tab) => (
              <Tabs.Tab
                key={tab.value}
                value={tab.value}
                onClick={() => navigate(`/app/bots/${bot.id}/${tab.value}`)}
                leftSection={<AppIcon name={tab.icon} size={15} />}
                style={{ whiteSpace: 'nowrap' }}
              >
                {t(tab.labelKey)}
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs>
      </Card>

      <Box>
        <Outlet />
      </Box>

      <ConfirmModal
        opened={deleteOpened}
        onClose={() => setDeleteOpened(false)}
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
        title={t('dashboard.deleteTitle')}
        description={t('dashboard.deleteText')}
        confirmLabel={t('common.delete')}
      />
    </Stack>
  )
}
