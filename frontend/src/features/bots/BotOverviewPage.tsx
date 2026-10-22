import {
  Badge,
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Timeline,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import {
  IconArrowRight,
  IconCheck,
  IconClock,
  IconPlus,
  IconX,
} from '@tabler/icons-react'
import {
  useBot,
  useBotEvents,
  useBotModules,
  useCommands,
} from '../../shared/api/hooks'
import { StatCard } from '../../shared/components/bits'
import { LoadingState } from '../../shared/components/states'
import { AppIcon } from '../../shared/components/icons'
import { formatDuration, formatRelative } from '../../shared/lib/format'

const eventIcon: Record<string, string> = {
  runtime: 'activity',
  config: 'settings',
  command: 'terminal',
  module: 'layout',
  error: 'alert',
}

export default function BotOverviewPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const modules = useBotModules(botId)
  const commands = useCommands(botId)
  const events = useBotEvents(botId)

  if (!bot) return <LoadingState minHeight={280} />

  const enabledModules = modules.data?.filter((item) => item.state.enabled) ?? []
  const checklist = [
    {
      key: 'token',
      label: t('bot.checklistToken'),
      done: Boolean(bot.tokenMasked),
      to: `/app/bots/${bot.id}/profile`,
    },
    {
      key: 'invite',
      label: t('bot.checklistInvite'),
      done: bot.guilds.some((guild) => guild.botAdded),
      to: `/app/bots/${bot.id}/guilds`,
    },
    {
      key: 'module',
      label: t('bot.checklistModule'),
      done: enabledModules.length > 0,
      to: `/app/bots/${bot.id}/modules`,
    },
    {
      key: 'command',
      label: t('bot.checklistCommand'),
      done: (commands.data?.length ?? 0) > 0,
      to: `/app/bots/${bot.id}/commands`,
    },
  ]
  const doneCount = checklist.filter((item) => item.done).length
  const progress = Math.round((doneCount / checklist.length) * 100)

  const quickLinks = [
    { to: `/app/bots/${bot.id}/modules`, label: t('nav.modules'), icon: 'layout', hint: `${enabledModules.length} / ${modules.data?.length ?? 0}` },
    { to: `/app/bots/${bot.id}/commands`, label: t('nav.commands'), icon: 'terminal', hint: `${commands.data?.length ?? 0}` },
    { to: `/app/bots/${bot.id}/flows`, label: t('nav.flows'), icon: 'bolt', hint: 'Visual' },
    { to: `/app/bots/${bot.id}/messages`, label: t('nav.messages'), icon: 'messages', hint: 'Embed builder' },
  ]

  return (
    <Stack gap="lg">
      <SimpleGrid cols={{ base: 2, lg: 4 }} spacing="md">
        <StatCard
          label={t('bot.ping')}
          value={`${bot.ping} ms`}
          icon="activity"
          accent={bot.ping > 200 ? 'yellow' : 'teal'}
          hint={bot.status === 'online' ? t('common.online') : t('common.offline')}
        />
        <StatCard
          label={t('bot.uptime')}
          value={formatDuration(bot.uptimeSeconds)}
          icon="clock"
          accent="cyan"
          hint={`${t('bot.version')} ${bot.version}`}
        />
        <StatCard
          label={t('bot.guilds')}
          value={bot.guilds.length}
          icon="server"
          hint={t('bot.guildsSubtitle')}
        />
        <StatCard
          label={t('nav.modules')}
          value={`${enabledModules.length}/${modules.data?.length ?? 0}`}
          icon="layout"
          accent="orange"
          hint={t('common.enabled')}
        />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="lg">
        <Stack gap="md" style={{ gridColumn: 'span 2' }}>
          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="md" wrap="wrap">
              <Group gap="sm">
                <ThemeIcon variant="light" color="teal" size={38} radius="md">
                  <IconCheck size={19} />
                </ThemeIcon>
                <Stack gap={0}>
                  <Title order={3} fz={18}>
                    {t('bot.checklist')}
                  </Title>
                  <Text size="xs" c="dimmed">
                    {doneCount} / {checklist.length} · {progress}%
                  </Text>
                </Stack>
              </Group>
              <Badge variant="light" color={doneCount === checklist.length ? 'teal' : 'brand'}>
                {doneCount === checklist.length ? t('common.done') : t('common.next')}
              </Badge>
            </Group>
            <Stack gap="xs">
              {checklist.map((item) => (
                <Group
                  key={item.key}
                  justify="space-between"
                  wrap="nowrap"
                  p="xs"
                  style={{
                    borderRadius: 10,
                    border: '1px solid var(--mantine-color-default-border)',
                  }}
                >
                  <Group gap="sm" wrap="nowrap">
                    <ThemeIcon
                      size={24}
                      radius="xl"
                      variant={item.done ? 'filled' : 'light'}
                      color={item.done ? 'teal' : 'gray'}
                    >
                      {item.done ? <IconCheck size={13} /> : <IconX size={13} />}
                    </ThemeIcon>
                    <Text size="sm" fw={item.done ? 500 : 600}>
                      {item.label}
                    </Text>
                  </Group>
                  <Button
                    component={Link}
                    to={item.to}
                    variant="subtle"
                    size="compact-xs"
                    rightSection={<IconArrowRight size={13} />}
                  >
                    {item.done ? t('common.edit') : t('common.open')}
                  </Button>
                </Group>
              ))}
            </Stack>
          </Card>

          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="md">
              <Title order={3} fz={18}>
                {t('bot.quickLinks')}
              </Title>
            </Group>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              {quickLinks.map((link) => (
                <Button
                  key={link.to}
                  component={Link}
                  to={link.to}
                  variant="default"
                  justify="space-between"
                  size="md"
                  leftSection={<AppIcon name={link.icon} size={17} />}
                  rightSection={<IconArrowRight size={15} />}
                  styles={{ inner: { width: '100%' } }}
                >
                  <Group gap={8}>
                    <Text size="sm" fw={600}>
                      {link.label}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {link.hint}
                    </Text>
                  </Group>
                </Button>
              ))}
            </SimpleGrid>
          </Card>
        </Stack>

        <Stack gap="md">
          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="md">
              <Title order={3} fz={18}>
                {t('bot.recentActivity')}
              </Title>
              <Button
                component={Link}
                to={`/app/bots/${bot.id}/status`}
                variant="subtle"
                size="compact-xs"
              >
                {t('common.all')}
              </Button>
            </Group>
            {events.data?.length ? (
              <Timeline bulletSize={22} lineWidth={1}>
                {events.data.slice(0, 6).map((event) => (
                  <Timeline.Item
                    key={event.id}
                    bullet={<AppIcon name={eventIcon[event.type] ?? 'info'} size={11} />}
                    title={
                      <Text size="sm" fw={600}>
                        {event.message}
                      </Text>
                    }
                  >
                    <Text size="xs" c="dimmed">
                      {formatRelative(event.createdAt)}
                    </Text>
                  </Timeline.Item>
                ))}
              </Timeline>
            ) : (
              <Text size="sm" c="dimmed">
                {t('bot.noEvents')}
              </Text>
            )}
          </Card>

          <Card withBorder radius="lg" p="lg">
            <Title order={3} fz={18} mb="sm">
              {t('common.details')}
            </Title>
            <Stack gap="xs">
              {[
                { label: t('bot.version'), value: bot.version },
                { label: t('bot.runtime'), value: bot.runtimeVersion },
                { label: t('common.status'), value: bot.status },
                { label: t('bot.lastUpdated'), value: formatRelative(bot.updatedAt) },
              ].map((row) => (
                <Group key={row.label} justify="space-between">
                  <Text size="xs" c="dimmed">
                    {row.label}
                  </Text>
                  <Text size="xs" fw={600}>
                    {row.value}
                  </Text>
                </Group>
              ))}
            </Stack>
            <Button
              component={Link}
              to={`/app/bots/${bot.id}/profile`}
              variant="light"
              fullWidth
              mt="md"
              leftSection={<IconPlus size={15} />}
            >
              {t('nav.botProfile')}
            </Button>
          </Card>

          <Card withBorder radius="lg" p="lg">
            <Group gap="sm" mb={4}>
              <IconClock size={16} />
              <Text size="sm" fw={700}>
                {t('bot.lastUpdated')}
              </Text>
            </Group>
            <Text size="xs" c="dimmed">
              {formatRelative(bot.createdAt)} · {bot.guilds.length} {t('nav.guilds').toLowerCase()}
            </Text>
          </Card>
        </Stack>
      </SimpleGrid>
    </Stack>
  )
}
