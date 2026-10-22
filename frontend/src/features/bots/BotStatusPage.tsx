import { useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Code,
  Group,
  ScrollArea,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { IconCopy, IconRefresh } from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { api } from '../../shared/api'
import {
  qk,
  useBot,
  useBotEvents,
  useToastMutation,
} from '../../shared/api/hooks'
import { Metric, StatusBadge } from '../../shared/components/bits'
import { EmptyState, LoadingState } from '../../shared/components/states'
import { PageHeader } from '../../shared/components/bits'
import { formatDate, formatDuration, formatRelative } from '../../shared/lib/format'

export default function BotStatusPage() {
  const { t } = useTranslation()
  const { botId } = useParams()
  const { data: bot } = useBot(botId)
  const events = useBotEvents(botId)
  const [filter, setFilter] = useState('all')

  const restartMutation = useToastMutation({
    mutationFn: () => api.bots.restart(botId as string),
    successMessage: t('dashboard.restarted'),
    invalidateKeys: [qk.bot(botId ?? ''), qk.botEvents(botId ?? ''), qk.bots],
  })

  const filteredEvents = useMemo(() => {
    if (!events.data) return []
    if (filter === 'all') return events.data
    return events.data.filter((event) => event.type === filter)
  }, [events.data, filter])

  if (!bot) return <LoadingState minHeight={280} />

  const diagnostics = {
    botId: bot.id,
    name: bot.name,
    status: bot.status,
    desiredState: bot.desiredState,
    ping: bot.ping,
    uptimeSeconds: bot.uptimeSeconds,
    runtime: bot.runtimeVersion,
    version: bot.version,
    guilds: bot.guilds.length,
    lastError: bot.lastError ?? null,
    updatedAt: bot.updatedAt,
  }

  const copyDiagnostics = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(diagnostics, null, 2))
      notifications.show({
        color: 'teal',
        title: t('notifications.typeSuccess'),
        message: t('bot.copyDiagnostics'),
      })
    } catch {
      notifications.show({ color: 'red', message: t('common.error') })
    }
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title={t('bot.diagnostics')}
        description={t('bot.diagnosticsSubtitle')}
        actions={
          <>
            <Button
              variant="default"
              leftSection={<IconCopy size={16} />}
              onClick={() => void copyDiagnostics()}
            >
              {t('bot.copyDiagnostics')}
            </Button>
            <Button
              leftSection={<IconRefresh size={16} />}
              loading={restartMutation.isPending}
              onClick={() => restartMutation.mutate()}
            >
              {t('dashboard.restart')}
            </Button>
          </>
        }
      />

      <SimpleGrid cols={{ base: 2, lg: 4 }} spacing="md">
        <Card withBorder radius="lg" p="md">
          <Text size="xs" c="dimmed" fw={700} tt="uppercase">
            {t('common.status')}
          </Text>
          <Group mt={6}>
            <StatusBadge status={bot.status} />
          </Group>
          <Text size="xs" c="dimmed" mt={6}>
            desired: {bot.desiredState}
          </Text>
        </Card>
        <Metric label={t('bot.ping')} value={`${bot.ping} ms`} />
        <Metric label={t('bot.uptime')} value={formatDuration(bot.uptimeSeconds)} />
        <Metric label={t('bot.runtime')} value={bot.runtimeVersion} />
      </SimpleGrid>

      <Card withBorder radius="lg" p="lg">
        <Group justify="space-between" mb="md" wrap="wrap">
          <Title order={3} fz={18}>
            {t('bot.eventLog')}
          </Title>
          <SegmentedControl
            size="xs"
            value={filter}
            onChange={setFilter}
            data={[
              { value: 'all', label: t('common.all') },
              { value: 'runtime', label: 'Runtime' },
              { value: 'config', label: 'Config' },
              { value: 'command', label: 'Command' },
              { value: 'module', label: 'Module' },
              { value: 'error', label: 'Error' },
            ]}
          />
        </Group>

        {events.isLoading && <LoadingState minHeight={180} />}
        {filteredEvents.length === 0 ? (
          <EmptyState icon="activity" title={t('bot.noEvents')} compact />
        ) : (
          <ScrollArea>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t('common.status')}</Table.Th>
                  <Table.Th>{t('bot.eventLog')}</Table.Th>
                  <Table.Th>{t('common.details')}</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {filteredEvents.map((event) => {
                  const color =
                    event.type === 'error'
                      ? 'red'
                      : event.type === 'command'
                        ? 'brand'
                        : event.type === 'module'
                          ? 'cyan'
                          : event.type === 'config'
                            ? 'orange'
                            : 'teal'
                  return (
                    <Table.Tr key={event.id}>
                      <Table.Td>
                        <Badge variant="light" color={color} size="sm">
                          {event.type}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{event.message}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed">
                          {formatRelative(event.createdAt)}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed">
                          {formatDate(event.createdAt, true)}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  )
                })}
              </Table.Tbody>
            </Table>
          </ScrollArea>
        )}
      </Card>

      <Card withBorder radius="lg" p="lg">
        <Title order={3} fz={18} mb="sm">
          {t('bot.copyDiagnostics')}
        </Title>
        <Code block style={{ maxHeight: 240, overflow: 'auto' }}>
          {JSON.stringify(diagnostics, null, 2)}
        </Code>
      </Card>
    </Stack>
  )
}
